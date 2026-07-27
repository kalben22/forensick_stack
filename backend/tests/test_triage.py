"""Tests for content identification, timestamp parsing and auto-routing."""

from __future__ import annotations

import io
import os
import random
import struct
import tarfile
import zipfile
from datetime import timezone

import pytest

from forensicstack.core.findings.timeparse import map_artifact_type, parse_timestamp
from forensicstack.core.triage.identify import (
    identify,
    printable_ratio,
    shannon_entropy,
)
from forensicstack.core.triage.kinds import ArtifactKind, FindingKind, KindFamily


def write(tmp_path, name: str, data: bytes):
    p = tmp_path / name
    p.write_bytes(data)
    return p


# --------------------------------------------------------------------------- #
# Signature identification
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "name,payload,expected",
    [
        ("a.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 2000, ArtifactKind.IMAGE_PNG),
        ("b.pdf", b"%PDF-1.7\n" + b"x" * 3000, ArtifactKind.PDF),
        ("c.evtx", b"ElfFile\x00" + b"\x00" * 5000, ArtifactKind.EVTX),
        ("d.hive", b"regf" + b"\x00" * 5000, ArtifactKind.REGISTRY_HIVE),
        ("e.pcap", b"\xd4\xc3\xb2\xa1" + b"\x00" * 5000, ArtifactKind.PCAP),
        ("f.pcapng", b"\x0a\x0d\x0d\x0a" + b"\x00" * 5000, ArtifactKind.PCAPNG),
        ("g.dmp", b"PAGEDU64" + b"\x00" * 5000, ArtifactKind.CRASH_DUMP),
        ("h.sqlite", b"SQLite format 3\x00" + b"\x00" * 5000, ArtifactKind.SQLITE),
        ("i.ab", b"ANDROID BACKUP\n1\n1\nnone\n" + b"\x00" * 500,
         ArtifactKind.ANDROID_BACKUP),
        ("j.e01", b"EVF\x09\x0d\x0a\xff\x00" + b"\x00" * 5000,
         ArtifactKind.DISK_IMAGE_EWF),
        ("k.lime", b"EMiL" + b"\x00" * 5000, ArtifactKind.MEMORY_DUMP),
        ("l.plist", b"bplist00" + b"\x00" * 500, ArtifactKind.PLIST),
        ("m.lnk", b"\x4c\x00\x00\x00\x01\x14\x02\x00" + b"\x00" * 500, ArtifactKind.LNK),
    ],
)
def test_signature_identification(tmp_path, name, payload, expected):
    ident = identify(write(tmp_path, name, payload))
    assert ident.kind is expected
    assert ident.confidence >= 0.7
    assert ident.sha256 and len(ident.sha256) == 64


def test_empty_file_is_not_guessed(tmp_path):
    ident = identify(write(tmp_path, "empty.raw", b""))
    assert ident.kind is ArtifactKind.UNKNOWN
    assert ident.confidence == 0.0


# --------------------------------------------------------------------------- #
# Content beats the file name
# --------------------------------------------------------------------------- #


def test_content_overrides_a_lying_extension(tmp_path):
    """A JPEG renamed to .raw must not be routed to Volatility."""
    ident = identify(write(tmp_path, "evidence.raw", b"\xff\xd8\xff\xe0JFIF" + b"\x00" * 20000))
    assert ident.kind is ArtifactKind.IMAGE_JPEG
    assert "extension_conflict" in ident.details
    assert ident.details["extension_conflict"]["extension"] == ".raw"


def test_double_extension_is_understood(tmp_path):
    """`backup.tar.gz` must resolve to .tar.gz, not .gz.

    The frontend's `'.' + name.split('.').pop()` produced `.gz`, which was not
    in the allowlist — so every iOS backup, the headline iLEAPP input, was
    rejected before it ever reached the API.
    """
    from forensicstack.core.triage.identify import _extension_of

    assert _extension_of("backup.tar.gz") == ".tar.gz"
    assert _extension_of("dump.TAR.GZ") == ".tar.gz"
    assert _extension_of("disk.E01") == ".e01"
    assert _extension_of("noext") == ""


def test_extension_is_used_only_when_content_is_silent(tmp_path):
    ident = identify(write(tmp_path, "x.pcap", b"\x11" * 50000))
    assert ident.kind is ArtifactKind.PCAP
    assert ident.confidence < 0.6, "an extension-only match must not look certain"


# --------------------------------------------------------------------------- #
# Container sub-typing
# --------------------------------------------------------------------------- #


