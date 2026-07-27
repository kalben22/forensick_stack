#!/usr/bin/env python3
"""
Generic triage scanner — runs inside the ``forensicstack/triage`` container.

Answers "what is worth looking at in this file?" for an artifact of *any* type,
which is what makes the platform useful before the analyst knows which
specialised tool to reach for.

Four passes, all streaming so a 5 GB input costs bounded memory:

1. ``strings``  — extracted and *classified* (URL, IP, email, path, registry
   key, base64 blob, private key, CTF flag) rather than dumped raw.
2. ``carve``    — embedded file signatures at non-zero offsets, i.e. the
   binwalk question: is something hidden inside this thing?
3. ``entropy``  — a block entropy profile that localises encrypted or packed
   regions instead of reporting one number for the whole file.
4. ``flags``    — configurable regex for CTF flag formats.

Stdlib only, on purpose: the container stays small and has no supply chain
beyond the base image.

Contract with the platform: read ``INPUT_PATH``, write JSON to
``$OUTPUT_PATH/triage.json``, exit non-zero on failure. Never ``|| true``.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path

CHUNK = 4 * 1024 * 1024
OVERLAP = 4096  # so a string or signature straddling a chunk edge is not lost

MIN_STRING_LEN = int(os.getenv("TRIAGE_MIN_STRING_LEN", "6"))
MAX_STRINGS_PER_CLASS = int(os.getenv("TRIAGE_MAX_STRINGS_PER_CLASS", "200"))
MAX_CARVED = int(os.getenv("TRIAGE_MAX_CARVED", "500"))
ENTROPY_BLOCK = 64 * 1024
MAX_ENTROPY_POINTS = 512

FLAG_PATTERNS = [
    p for p in os.getenv(
        "TRIAGE_FLAG_REGEX",
        r"[A-Za-z0-9_]{2,20}\{[^}\n]{1,120}\}"
    ).split("|||") if p
]

# --------------------------------------------------------------------------- #
# String classification
# --------------------------------------------------------------------------- #

_ASCII_RUN = re.compile(rb"[\x20-\x7e]{%d,}" % MIN_STRING_LEN)
_UTF16_RUN = re.compile(rb"(?:[\x20-\x7e]\x00){%d,}" % MIN_STRING_LEN)

CLASSIFIERS: list[tuple[str, re.Pattern[str]]] = [
    ("url", re.compile(r"\b(?:https?|ftp|smb|ldap)://[^\s'\"<>]{4,}", re.I)),
    ("onion", re.compile(r"\b[a-z2-7]{16,56}\.onion\b", re.I)),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]{2,}\b")),
    ("ipv4", re.compile(
        r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")),
    ("ipv6", re.compile(r"\b(?:[0-9a-f]{1,4}:){5,7}[0-9a-f]{1,4}\b", re.I)),
    ("windows_path", re.compile(r"\b[A-Za-z]:\\\\?(?:[^\\/:*?\"<>|\r\n]+\\\\?){1,}")),
    ("unc_path", re.compile(r"\\\\[A-Za-z0-9._-]+\\[^\s\"'<>|]{1,}")),
    ("registry_key", re.compile(
        r"\b(?:HKEY_[A-Z_]+|HKLM|HKCU)\\[^\s\"'<>|]{3,}")),
    ("unix_path", re.compile(r"(?:/(?:etc|usr|var|home|root|opt|tmp|proc)/)[\w./-]{2,}")),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----")),
    ("aws_key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}")),
    ("bitcoin_address", re.compile(r"\b(?:bc1[a-z0-9]{25,62}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b")),
    ("base64_blob", re.compile(r"\b(?:[A-Za-z0-9+/]{40,}={0,2})\b")),
    ("mutex_or_guid", re.compile(
        r"\b\{?[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\}?\b", re.I)),
    ("user_agent", re.compile(r"Mozilla/\d\.\d \([^)]{5,120}\)")),
    ("powershell", re.compile(
        r"(?i)powershell(?:\.exe)?\s+(?:-\w+\s+){0,4}(?:-enc(?:odedcommand)?|-nop|-w\s+hidden)")),
]

# --------------------------------------------------------------------------- #
# Carving signatures (offset > 0 is the interesting case)
# --------------------------------------------------------------------------- #

CARVE_SIGNATURES: list[tuple[str, bytes]] = [
    ("zip", b"PK\x03\x04"),
    ("rar", b"Rar!\x1a\x07"),
    ("7z", b"7z\xbc\xaf\x27\x1c"),
    ("gzip", b"\x1f\x8b\x08"),
    ("bzip2", b"BZh9"),
    ("xz", b"\xfd7zXZ\x00"),
    ("zstd", b"\x28\xb5\x2f\xfd"),
    ("png", b"\x89PNG\r\n\x1a\n"),
    ("jpeg", b"\xff\xd8\xff"),
    ("gif", b"GIF89a"),
    ("bmp", b"BM"),
    ("pdf", b"%PDF-"),
    ("elf", b"\x7fELF"),
    ("pe", b"MZ\x90\x00"),
    ("sqlite", b"SQLite format 3\x00"),
    ("ole2", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"),
    ("cab", b"MSCF"),
    ("iso", b"CD001"),
    ("tar", b"ustar"),
    ("pcap", b"\xd4\xc3\xb2\xa1"),
    ("evtx", b"ElfFile\x00"),
    ("registry_hive", b"regf"),
    ("lnk", b"\x4c\x00\x00\x00\x01\x14\x02\x00"),
    ("rtf", b"{\\rtf"),
    ("class", b"\xca\xfe\xba\xbe"),
    ("wasm", b"\x00asm"),
]

# A handful of these fire constantly inside normal binaries; require more
# context before reporting them.
NOISY = {"bmp", "tar", "jpeg"}


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    n = len(data)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def _decode(raw: bytes) -> str:
    return raw.decode("ascii", errors="replace")


def scan(path: Path) -> dict:
    size = path.stat().st_size
    by_class: dict[str, list[dict]] = {}
    seen_values: dict[str, set[str]] = {}
    carved: list[dict] = []
    flags: list[dict] = []
    entropy_points: list[dict] = []
    truncated: set[str] = set()

    flag_res = [re.compile(p) for p in FLAG_PATTERNS]
    entropy_stride = max(1, (size // ENTROPY_BLOCK) // MAX_ENTROPY_POINTS + 1)

    block_index = 0
    offset = 0
    tail = b""

    with path.open("rb") as fh:
        while True:
            chunk = fh.read(CHUNK)
            if not chunk:
                break
            window = tail + chunk
            window_start = offset - len(tail)

            # ---- entropy profile ---------------------------------------- #
            for i in range(0, len(chunk), ENTROPY_BLOCK):
                if block_index % entropy_stride == 0:
                    block = chunk[i:i + ENTROPY_BLOCK]
                    if block:
                        entropy_points.append({
                            "offset": offset + i,
                            "entropy": round(entropy(block), 3),
                        })
                block_index += 1

            # ---- carving ------------------------------------------------- #
            if len(carved) < MAX_CARVED:
                for name, magic in CARVE_SIGNATURES:
                    start = 0
                    while True:
                        idx = window.find(magic, start)
                        if idx < 0:
                            break
                        abs_off = window_start + idx
                        start = idx + 1
                        if abs_off == 0:
                            continue  # that's the file's own header
                        if name in NOISY and abs_off % 512 != 0:
                            continue
                        if len(carved) >= MAX_CARVED:
                            truncated.add("carved")
                            break
                        carved.append({
                            "type": name,
                            "offset": abs_off,
                            "magic": magic.hex(),
                        })
                    if len(carved) >= MAX_CARVED:
                        break

            # ---- strings ------------------------------------------------- #
            for regex, encoding in ((_ASCII_RUN, "ascii"), (_UTF16_RUN, "utf-16le")):
                for m in regex.finditer(window):
                    raw = m.group()
                    if encoding == "utf-16le":
                        raw = raw[::2]
                    text = _decode(raw)
                    abs_off = window_start + m.start()

                    for fre in flag_res:
                        for fm in fre.finditer(text):
                            flags.append({
                                "value": fm.group()[:200],
                                "offset": abs_off + fm.start(),
                                "encoding": encoding,
                            })

                    for label, cre in CLASSIFIERS:
                        for cm in cre.finditer(text):
                            value = cm.group()[:512]
                            bucket = seen_values.setdefault(label, set())
                            if value in bucket:
                                continue
                            entries = by_class.setdefault(label, [])
                            if len(entries) >= MAX_STRINGS_PER_CLASS:
                                truncated.add(label)
                                continue
                            bucket.add(value)
                            entries.append({
                                "value": value,
                                "offset": abs_off + cm.start(),
                                "encoding": encoding,
                            })

            tail = window[-OVERLAP:] if len(window) > OVERLAP else window
            offset += len(chunk)

    # de-duplicate flags, preserving first sighting
    unique_flags: list[dict] = []
    seen_flags: set[str] = set()
    for f in flags:
        if f["value"] in seen_flags:
            continue
        seen_flags.add(f["value"])
        unique_flags.append(f)

    high = [p for p in entropy_points if p["entropy"] >= 7.5]
    return {
        "file": {"name": path.name, "size": size},
        "strings": by_class,
        "carved": carved,
        "flags": unique_flags,
        "entropy": {
            "points": entropy_points,
            "mean": round(
                sum(p["entropy"] for p in entropy_points) / len(entropy_points), 3
            ) if entropy_points else 0.0,
            "high_entropy_regions": len(high),
            "high_entropy_ratio": round(len(high) / len(entropy_points), 3)
            if entropy_points else 0.0,
        },
        "truncated": sorted(truncated),
    }


def main() -> int:
    input_path = os.getenv("INPUT_PATH", "")
    output_dir = os.getenv("OUTPUT_PATH", "/output")

    if not input_path:
        print("INPUT_PATH is not set", file=sys.stderr)
        return 2
    p = Path(input_path)
    if not p.is_file():
        print(f"input file not found: {input_path}", file=sys.stderr)
        return 2

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    try:
        result = scan(p)
    except Exception as exc:  # noqa: BLE001 - report, never swallow
        print(f"triage scan failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    (out / "triage.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    counts = {k: len(v) for k, v in result["strings"].items()}
    print(
        f"triage: {sum(counts.values())} classified strings "
        f"({len(counts)} classes), {len(result['carved'])} embedded signatures, "
        f"{len(result['flags'])} flag candidates"
    )
    if result["truncated"]:
        print(f"triage: result caps hit for: {', '.join(result['truncated'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
