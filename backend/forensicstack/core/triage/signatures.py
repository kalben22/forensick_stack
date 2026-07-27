"""
Content signatures used by the identification engine.

Everything here is *data*.  The matching logic lives in ``identify.py``.

Deliberately dependency-free: no ``python-magic``, no ``libmagic`` in the image.
The set below covers the artefact types a DFIR/CTF platform actually routes on,
and being our own table means we can attach an ``os_hint`` and a routing-relevant
``ArtifactKind`` rather than a human-readable description string we would then
have to re-parse.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forensicstack.core.triage.kinds import ArtifactKind


@dataclass(frozen=True)
class Signature:
    kind: ArtifactKind
    magic: bytes
    offset: int = 0
    confidence: float = 0.95
    os_hint: str | None = None
    mime: str | None = None
    label: str = ""
    #: Optional extra bytes that must also be present, as (offset, magic).
    also: tuple[tuple[int, bytes], ...] = field(default_factory=tuple)


# Ordered: the first match wins, so put the specific before the generic.
SIGNATURES: tuple[Signature, ...] = (
    # ---- memory ---------------------------------------------------------- #
    Signature(ArtifactKind.CRASH_DUMP, b"PAGEDU64", 0, 0.99, "windows",
              label="Windows 64-bit crash dump"),
    Signature(ArtifactKind.CRASH_DUMP, b"PAGEDUMP", 0, 0.99, "windows",
              label="Windows 32-bit crash dump"),
    Signature(ArtifactKind.HIBERNATION_FILE, b"HIBR", 0, 0.97, "windows",
              label="Windows hibernation file"),
    Signature(ArtifactKind.HIBERNATION_FILE, b"hibr", 0, 0.97, "windows",
              label="Windows hibernation file (slack)"),
    Signature(ArtifactKind.HIBERNATION_FILE, b"WAKE", 0, 0.90, "windows",
              label="Windows hibernation file (resumed)"),
    Signature(ArtifactKind.MEMORY_DUMP, b"EMiL", 0, 0.97, "linux",
              label="LiME memory image"),
    Signature(ArtifactKind.PROCESS_DUMP, b"MDMP", 0, 0.97, "windows",
              label="Windows minidump"),
    # VMware saved state / suspended VM memory
    Signature(ArtifactKind.MEMORY_DUMP, b"\xd2\xbe\xd2\xbe", 0, 0.85, None,
              label="VMware .vmss/.vmem container"),

    # ---- disk images ----------------------------------------------------- #
    Signature(ArtifactKind.DISK_IMAGE_EWF, b"EVF\x09\x0d\x0a\xff\x00", 0, 0.99,
              label="EnCase EWF (E01)"),
    Signature(ArtifactKind.DISK_IMAGE_EWF, b"LVF\x09\x0d\x0a\xff\x00", 0, 0.99,
              label="EnCase logical evidence (L01)"),
    Signature(ArtifactKind.DISK_IMAGE_EWF, b"EVF2\x0d\x0a\x81", 0, 0.99,
              label="EnCase Ex01"),
    Signature(ArtifactKind.DISK_IMAGE_VMDK, b"KDMV", 0, 0.97, label="VMware VMDK"),
    Signature(ArtifactKind.DISK_IMAGE_VMDK, b"# Disk DescriptorFile", 0, 0.90,
              label="VMware VMDK descriptor"),
    Signature(ArtifactKind.DISK_IMAGE_QCOW, b"QFI\xfb", 0, 0.98, label="QEMU QCOW"),
    Signature(ArtifactKind.DISK_IMAGE_VHD, b"vhdxfile", 0, 0.98, label="Hyper-V VHDX"),
    Signature(ArtifactKind.DISK_IMAGE_RAW, b"AFF", 0, 0.85, label="AFF image"),

    # ---- windows artefacts ----------------------------------------------- #
    Signature(ArtifactKind.EVTX, b"ElfFile\x00", 0, 0.99, "windows",
              label="Windows Event Log (EVTX)"),
    Signature(ArtifactKind.REGISTRY_HIVE, b"regf", 0, 0.99, "windows",
              label="Windows registry hive"),
    Signature(ArtifactKind.PREFETCH, b"MAM\x04", 0, 0.95, "windows",
              label="Windows Prefetch (compressed)"),
    Signature(ArtifactKind.PREFETCH, b"SCCA", 4, 0.97, "windows",
              label="Windows Prefetch"),
    Signature(ArtifactKind.LNK, b"\x4c\x00\x00\x00\x01\x14\x02\x00", 0, 0.98,
              "windows", label="Windows shortcut (LNK)"),
    Signature(ArtifactKind.MFT, b"FILE0", 0, 0.90, "windows", label="NTFS $MFT"),
    Signature(ArtifactKind.MFT, b"BAAD", 0, 0.70, "windows",
              label="NTFS $MFT (damaged record)"),

    # ---- network --------------------------------------------------------- #
    Signature(ArtifactKind.PCAP, b"\xd4\xc3\xb2\xa1", 0, 0.99, label="pcap (LE)"),
    Signature(ArtifactKind.PCAP, b"\xa1\xb2\xc3\xd4", 0, 0.99, label="pcap (BE)"),
    Signature(ArtifactKind.PCAP, b"\x4d\x3c\xb2\xa1", 0, 0.99,
              label="pcap nanosecond (LE)"),
    Signature(ArtifactKind.PCAP, b"\xa1\xb2\x3c\x4d", 0, 0.99,
              label="pcap nanosecond (BE)"),
    Signature(ArtifactKind.PCAPNG, b"\x0a\x0d\x0d\x0a", 0, 0.97, label="pcapng"),

    # ---- mobile ---------------------------------------------------------- #
    Signature(ArtifactKind.ANDROID_BACKUP, b"ANDROID BACKUP", 0, 0.99, "android",
              label="Android adb backup"),

    # ---- archives (zip family needs sub-typing, see identify.py) ---------- #
    Signature(ArtifactKind.ARCHIVE_ZIP, b"PK\x03\x04", 0, 0.80, label="ZIP"),
    Signature(ArtifactKind.ARCHIVE_ZIP, b"PK\x05\x06", 0, 0.70, label="ZIP (empty)"),
    Signature(ArtifactKind.ARCHIVE_7Z, b"7z\xbc\xaf\x27\x1c", 0, 0.99, label="7-Zip"),
    Signature(ArtifactKind.ARCHIVE_RAR, b"Rar!\x1a\x07", 0, 0.99, label="RAR"),
    Signature(ArtifactKind.ARCHIVE_GZ, b"\x1f\x8b", 0, 0.92, label="gzip"),
    Signature(ArtifactKind.ARCHIVE_TAR, b"ustar", 257, 0.96, label="tar (POSIX)"),
    Signature(ArtifactKind.COMPRESSED_OPAQUE, b"\xfd7zXZ\x00", 0, 0.95, label="xz"),
    Signature(ArtifactKind.COMPRESSED_OPAQUE, b"BZh", 0, 0.90, label="bzip2"),
    Signature(ArtifactKind.COMPRESSED_OPAQUE, b"\x04\x22\x4d\x18", 0, 0.90,
              label="lz4"),
    Signature(ArtifactKind.COMPRESSED_OPAQUE, b"\x28\xb5\x2f\xfd", 0, 0.92,
              label="zstd"),

    # ---- documents ------------------------------------------------------- #
    Signature(ArtifactKind.PDF, b"%PDF-", 0, 0.98, mime="application/pdf",
              label="PDF"),
    Signature(ArtifactKind.OFFICE_OLE, b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", 0, 0.95,
              label="OLE2 compound (legacy Office / MSI)"),
    Signature(ArtifactKind.EMAIL, b"From ", 0, 0.55, label="mbox"),
    Signature(ArtifactKind.EMAIL, b"Return-Path:", 0, 0.80, label="RFC822 message"),
    Signature(ArtifactKind.EMAIL, b"Received:", 0, 0.70, label="RFC822 message"),

    # ---- media ----------------------------------------------------------- #
    Signature(ArtifactKind.IMAGE_JPEG, b"\xff\xd8\xff", 0, 0.98,
              mime="image/jpeg", label="JPEG"),
    Signature(ArtifactKind.IMAGE_PNG, b"\x89PNG\r\n\x1a\n", 0, 0.99,
              mime="image/png", label="PNG"),
    Signature(ArtifactKind.IMAGE_GIF, b"GIF87a", 0, 0.98, mime="image/gif",
              label="GIF"),
    Signature(ArtifactKind.IMAGE_GIF, b"GIF89a", 0, 0.98, mime="image/gif",
              label="GIF"),
    Signature(ArtifactKind.IMAGE_BMP, b"BM", 0, 0.75, mime="image/bmp", label="BMP"),
    Signature(ArtifactKind.IMAGE_TIFF, b"II*\x00", 0, 0.90, mime="image/tiff",
              label="TIFF (LE)"),
    Signature(ArtifactKind.IMAGE_TIFF, b"MM\x00*", 0, 0.90, mime="image/tiff",
              label="TIFF (BE)"),
    Signature(ArtifactKind.IMAGE_WEBP, b"RIFF", 0, 0.85, mime="image/webp",
              label="WebP", also=((8, b"WEBP"),)),
    Signature(ArtifactKind.AUDIO, b"RIFF", 0, 0.85, label="WAV",
              also=((8, b"WAVE"),)),
    Signature(ArtifactKind.AUDIO, b"ID3", 0, 0.90, label="MP3 (ID3)"),
    Signature(ArtifactKind.AUDIO, b"fLaC", 0, 0.95, label="FLAC"),
    Signature(ArtifactKind.AUDIO, b"OggS", 0, 0.90, label="Ogg"),
    Signature(ArtifactKind.VIDEO, b"ftyp", 4, 0.90, label="ISO-BMFF (MP4/MOV)"),
    Signature(ArtifactKind.VIDEO, b"\x1a\x45\xdf\xa3", 0, 0.92, label="Matroska/WebM"),

    # ---- executables ----------------------------------------------------- #
    Signature(ArtifactKind.PE, b"MZ", 0, 0.75, "windows", label="PE / MS-DOS"),
    Signature(ArtifactKind.ELF, b"\x7fELF", 0, 0.98, "linux", label="ELF"),
    Signature(ArtifactKind.MACHO, b"\xcf\xfa\xed\xfe", 0, 0.95, "macos",
              label="Mach-O 64"),
    Signature(ArtifactKind.MACHO, b"\xce\xfa\xed\xfe", 0, 0.95, "macos",
              label="Mach-O 32"),
    Signature(ArtifactKind.MACHO, b"\xca\xfe\xba\xbe", 0, 0.70, "macos",
              label="Mach-O universal"),

    # ---- data ------------------------------------------------------------ #
    Signature(ArtifactKind.SQLITE, b"SQLite format 3\x00", 0, 0.99,
              label="SQLite database"),
    Signature(ArtifactKind.PLIST, b"bplist00", 0, 0.98, "ios",
              label="Apple binary plist"),
)


#: Markers scanned for across sampled windows of a large, magic-less file.
#: A raw memory image has no header, so this is how we tell one from a random
#: 4 GB blob.  Each entry is (marker, os_hint, weight).
MEMORY_MARKERS: tuple[tuple[bytes, str, float], ...] = (
    (b"KDBG", "windows", 0.35),
    (b"\\SystemRoot\\System32", "windows", 0.30),
    (b"ntoskrnl.exe", "windows", 0.30),
    (b"PsActiveProcessHead", "windows", 0.35),
    (b"\\Device\\HarddiskVolume", "windows", 0.20),
    (b"\\REGISTRY\\MACHINE", "windows", 0.25),
    (b"Windows Boot Manager", "windows", 0.15),
    (b"KiSystemStartup", "windows", 0.25),
    (b"Linux version ", "linux", 0.40),
    (b"swapper/0", "linux", 0.25),
    (b"init_task", "linux", 0.25),
    (b"/proc/self/", "linux", 0.10),
    (b"Darwin Kernel Version", "macos", 0.40),
    (b"com.apple.kernel", "macos", 0.20),
)

#: Extensions that only ever act as a *hint*.  Content always wins; these are
#: used to break ties and to catch raw images that carry no marker at all.
EXTENSION_HINTS: dict[str, ArtifactKind] = {
    ".raw": ArtifactKind.MEMORY_DUMP,
    ".mem": ArtifactKind.MEMORY_DUMP,
    ".vmem": ArtifactKind.MEMORY_DUMP,
    ".lime": ArtifactKind.MEMORY_DUMP,
    ".dmp": ArtifactKind.CRASH_DUMP,
    ".core": ArtifactKind.MEMORY_DUMP,
    ".sys": ArtifactKind.HIBERNATION_FILE,
    ".dd": ArtifactKind.DISK_IMAGE_RAW,
    ".img": ArtifactKind.DISK_IMAGE_RAW,
    ".e01": ArtifactKind.DISK_IMAGE_EWF,
    ".l01": ArtifactKind.DISK_IMAGE_EWF,
    ".vmdk": ArtifactKind.DISK_IMAGE_VMDK,
    ".vhd": ArtifactKind.DISK_IMAGE_VHD,
    ".vhdx": ArtifactKind.DISK_IMAGE_VHD,
    ".qcow2": ArtifactKind.DISK_IMAGE_QCOW,
    ".pcap": ArtifactKind.PCAP,
    ".cap": ArtifactKind.PCAP,
    ".pcapng": ArtifactKind.PCAPNG,
    ".evtx": ArtifactKind.EVTX,
    ".ab": ArtifactKind.ANDROID_BACKUP,
    ".apk": ArtifactKind.APK,
    ".ipa": ArtifactKind.IPA,
    ".tar": ArtifactKind.ARCHIVE_TAR,
    ".zip": ArtifactKind.ARCHIVE_ZIP,
    ".eml": ArtifactKind.EMAIL,
    ".mbox": ArtifactKind.EMAIL,
    ".csv": ArtifactKind.CSV,
    ".json": ArtifactKind.JSON,
    ".xml": ArtifactKind.XML,
    ".txt": ArtifactKind.TEXT,
    ".log": ArtifactKind.TEXT,
}

#: OOXML / APK / IPA / iOS backup all masquerade as ZIP.  These entry-name
#: prefixes disambiguate without unzipping the whole archive.
ZIP_CONTENT_HINTS: tuple[tuple[bytes, ArtifactKind, str | None], ...] = (
    (b"AndroidManifest.xml", ArtifactKind.APK, "android"),
    (b"classes.dex", ArtifactKind.APK, "android"),
    (b"Payload/", ArtifactKind.IPA, "ios"),
    (b"word/document.xml", ArtifactKind.OFFICE_OOXML, None),
    (b"xl/workbook.xml", ArtifactKind.OFFICE_OOXML, None),
    (b"ppt/presentation.xml", ArtifactKind.OFFICE_OOXML, None),
    (b"[Content_Types].xml", ArtifactKind.OFFICE_OOXML, None),
    (b"Manifest.plist", ArtifactKind.IOS_BACKUP, "ios"),
    (b"Manifest.db", ArtifactKind.IOS_BACKUP, "ios"),
    (b"Info.plist", ArtifactKind.IOS_BACKUP, "ios"),
)

#: Same idea for tar archives — the member names tell us it is a phone dump.
TAR_CONTENT_HINTS: tuple[tuple[bytes, ArtifactKind, str | None], ...] = (
    (b"private/var/mobile", ArtifactKind.IOS_BACKUP, "ios"),
    (b"var/mobile/Library", ArtifactKind.IOS_BACKUP, "ios"),
    (b"Manifest.db", ArtifactKind.IOS_BACKUP, "ios"),
    (b"data/data/com.android", ArtifactKind.FILESYSTEM_ARCHIVE, "android"),
    (b"data/system/packages", ArtifactKind.FILESYSTEM_ARCHIVE, "android"),
)