def _zip_with(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in entries.items():
            z.writestr(name, data)
    return buf.getvalue()


def _tar_with(names: list[str]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as t:
        for n in names:
            info = tarfile.TarInfo(n)
            info.size = 10
            t.addfile(info, io.BytesIO(b"0123456789"))
    return buf.getvalue()


def test_apk_is_not_reported_as_a_zip(tmp_path):
    data = _zip_with({"AndroidManifest.xml": b"x" * 100, "classes.dex": b"y" * 100})
    ident = identify(write(tmp_path, "app.apk", data))
    assert ident.kind is ArtifactKind.APK
    assert ident.os_hint == "android"


def test_ooxml_is_not_reported_as_a_zip(tmp_path):
    data = _zip_with({"[Content_Types].xml": b"x" * 50, "word/document.xml": b"y" * 50})
    assert identify(write(tmp_path, "report.docx", data)).kind is ArtifactKind.OFFICE_OOXML


def test_ios_backup_tar_beats_the_generic_tar_signature(tmp_path):
    """Regression: the refined verdict must *replace* the generic one.

    The generic tar signature scores 0.96; if the refinement is merely
    prepended, the final confidence sort puts plain `archive_tar` back on top
    and the artifact is routed to no mobile tool at all.
    """
    data = _tar_with(["private/var/mobile/Library/SMS/sms.db"])
    ident = identify(write(tmp_path, "phone.tar", data))
    assert ident.kind is ArtifactKind.IOS_BACKUP
    assert ident.os_hint == "ios"


def test_android_filesystem_tar(tmp_path):
    data = _tar_with(["data/data/com.android.providers.telephony/databases/mmssms.db"])
    ident = identify(write(tmp_path, "android.tar", data))
    assert ident.kind is ArtifactKind.FILESYSTEM_ARCHIVE
    assert ident.os_hint == "android"


# --------------------------------------------------------------------------- #
# Executables
# --------------------------------------------------------------------------- #


def test_elf_core_dump_is_memory_not_a_binary(tmp_path):
    elf = bytearray(b"\x7fELF\x02\x01\x01" + b"\x00" * 9)
    elf += struct.pack("<H", 4)  # ET_CORE
    elf += b"\x00" * 4000
    ident = identify(write(tmp_path, "app.core", bytes(elf)))
    assert ident.kind is ArtifactKind.MEMORY_DUMP


def test_plain_elf_stays_an_executable(tmp_path):
    elf = bytearray(b"\x7fELF\x02\x01\x01" + b"\x00" * 9)
    elf += struct.pack("<H", 2)  # ET_EXEC
    elf += b"\x00" * 4000
    assert identify(write(tmp_path, "bin", bytes(elf))).kind is ArtifactKind.ELF


def test_real_pe_is_detected(tmp_path):
    pe = bytearray(b"MZ" + b"\x00" * 0x3A)
    pe += struct.pack("<I", 0x80)
    pe += b"\x00" * (0x80 - 0x40)
    pe += b"PE\x00\x00" + b"\x00" * 4000
    ident = identify(write(tmp_path, "x.exe", bytes(pe)))
    assert ident.kind is ArtifactKind.PE
    assert ident.os_hint == "windows"


def test_bare_mz_is_not_called_a_pe(tmp_path):
    """'MZ' with no PE header is a false positive and must be discarded."""
    ident = identify(write(tmp_path, "y.bin", b"MZ" + b"\x00" * 6000))
    assert ident.kind is not ArtifactKind.PE


# --------------------------------------------------------------------------- #
# Magic-less blobs
# --------------------------------------------------------------------------- #


def _fake_windows_memory(size: int = 40 * 1024 * 1024, seed: int = 11) -> bytes:
    rng = random.Random(seed)
    mem = bytearray(size)
    markers = [
        b"KDBG", b"\\SystemRoot\\System32", b"ntoskrnl.exe",
        b"PsActiveProcessHead", b"\\REGISTRY\\MACHINE",
    ]
    for _ in range(300):
        m = rng.choice(markers)
        off = rng.randrange(0, size - 64)
        mem[off:off + len(m)] = m
    for i in range(0, size, 131072):
        mem[i:i + 2048] = bytes(rng.randrange(0, 80) for _ in range(2048))
    return bytes(mem)


def test_raw_memory_dump_is_identified_without_a_magic_number(tmp_path):
    ident = identify(write(tmp_path, "dump.mem", _fake_windows_memory()))
    assert ident.kind is ArtifactKind.MEMORY_DUMP
    assert ident.os_hint == "windows"
    assert ident.confidence >= 0.75
    assert any("memory.marker" in str(e) for e in ident.evidence)


def test_disk_image_detected_from_mbr(tmp_path):
    blob = bytearray(64 * 1024 * 1024)
    blob[510:512] = b"\x55\xaa"
    blob[3:11] = b"NTFS    "
    ident = identify(write(tmp_path, "disk.bin", bytes(blob)))
    assert ident.kind is ArtifactKind.DISK_IMAGE_RAW


def test_high_entropy_blob_is_reported_as_opaque(tmp_path):
    ident = identify(write(tmp_path, "blob", os.urandom(60000)))
    assert ident.kind in {ArtifactKind.ENCRYPTED, ArtifactKind.UNKNOWN}
    assert ident.entropy > 7.5


def test_identification_cost_is_bounded_by_sampling(tmp_path):
    """A large file must not be read end-to-end (except for hashing)."""
    big = write(tmp_path, "big.mem", _fake_windows_memory(80 * 1024 * 1024))
    ident = identify(big, compute_hashes=False)
    assert ident.kind is ArtifactKind.MEMORY_DUMP
    assert ident.sha256 is None


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def test_entropy_bounds():
    assert shannon_entropy(b"") == 0.0
    assert shannon_entropy(b"\x00" * 1000) == 0.0
    assert shannon_entropy(bytes(range(256)) * 4) > 7.9


def test_printable_ratio():
    assert printable_ratio(b"hello world") == 1.0
    assert printable_ratio(b"\x00\x01\x02\x03") == 0.0


def test_kind_family_mapping():
    assert ArtifactKind.MEMORY_DUMP.family is KindFamily.MEMORY
    assert ArtifactKind.PCAP.family is KindFamily.NETWORK
    assert ArtifactKind.UNKNOWN.family is KindFamily.OTHER


# --------------------------------------------------------------------------- #
# Timestamps — the field v1 threw away
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "value,expected_iso",
    [
        ("2024-03-11 09:12:44", "2024-03-11T09:12:44+00:00"),
        ("2024-03-11T09:12:44Z", "2024-03-11T09:12:44+00:00"),
        ("2024-03-11T09:12:44.123456Z", "2024-03-11T09:12:44.123456+00:00"),
        ("03/11/2024 09:12:44", "2024-03-11T09:12:44+00:00"),
        ("2024:03:11 09:12:44", "2024-03-11T09:12:44+00:00"),   # ExifTool
        ("2024-03-11 09:12:44 UTC", "2024-03-11T09:12:44+00:00"),
        ("2024-03-11 09:12:44 +0100", "2024-03-11T08:12:44+00:00"),
        (1710148364, "2024-03-11T09:12:44+00:00"),              # unix seconds
        (1710148364000, "2024-03-11T09:12:44+00:00"),           # unix millis
    ],
)
def test_parse_timestamp_formats(value, expected_iso):
    ts, _ = parse_timestamp(value)
    assert ts is not None, f"failed to parse {value!r}"
    assert ts.tzinfo is not None
    assert ts.astimezone(timezone.utc).isoformat() == expected_iso


@pytest.mark.parametrize("value", ["", "n/a", "none", "-", "0", "garbage", None])
def test_parse_timestamp_refuses_to_guess(value):
    """An unparseable value must yield None — never the epoch as a stand-in."""
    assert parse_timestamp(value) == (None, None)


def test_parse_timestamp_windows_filetime():
    ts, precision = parse_timestamp(133545432640000000)
    assert ts is not None and 2024 <= ts.year <= 2025
    assert precision == "us"


def test_parse_timestamp_rejects_implausible_years():
    assert parse_timestamp(99999999999999999999) == (None, None)


@pytest.mark.parametrize(
    "tool,artifact_type,expected",
    [
        ("volatility", "windows.pslist", FindingKind.PROCESS),
        ("volatility", "windows.netscan", FindingKind.NETWORK_CONNECTION),
        ("volatility", "windows.malfind", FindingKind.SIGNATURE_MATCH),
        ("eztools", "prefetch", FindingKind.EXECUTION_EVIDENCE),
        ("eztools", "shellbags", FindingKind.REGISTRY_KEY),
        ("ileapp", "Safari History", FindingKind.BROWSER_HISTORY),
        ("aleapp", "SMS Messages", FindingKind.SMS),
        ("exiftool", "metadata", FindingKind.FILE_METADATA),
        ("volatility", "_error", FindingKind.ERROR),
        ("unknown-tool", "whatever", FindingKind.LOG_EVENT),
    ],
)
def test_legacy_artifact_type_maps_to_closed_vocabulary(tool, artifact_type, expected):
    assert map_artifact_type(tool, artifact_type) is expected
