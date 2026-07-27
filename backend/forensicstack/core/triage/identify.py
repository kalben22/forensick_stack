"""
Content-based artifact identification.

This is what makes "upload anything and the platform figures out what to do
with it" possible.  The old flow required the analyst to already know the answer:
pick the tool, pick the feature, hope the extension matched a hardcoded list.

Design constraints:

* **Never read the whole file.**  Inputs are routinely multi-GB memory images.
  We read a header window, a footer window, and a handful of sampled windows
  spread through the file.  Cost is O(1) in file size, not O(n).
* **Content beats the file name, always.**  ``evidence.raw`` might be a disk
  image, a memory dump or a JPEG somebody renamed.  Extensions are a tie-break
  hint and nothing more.
* **No native dependency.**  No libmagic in the image; the signature table in
  ``signatures.py`` is ours, and it maps straight to routing decisions instead
  of to a human-readable description we'd have to re-parse.
* **Say when you don't know.**  ``UNKNOWN`` with low confidence is a valid,
  useful answer — it routes to the generic carving/strings path rather than
  guessing a tool that will fail 40 minutes later.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
import string
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

from forensicstack.core.triage.kinds import ArtifactKind, KindFamily
from forensicstack.core.triage.signatures import (
    EXTENSION_HINTS,
    MEMORY_MARKERS,
    SIGNATURES,
    TAR_CONTENT_HINTS,
    ZIP_CONTENT_HINTS,
    Signature,
)

# Window sizes.  Header must cover the deepest signature offset (tar's `ustar`
# lives at 257) plus a comfortable margin for ZIP central-directory scanning.
HEADER_BYTES = 64 * 1024
FOOTER_BYTES = 64 * 1024

#: Interior sampling budget.  Wide enough that kernel markers scattered through
#: a multi-GB memory image are actually hit, bounded so cost stays O(1) in file
#: size: at most SAMPLE_COUNT * SAMPLE_BYTES is ever read regardless of input.
SAMPLE_BYTES = 1024 * 1024
SAMPLE_COUNT = 24

#: Below this, "it's a big magic-less blob" reasoning doesn't apply.
MIN_MEMORY_DUMP_BYTES = 16 * 1024 * 1024

_PRINTABLE = frozenset(bytes(string.printable, "ascii"))


# --------------------------------------------------------------------------- #
# Result
# --------------------------------------------------------------------------- #


@dataclass
class Evidence:
    """One reason the engine reached its conclusion.

    Surfaced to the analyst.  An identification you can't explain is one you
    can't defend in a report — and in practice it's also one you can't debug.
    """

    rule: str
    detail: str
    weight: float = 0.0

    def __str__(self) -> str:  # pragma: no cover - display only
        return f"{self.rule}: {self.detail}"


@dataclass
class ArtifactIdentity:
    kind: ArtifactKind = ArtifactKind.UNKNOWN
    confidence: float = 0.0
    os_hint: str | None = None
    label: str = ""
    mime: str | None = None

    size: int = 0
    sha256: str | None = None
    md5: str | None = None

    entropy: float = 0.0
    printable_ratio: float = 0.0
    page_aligned: bool = False

    evidence: list[Evidence] = field(default_factory=list)
    alternatives: list[tuple[ArtifactKind, float]] = field(default_factory=list)
    details: dict[str, object] = field(default_factory=dict)

    @property
    def family(self) -> KindFamily:
        return self.kind.family

    @property
    def is_confident(self) -> bool:
        return self.confidence >= 0.75

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "family": self.family.value,
            "confidence": round(self.confidence, 3),
            "os_hint": self.os_hint,
            "label": self.label,
            "mime": self.mime,
            "size": self.size,
            "sha256": self.sha256,
            "md5": self.md5,
            "entropy": round(self.entropy, 3),
            "printable_ratio": round(self.printable_ratio, 3),
            "page_aligned": self.page_aligned,
            "evidence": [str(e) for e in self.evidence],
            "alternatives": [
                {"kind": k.value, "confidence": round(c, 3)}
                for k, c in self.alternatives
            ],
            "details": self.details,
        }


# --------------------------------------------------------------------------- #
# Sampling helpers
# --------------------------------------------------------------------------- #


def _read_at(fh: BinaryIO, offset: int, size: int) -> bytes:
    try:
        fh.seek(offset)
    except OSError:
        return b""
    return fh.read(size)


def _sample_windows(fh: BinaryIO, size: int) -> list[bytes]:
    """Evenly spaced interior windows, so a marker anywhere in a 4 GB image has
    a fair chance of being seen without reading 4 GB.

    The window is clamped to the available span so a small file yields a few
    modest reads rather than SAMPLE_COUNT heavily-overlapping ones.
    """
    if size <= HEADER_BYTES + FOOTER_BYTES:
        return []
    span = size - HEADER_BYTES - FOOTER_BYTES
    window = max(32 * 1024, min(SAMPLE_BYTES, span // SAMPLE_COUNT or span))
    step = max(1, span // SAMPLE_COUNT)
    out: list[bytes] = []
    for i in range(SAMPLE_COUNT):
        off = HEADER_BYTES + i * step
        if off >= size - FOOTER_BYTES:
            break
        chunk = _read_at(fh, off, min(window, size - off))
        if chunk:
            out.append(chunk)
    return out


def shannon_entropy(data: bytes) -> float:
    """Bits per byte, 0..8.  >7.5 means compressed or encrypted."""
    if not data:
        return 0.0
    counts = Counter(data)
    n = len(data)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def printable_ratio(data: bytes) -> float:
    if not data:
        return 0.0
    return sum(1 for b in data if b in _PRINTABLE) / len(data)


# --------------------------------------------------------------------------- #
# Signature matching
# --------------------------------------------------------------------------- #


def _signature_matches(sig: Signature, header: bytes) -> bool:
    end = sig.offset + len(sig.magic)
    if len(header) < end:
        return False
    if header[sig.offset:end] != sig.magic:
        return False
    for off, extra in sig.also:
        if header[off:off + len(extra)] != extra:
            return False
    return True


def _match_signatures(header: bytes) -> list[Signature]:
    return [s for s in SIGNATURES if _signature_matches(s, header)]


# --------------------------------------------------------------------------- #
# Container sub-typing
# --------------------------------------------------------------------------- #


def _refine_zip(fh: BinaryIO, size: int, header: bytes) -> tuple[ArtifactKind, str | None, str] | None:
    """A ZIP could be an APK, an IPA, an OOXML document or an iOS backup.

    We look at entry names in the local-file headers we already have, plus the
    tail (where the central directory lives) — no full inflate, no temp file.
    """
    footer = _read_at(fh, max(0, size - FOOTER_BYTES), FOOTER_BYTES)
    haystack = header + footer
    for needle, kind, os_hint in ZIP_CONTENT_HINTS:
        if needle in haystack:
            return kind, os_hint, f"zip entry {needle.decode(errors='replace')!r}"
    return None


def _refine_tar(fh: BinaryIO, size: int, header: bytes) -> tuple[ArtifactKind, str | None, str] | None:
    samples = _sample_windows(fh, size)
    haystack = header + b"".join(samples[:4])
    for needle, kind, os_hint in TAR_CONTENT_HINTS:
        if needle in haystack:
            return kind, os_hint, f"tar member {needle.decode(errors='replace')!r}"
    return None


_ELF_CORE = 4


def _refine_elf(header: bytes) -> tuple[ArtifactKind, str] | None:
    """An ELF with e_type == ET_CORE is a process/memory dump, not a binary."""
    if len(header) < 18:
        return None
    little = header[5] == 1
    e_type = int.from_bytes(header[16:18], "little" if little else "big")
    if e_type == _ELF_CORE:
        return ArtifactKind.MEMORY_DUMP, "ELF e_type=ET_CORE"
    return None


def _refine_pe(header: bytes) -> tuple[ArtifactKind, str] | None:
    """Distinguish a real PE from any file that happens to start with 'MZ'."""
    if len(header) < 0x40:
        return None
    pe_off = int.from_bytes(header[0x3C:0x40], "little")
    if 0 < pe_off < len(header) - 4 and header[pe_off:pe_off + 4] == b"PE\x00\x00":
        if b"BSJB" in header[:HEADER_BYTES]:
            return ArtifactKind.DOTNET, "PE header + .NET metadata (BSJB)"
        return ArtifactKind.PE, f"PE header at offset 0x{pe_off:x}"
    return None


# --------------------------------------------------------------------------- #
# Magic-less blobs: memory vs disk vs noise
# --------------------------------------------------------------------------- #

_MBR_SIG = b"\x55\xaa"
_GPT_SIG = b"EFI PART"
_FS_MAGICS: tuple[tuple[int, bytes, str], ...] = (
    (3, b"NTFS    ", "NTFS boot sector"),
    (3, b"MSDOS5.0", "FAT boot sector"),
    (54, b"FAT1", "FAT boot sector"),
    (0x438, b"\x53\xef", "ext2/3/4 superblock"),
    (0x10040, b"XFSB", "XFS superblock"),
    (65536, b"\x42\x54\x52\x46\x53\x5f\x4d", "Btrfs superblock"),
)


def _looks_like_disk_image(header: bytes, size: int) -> tuple[float, list[Evidence]]:
    ev: list[Evidence] = []
    score = 0.0
    if len(header) >= 512 and header[510:512] == _MBR_SIG:
        score += 0.45
        ev.append(Evidence("disk.mbr", "0x55AA boot signature at offset 510", 0.45))
    if _GPT_SIG in header[:HEADER_BYTES]:
        score += 0.45
        ev.append(Evidence("disk.gpt", "'EFI PART' GPT header present", 0.45))
    for off, magic, what in _FS_MAGICS:
        if header[off:off + len(magic)] == magic:
            score += 0.40
            ev.append(Evidence("disk.fs", what, 0.40))
            break
    if size >= 64 * 1024 * 1024 and size % 512 == 0:
        score += 0.05
    return min(score, 0.95), ev


def _looks_like_memory_dump(
    header: bytes, samples: list[bytes], size: int
) -> tuple[float, str | None, list[Evidence]]:
    """Score a magic-less blob as a raw memory image.

    Raw dumps (``.raw``, ``.vmem``, ``dd`` of /dev/mem) carry no header at all,
    so identification has to be behavioural: kernel strings scattered through
    the image, page-aligned size, and a byte distribution that is neither text
    nor compressed noise.
    """
    ev: list[Evidence] = []
    haystack = header + b"".join(samples)
    if not haystack:
        return 0.0, None, ev

    score = 0.0
    os_votes: Counter[str] = Counter()
    for marker, os_hint, weight in MEMORY_MARKERS:
        if marker in haystack:
            score += weight
            os_votes[os_hint] += 1
            ev.append(
                Evidence(
                    "memory.marker",
                    f"kernel marker {marker.decode(errors='replace')!r} present",
                    weight,
                )
            )

    if size >= MIN_MEMORY_DUMP_BYTES and size % 4096 == 0:
        score += 0.10
        ev.append(Evidence("memory.aligned", "size is a multiple of 4096", 0.10))

    # Memory images have a characteristic mid-range entropy: lots of zero pages
    # and structured kernel data, unlike compressed archives (>7.5) or plain
    # text (<5).
    ent = shannon_entropy(haystack[: 4 * SAMPLE_BYTES])
    if size >= MIN_MEMORY_DUMP_BYTES and 3.0 <= ent <= 7.2:
        score += 0.08
        ev.append(Evidence("memory.entropy", f"mixed entropy {ent:.2f} bits/byte", 0.08))

    zero_run = sum(1 for c in samples if c.count(0) > len(c) * 0.9)
    if zero_run:
        score += 0.07
        ev.append(
            Evidence("memory.zero_pages", f"{zero_run} sampled windows are ~all-zero", 0.07)
        )

    os_hint = os_votes.most_common(1)[0][0] if os_votes else None
    return min(score, 0.97), os_hint, ev


# --------------------------------------------------------------------------- #
# Text sub-typing
# --------------------------------------------------------------------------- #

_JSON_RE = re.compile(rb"^\s*[\[{]")
_XML_RE = re.compile(rb"^\s*<\?xml|^\s*<[a-zA-Z]")
_CSV_RE = re.compile(rb"^[^\n]{1,4096}[,;\t][^\n]{0,4096}\n")


def _refine_text(header: bytes) -> tuple[ArtifactKind, str]:
    if _JSON_RE.match(header):
        return ArtifactKind.JSON, "starts with '{' or '['"
    if _XML_RE.match(header):
        return ArtifactKind.XML, "starts with an XML declaration or tag"
    if _CSV_RE.match(header):
        return ArtifactKind.CSV, "delimiter-separated first line"
    return ArtifactKind.TEXT, "mostly printable bytes"


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #


def identify(
    path: str | os.PathLike[str],
    *,
    original_filename: str | None = None,
    compute_hashes: bool = True,
) -> ArtifactIdentity:
    """Identify the artifact at ``path``.

    ``original_filename`` lets the caller pass the name the user uploaded when
    the on-disk name is a UUID.  It is used only as a hint.
    """
    p = Path(path)
    size = p.stat().st_size
    name = original_filename or p.name
    ident = ArtifactIdentity(size=size)
    ident.page_aligned = size > 0 and size % 4096 == 0

    if size == 0:
        ident.kind = ArtifactKind.UNKNOWN
        ident.label = "empty file"
        ident.evidence.append(Evidence("size", "file is empty"))
        return ident

    with p.open("rb") as fh:
        header = _read_at(fh, 0, HEADER_BYTES)
        samples = _sample_windows(fh, size)

        ident.entropy = shannon_entropy(header[:SAMPLE_BYTES])
        ident.printable_ratio = printable_ratio(header[:8192])

        candidates: list[tuple[ArtifactKind, float, str | None, str, str | None]] = []

        # 1. exact signatures
        for sig in _match_signatures(header):
            candidates.append(
                (sig.kind, sig.confidence, sig.os_hint, sig.label or sig.kind.value, sig.mime)
            )
            ident.evidence.append(
                Evidence("signature", f"{sig.label or sig.kind.value} @ offset {sig.offset}",
                         sig.confidence)
            )

        top_kind = candidates[0][0] if candidates else None

        def _supersede(generic: ArtifactKind, kind: ArtifactKind, conf: float,
                       os_hint: str | None, label: str, rule: str, why: str) -> None:
            """A refined verdict *replaces* the generic container hit.

            It must not merely be prepended: the final sort is by confidence, so
            leaving the generic candidate in place would let 'tar' (0.96) beat
            the 'this tar is an iOS backup' conclusion it was derived from.
            """
            nonlocal candidates
            candidates = [c for c in candidates if c[0] is not generic]
            candidates.insert(0, (kind, conf, os_hint, label, None))
            ident.evidence.append(Evidence(rule, why, conf))

        if top_kind is ArtifactKind.ARCHIVE_ZIP:
            refined = _refine_zip(fh, size, header)
            if refined:
                kind, os_hint, why = refined
                _supersede(ArtifactKind.ARCHIVE_ZIP, kind, 0.95, os_hint,
                           kind.value, "zip.refine", why)
        elif top_kind is ArtifactKind.ARCHIVE_TAR:
            refined = _refine_tar(fh, size, header)
            if refined:
                kind, os_hint, why = refined
                _supersede(ArtifactKind.ARCHIVE_TAR, kind, 0.97, os_hint,
                           kind.value, "tar.refine", why)
        elif top_kind is ArtifactKind.ELF:
            refined_elf = _refine_elf(header)
            if refined_elf:
                kind, why = refined_elf
                _supersede(ArtifactKind.ELF, kind, 0.99, "linux",
                           "ELF core dump", "elf.refine", why)
        elif top_kind is ArtifactKind.PE:
            refined_pe = _refine_pe(header)
            if refined_pe:
                kind, why = refined_pe
                _supersede(ArtifactKind.PE, kind, 0.95, "windows",
                           kind.value, "pe.refine", why)
            else:
                # 'MZ' with no PE header — almost certainly a false positive.
                candidates = [c for c in candidates if c[0] is not ArtifactKind.PE]
                ident.evidence.append(
                    Evidence("pe.refine", "'MZ' present but no PE header — discarded", 0.0)
                )

        # 3. magic-less blobs
        if not candidates:
            disk_score, disk_ev = _looks_like_disk_image(header, size)
            mem_score, mem_os, mem_ev = _looks_like_memory_dump(header, samples, size)

            if disk_score >= 0.40 and disk_score >= mem_score:
                ident.evidence.extend(disk_ev)
                candidates.append(
                    (ArtifactKind.DISK_IMAGE_RAW, disk_score, None, "raw disk image", None)
                )
            elif mem_score >= 0.30:
                ident.evidence.extend(mem_ev)
                candidates.append(
                    (ArtifactKind.MEMORY_DUMP, mem_score, mem_os, "raw memory image", None)
                )
            else:
                ident.evidence.extend(disk_ev + mem_ev)

        # 4. text / opaque fallbacks
        if not candidates:
            if ident.printable_ratio > 0.92:
                kind, why = _refine_text(header)
                candidates.append((kind, 0.70, None, kind.value, "text/plain"))
                ident.evidence.append(Evidence("text", why, 0.70))
            elif ident.entropy >= 7.85 and size > 4096:
                candidates.append(
                    (ArtifactKind.ENCRYPTED, 0.55, None, "high-entropy opaque blob", None)
                )
                ident.evidence.append(
                    Evidence("entropy",
                             f"{ident.entropy:.2f} bits/byte — encrypted or compressed", 0.55)
                )

        # 5. extension hint — tie-break only, never an override of strong content
        ext = _extension_of(name)
        hinted = EXTENSION_HINTS.get(ext)
        if hinted:
            if not candidates:
                candidates.append((hinted, 0.45, None, f"by extension {ext}", None))
                ident.evidence.append(
                    Evidence("extension", f"{ext} (no content signature matched)", 0.45)
                )
            elif candidates[0][0] is hinted:
                boosted = list(candidates[0])
                boosted[1] = min(0.99, float(boosted[1]) + 0.04)
                candidates[0] = tuple(boosted)  # type: ignore[assignment]
                ident.evidence.append(
                    Evidence("extension", f"{ext} agrees with content", 0.04)
                )
            elif candidates[0][0].family is not hinted.family:
                ident.evidence.append(
                    Evidence(
                        "extension.conflict",
                        f"name says {ext} ({hinted.value}) but content says "
                        f"{candidates[0][0].value} — trusting content",
                    )
                )
                ident.details["extension_conflict"] = {
                    "extension": ext,
                    "extension_kind": hinted.value,
                    "content_kind": candidates[0][0].value,
                }

        if compute_hashes:
            ident.sha256, ident.md5 = _hash_file(fh)

    if candidates:
        candidates.sort(key=lambda c: c[1], reverse=True)
        kind, conf, os_hint, label, mime = candidates[0]
        ident.kind, ident.confidence = kind, float(conf)
        ident.os_hint, ident.label, ident.mime = os_hint, label, mime
        seen = {kind}
        for k, c, *_ in candidates[1:]:
            if k not in seen:
                ident.alternatives.append((k, float(c)))
                seen.add(k)
    else:
        ident.kind = ArtifactKind.UNKNOWN
        ident.confidence = 0.0
        ident.label = "unrecognised"
        ident.evidence.append(
            Evidence("fallback", "no signature, heuristic or extension matched")
        )

    return ident


def _extension_of(name: str) -> str:
    """Lowercased extension, double-extension aware.

    ``backup.tar.gz`` must resolve to ``.tar.gz`` and not ``.gz`` — the old
    front-end did ``'.' + name.split('.')[-1]`` and consequently rejected every
    iOS backup, the single most common iLEAPP input.
    """
    lowered = name.lower()
    for double in (".tar.gz", ".tar.bz2", ".tar.xz", ".tar.zst"):
        if lowered.endswith(double):
            return double
    idx = lowered.rfind(".")
    return lowered[idx:] if idx > 0 else ""


def _hash_file(fh: BinaryIO, chunk: int = 4 * 1024 * 1024) -> tuple[str, str]:
    """Streaming SHA-256 + MD5.

    Streaming matters: the artifact upload path used to do ``await file.read()``
    into a single buffer, so peak RSS tracked file size and a 4 GB upload could
    OOM the container.
    """
    sha, md5 = hashlib.sha256(), hashlib.md5()
    fh.seek(0)
    while True:
        block = fh.read(chunk)
        if not block:
            break
        sha.update(block)
        md5.update(block)
    return sha.hexdigest(), md5.hexdigest()
