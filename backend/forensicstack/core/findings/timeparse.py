"""
Timestamp parsing and v1→v2 kind mapping.

The single most valuable field in DFIR is time, and v1 threw it away: two of the
five normalizers set ``timestamp=None`` unconditionally, and the rest passed the
tool's raw string through untouched — so ``"2024-03-11 09:12:44 UTC"``,
``"2024-03-11T09:12:44.123456+00:00"`` and ``"03/11/2024 09:12:44"`` were three
incomparable values.

Parsing lives here, once, and is tested — rather than being re-improvised per
normalizer.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Literal

from forensicstack.core.triage.kinds import FindingKind

Precision = Literal["s", "ms", "us", "ns"]

#: Explicit formats, tried in order. ISO is handled separately, first.
_FORMATS: tuple[tuple[str, Precision], ...] = (
    ("%Y-%m-%d %H:%M:%S.%f", "us"),
    ("%Y-%m-%d %H:%M:%S", "s"),
    ("%Y-%m-%dT%H:%M:%S.%f", "us"),
    ("%Y-%m-%dT%H:%M:%S", "s"),
    ("%Y/%m/%d %H:%M:%S", "s"),
    ("%m/%d/%Y %H:%M:%S", "s"),
    ("%m/%d/%Y %I:%M:%S %p", "s"),
    ("%d/%m/%Y %H:%M:%S", "s"),
    ("%d-%m-%Y %H:%M:%S", "s"),
    ("%b %d %Y %H:%M:%S", "s"),
    ("%d %b %Y %H:%M:%S", "s"),
    ("%a %b %d %H:%M:%S %Y", "s"),
    ("%Y:%m:%d %H:%M:%S", "s"),          # ExifTool's native format
    ("%Y-%m-%d", "s"),
    ("%m/%d/%Y", "s"),
)

_TRAILING_TZ = re.compile(r"\s*(UTC|GMT|Z)$", re.IGNORECASE)
_OFFSET = re.compile(r"([+-]\d{2}):?(\d{2})$")

#: Windows FILETIME epoch (1601-01-01) offset from the Unix epoch, in seconds.
_FILETIME_EPOCH_DELTA = 11_644_473_600

# Plausibility window. Anything outside is almost certainly a misparsed integer
# rather than a real event, and a bogus 1970 or 4000 entry poisons a timeline.
_MIN_YEAR, _MAX_YEAR = 1980, 2100


def _plausible(dt: datetime) -> bool:
    return _MIN_YEAR <= dt.year <= _MAX_YEAR


def _from_epoch_number(value: float) -> tuple[datetime | None, Precision | None]:
    """Interpret a bare number as an epoch, guessing the unit by magnitude."""
    candidates: tuple[tuple[float, Precision], ...] = (
        (value, "s"),
        (value / 1_000, "ms"),
        (value / 1_000_000, "us"),
        (value / 1_000_000_000, "ns"),
        # Windows FILETIME: 100 ns intervals since 1601
        (value / 10_000_000 - _FILETIME_EPOCH_DELTA, "us"),
        # WebKit/Chrome: microseconds since 1601
        (value / 1_000_000 - _FILETIME_EPOCH_DELTA, "us"),
        # Apple/Cocoa: seconds since 2001-01-01
        (value + 978_307_200, "s"),
    )
    for seconds, precision in candidates:
        try:
            dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            continue
        if _plausible(dt):
            return dt, precision
    return None, None


def parse_timestamp(value: object) -> tuple[datetime | None, Precision | None]:
    """Best-effort parse into a timezone-aware UTC datetime.

    Returns ``(None, None)`` when the value cannot be parsed — never a guess,
    and never the epoch as a stand-in for "unknown".
    """
    if value is None:
        return None, None

    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc), "us" if dt.microsecond else "s"

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _from_epoch_number(float(value))

    text = str(value).strip()
    if not text or text.lower() in {"n/a", "none", "null", "-", "unknown", "0"}:
        return None, None

    # ISO 8601, including a trailing Z
    iso = text.replace("Z", "+00:00") if text.endswith("Z") else text
    try:
        dt = datetime.fromisoformat(iso)
        dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        if _plausible(dt):
            return dt.astimezone(timezone.utc), "us" if dt.microsecond else "s"
    except ValueError:
        pass

    # A bare number in a string
    if re.fullmatch(r"-?\d+(?:\.\d+)?", text):
        return _from_epoch_number(float(text))

    # Explicit offset, e.g. "2024-03-11 09:12:44 +0100"
    tz = timezone.utc
    offset_match = _OFFSET.search(text)
    body = text
    if offset_match:
        hours, minutes = int(offset_match.group(1)), int(offset_match.group(2))
        sign = 1 if hours >= 0 else -1
        tz = timezone(timedelta(hours=hours, minutes=sign * minutes))
        body = text[: offset_match.start()].strip()
    body = _TRAILING_TZ.sub("", body).strip()

    for fmt, precision in _FORMATS:
        try:
            dt = datetime.strptime(body, fmt).replace(tzinfo=tz)
        except ValueError:
            continue
        if _plausible(dt):
            return dt.astimezone(timezone.utc), precision

    return None, None


# --------------------------------------------------------------------------- #
# v1 artifact_type → v2 FindingKind
# --------------------------------------------------------------------------- #

_TOOL_DEFAULT: dict[str, FindingKind] = {
    "volatility": FindingKind.PROCESS,
    "exiftool": FindingKind.EXIF,
    "ileapp": FindingKind.LOG_EVENT,
    "aleapp": FindingKind.LOG_EVENT,
    "eztools": FindingKind.EXECUTION_EVIDENCE,
    "triage": FindingKind.STRING_HIT,
    "yara": FindingKind.YARA_MATCH,
}

_SUBSTRING_MAP: tuple[tuple[str, FindingKind], ...] = (
    ("pslist", FindingKind.PROCESS),
    ("pstree", FindingKind.PROCESS),
    ("psscan", FindingKind.PROCESS),
    ("cmdline", FindingKind.PROCESS),
    ("malfind", FindingKind.SIGNATURE_MATCH),
    ("netscan", FindingKind.NETWORK_CONNECTION),
    ("netstat", FindingKind.NETWORK_CONNECTION),
    ("connection", FindingKind.NETWORK_CONNECTION),
    ("dns", FindingKind.DNS_QUERY),
    ("http", FindingKind.HTTP_REQUEST),
    ("svcscan", FindingKind.SERVICE),
    ("service", FindingKind.SERVICE),
    ("driver", FindingKind.DRIVER),
    ("modules", FindingKind.DRIVER),
    ("dlllist", FindingKind.FILE),
    ("filescan", FindingKind.FILE),
    ("mft", FindingKind.FILE),
    ("registry", FindingKind.REGISTRY_KEY),
    ("hive", FindingKind.REGISTRY_KEY),
    ("shellbag", FindingKind.REGISTRY_KEY),
    ("amcache", FindingKind.EXECUTION_EVIDENCE),
    ("prefetch", FindingKind.EXECUTION_EVIDENCE),
    ("appcompat", FindingKind.EXECUTION_EVIDENCE),
    ("shimcache", FindingKind.EXECUTION_EVIDENCE),
    ("srum", FindingKind.EXECUTION_EVIDENCE),
    ("bash", FindingKind.EXECUTION_EVIDENCE),
    ("jumplist", FindingKind.FILE),
    ("lnk", FindingKind.FILE),
    ("recyclebin", FindingKind.FILE),
    ("usb", FindingKind.USB_DEVICE),
    ("evtx", FindingKind.LOG_EVENT),
    ("event", FindingKind.LOG_EVENT),
    ("sms", FindingKind.SMS),
    ("message", FindingKind.CHAT_MESSAGE),
    ("chat", FindingKind.CHAT_MESSAGE),
    ("call", FindingKind.CALL),
    ("contact", FindingKind.CONTACT),
    ("location", FindingKind.GEOLOCATION),
    ("gps", FindingKind.GEOLOCATION),
    ("geo", FindingKind.GEOLOCATION),
    ("history", FindingKind.BROWSER_HISTORY),
    ("browser", FindingKind.BROWSER_HISTORY),
    ("safari", FindingKind.BROWSER_HISTORY),
    ("chrome", FindingKind.BROWSER_HISTORY),
    ("download", FindingKind.BROWSER_DOWNLOAD),
    ("account", FindingKind.USER_ACCOUNT),
    ("credential", FindingKind.CREDENTIAL),
    ("password", FindingKind.CREDENTIAL),
    ("email", FindingKind.EMAIL),
    ("mail", FindingKind.EMAIL),
    ("task", FindingKind.SCHEDULED_TASK),
    ("exif", FindingKind.EXIF),
    ("metadata", FindingKind.FILE_METADATA),
    ("yara", FindingKind.YARA_MATCH),
    ("error", FindingKind.ERROR),
    ("_error", FindingKind.ERROR),
)


def map_artifact_type(tool: str, artifact_type: str) -> FindingKind:
    """Map a v1 ``(tool, artifact_type)`` pair onto the closed v2 vocabulary."""
    needle = (artifact_type or "").lower()
    for substring, kind in _SUBSTRING_MAP:
        if substring in needle:
            return kind
    return _TOOL_DEFAULT.get((tool or "").lower(), FindingKind.LOG_EVENT)
