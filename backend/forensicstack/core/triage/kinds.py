"""
Closed vocabularies shared by identification, routing and normalization.

These enums are deliberately *closed*.  The old code used free strings for
``Finding.source`` ("memory", "filesystem", a CSV stem, a host path...) which
made cross-tool correlation impossible: nothing could join "Volatility saw this
process" to "Prefetch saw this execution" to "MFT saw this file".
"""

from __future__ import annotations

from enum import Enum


class ArtifactKind(str, Enum):
    """What an uploaded file *is*, determined by content — not by its name."""

    # memory
    MEMORY_DUMP = "memory_dump"
    HIBERNATION_FILE = "hibernation_file"
    CRASH_DUMP = "crash_dump"
    PROCESS_DUMP = "process_dump"

    # disk / filesystem
    DISK_IMAGE_RAW = "disk_image_raw"
    DISK_IMAGE_EWF = "disk_image_ewf"      # E01 / EnCase
    DISK_IMAGE_VMDK = "disk_image_vmdk"
    DISK_IMAGE_VHD = "disk_image_vhd"
    DISK_IMAGE_QCOW = "disk_image_qcow"
    FILESYSTEM_ARCHIVE = "filesystem_archive"

    # mobile
    IOS_BACKUP = "ios_backup"
    ANDROID_BACKUP = "android_backup"
    APK = "apk"
    IPA = "ipa"

    # windows artefacts
    EVTX = "evtx"
    REGISTRY_HIVE = "registry_hive"
    PREFETCH = "prefetch"
    LNK = "lnk"
    MFT = "mft"
    JUMPLIST = "jumplist"

    # network
    PCAP = "pcap"
    PCAPNG = "pcapng"

    # containers
    ARCHIVE_ZIP = "archive_zip"
    ARCHIVE_TAR = "archive_tar"
    ARCHIVE_7Z = "archive_7z"
    ARCHIVE_RAR = "archive_rar"
    ARCHIVE_GZ = "archive_gz"

    # documents & media
    PDF = "pdf"
    OFFICE_OOXML = "office_ooxml"
    OFFICE_OLE = "office_ole"
    IMAGE_JPEG = "image_jpeg"
    IMAGE_PNG = "image_png"
    IMAGE_GIF = "image_gif"
    IMAGE_BMP = "image_bmp"
    IMAGE_TIFF = "image_tiff"
    IMAGE_WEBP = "image_webp"
    AUDIO = "audio"
    VIDEO = "video"

    # executables
    PE = "pe"
    ELF = "elf"
    MACHO = "macho"
    DOTNET = "dotnet"

    # data
    SQLITE = "sqlite"
    PLIST = "plist"
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    TEXT = "text"
    EMAIL = "email"
    PCAP_TEXT = "pcap_text"

    # crypto / opaque
    ENCRYPTED = "encrypted"
    COMPRESSED_OPAQUE = "compressed_opaque"

    UNKNOWN = "unknown"

    @property
    def family(self) -> "KindFamily":
        return _FAMILY.get(self, KindFamily.OTHER)


class KindFamily(str, Enum):
    MEMORY = "memory"
    DISK = "disk"
    MOBILE = "mobile"
    WINDOWS_ARTIFACT = "windows_artifact"
    NETWORK = "network"
    ARCHIVE = "archive"
    DOCUMENT = "document"
    MEDIA = "media"
    EXECUTABLE = "executable"
    DATA = "data"
    OPAQUE = "opaque"
    OTHER = "other"


_FAMILY: dict[ArtifactKind, KindFamily] = {
    ArtifactKind.MEMORY_DUMP: KindFamily.MEMORY,
    ArtifactKind.HIBERNATION_FILE: KindFamily.MEMORY,
    ArtifactKind.CRASH_DUMP: KindFamily.MEMORY,
    ArtifactKind.PROCESS_DUMP: KindFamily.MEMORY,
    ArtifactKind.DISK_IMAGE_RAW: KindFamily.DISK,
    ArtifactKind.DISK_IMAGE_EWF: KindFamily.DISK,
    ArtifactKind.DISK_IMAGE_VMDK: KindFamily.DISK,
    ArtifactKind.DISK_IMAGE_VHD: KindFamily.DISK,
    ArtifactKind.DISK_IMAGE_QCOW: KindFamily.DISK,
    ArtifactKind.FILESYSTEM_ARCHIVE: KindFamily.DISK,
    ArtifactKind.IOS_BACKUP: KindFamily.MOBILE,
    ArtifactKind.ANDROID_BACKUP: KindFamily.MOBILE,
    ArtifactKind.APK: KindFamily.MOBILE,
    ArtifactKind.IPA: KindFamily.MOBILE,
    ArtifactKind.EVTX: KindFamily.WINDOWS_ARTIFACT,
    ArtifactKind.REGISTRY_HIVE: KindFamily.WINDOWS_ARTIFACT,
    ArtifactKind.PREFETCH: KindFamily.WINDOWS_ARTIFACT,
    ArtifactKind.LNK: KindFamily.WINDOWS_ARTIFACT,
    ArtifactKind.MFT: KindFamily.WINDOWS_ARTIFACT,
    ArtifactKind.JUMPLIST: KindFamily.WINDOWS_ARTIFACT,
    ArtifactKind.PCAP: KindFamily.NETWORK,
    ArtifactKind.PCAPNG: KindFamily.NETWORK,
    ArtifactKind.ARCHIVE_ZIP: KindFamily.ARCHIVE,
    ArtifactKind.ARCHIVE_TAR: KindFamily.ARCHIVE,
    ArtifactKind.ARCHIVE_7Z: KindFamily.ARCHIVE,
    ArtifactKind.ARCHIVE_RAR: KindFamily.ARCHIVE,
    ArtifactKind.ARCHIVE_GZ: KindFamily.ARCHIVE,
    ArtifactKind.PDF: KindFamily.DOCUMENT,
    ArtifactKind.OFFICE_OOXML: KindFamily.DOCUMENT,
    ArtifactKind.OFFICE_OLE: KindFamily.DOCUMENT,
    ArtifactKind.EMAIL: KindFamily.DOCUMENT,
    ArtifactKind.IMAGE_JPEG: KindFamily.MEDIA,
    ArtifactKind.IMAGE_PNG: KindFamily.MEDIA,
    ArtifactKind.IMAGE_GIF: KindFamily.MEDIA,
    ArtifactKind.IMAGE_BMP: KindFamily.MEDIA,
    ArtifactKind.IMAGE_TIFF: KindFamily.MEDIA,
    ArtifactKind.IMAGE_WEBP: KindFamily.MEDIA,
    ArtifactKind.AUDIO: KindFamily.MEDIA,
    ArtifactKind.VIDEO: KindFamily.MEDIA,
    ArtifactKind.PE: KindFamily.EXECUTABLE,
    ArtifactKind.ELF: KindFamily.EXECUTABLE,
    ArtifactKind.MACHO: KindFamily.EXECUTABLE,
    ArtifactKind.DOTNET: KindFamily.EXECUTABLE,
    ArtifactKind.SQLITE: KindFamily.DATA,
    ArtifactKind.PLIST: KindFamily.DATA,
    ArtifactKind.JSON: KindFamily.DATA,
    ArtifactKind.XML: KindFamily.DATA,
    ArtifactKind.CSV: KindFamily.DATA,
    ArtifactKind.TEXT: KindFamily.DATA,
    ArtifactKind.ENCRYPTED: KindFamily.OPAQUE,
    ArtifactKind.COMPRESSED_OPAQUE: KindFamily.OPAQUE,
}


class FindingKind(str, Enum):
    """Closed vocabulary for normalised findings — the join key across tools."""

    PROCESS = "process"
    NETWORK_CONNECTION = "network_connection"
    DNS_QUERY = "dns_query"
    HTTP_REQUEST = "http_request"
    FILE = "file"
    FILE_METADATA = "file_metadata"
    REGISTRY_KEY = "registry_key"
    EXECUTION_EVIDENCE = "execution_evidence"
    SCHEDULED_TASK = "scheduled_task"
    SERVICE = "service"
    DRIVER = "driver"
    USB_DEVICE = "usb_device"
    USER_ACCOUNT = "user_account"
    CREDENTIAL = "credential"
    BROWSER_HISTORY = "browser_history"
    BROWSER_DOWNLOAD = "browser_download"
    SMS = "sms"
    CALL = "call"
    CONTACT = "contact"
    CHAT_MESSAGE = "chat_message"
    GEOLOCATION = "geolocation"
    EMAIL = "email"
    EXIF = "exif"
    YARA_MATCH = "yara_match"
    SIGNATURE_MATCH = "signature_match"
    EMBEDDED_FILE = "embedded_file"
    STRING_HIT = "string_hit"
    FLAG_CANDIDATE = "flag_candidate"
    LOG_EVENT = "log_event"
    ARTIFACT_IDENTITY = "artifact_identity"
    ERROR = "error"
