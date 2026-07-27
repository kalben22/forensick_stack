"""
Centralised MinIO (S3-compatible) client for ForensicStack.

Two buckets are used:
  forensic-artifacts  — raw files uploaded by investigators via the API
  forensic-outputs    — analysis results produced by workers (used by worker.py)
"""
import hashlib
import io
import logging
import os
from datetime import timedelta
from pathlib import Path
from typing import BinaryIO, Optional

from dotenv import load_dotenv
from minio import Minio
from minio.error import S3Error

from forensicstack.core.database import require_env

load_dotenv()

logger = logging.getLogger(__name__)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
# No defaults: "minioadmin" / "M1nI0f0R3ns1cStAck" are published in this repo,
# so a deployment booting without a .env exposed every piece of evidence in
# object storage to anyone who could reach port 9000.
MINIO_ACCESS_KEY = require_env("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = require_env("MINIO_SECRET_KEY")

# Bucket names are not secret — defaults are fine.
ARTIFACTS_BUCKET = os.getenv("MINIO_ARTIFACTS_BUCKET", "forensic-artifacts")
OUTPUTS_BUCKET = os.getenv("MINIO_OUTPUTS_BUCKET", "forensic-outputs")

# Upload ceiling, configurable per deployment (default 5 GB).
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(5 * 1024**3)))

# Everything we store is treated as opaque bytes — see force_safe_content_type().
SAFE_CONTENT_TYPE = "application/octet-stream"


def force_safe_content_type(_client_supplied: Optional[str] = None) -> str:
    """
    Always return application/octet-stream for stored artifacts.

    The client-supplied Content-Type used to be persisted verbatim and then
    replayed by the presigned download URL. An uploader could label an evidence
    file `text/html`, and any investigator opening the presigned link would
    execute the attacker's script in the browser origin serving the evidence —
    stored XSS delivered through the chain of custody.
    """
    return SAFE_CONTENT_TYPE


def sanitize_filename(filename: Optional[str]) -> str:
    """
    Reduce a client-supplied filename to a single safe path component.

    `Path(name).name` strips directory traversal ("../../etc/passwd") and any
    absolute or Windows-style prefix, so a crafted multipart filename cannot
    escape its case prefix and overwrite another case's object key.
    """
    if not filename:
        return "upload"
    safe = Path(filename).name.replace("\\", "_").strip()
    # Path().name leaves "." / ".." untouched on some inputs; reject outright.
    if not safe or safe in {".", ".."}:
        return "upload"
    return safe


class MinioService:
    """Thin wrapper around the Minio client for artifact storage."""

    def __init__(self):
        self.client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False,
        )
        self._ensure_buckets()

    def _ensure_buckets(self):
        for bucket in (ARTIFACTS_BUCKET, OUTPUTS_BUCKET):
            try:
                if not self.client.bucket_exists(bucket):
                    self.client.make_bucket(bucket)
                    logger.info("[MinIO] Created bucket: %s", bucket)
            except S3Error as e:
                logger.warning("[MinIO] Could not create bucket %s: %s", bucket, e)

    # ── Upload ─────────────────────────────────────────────────────────────────

    def upload_artifact(
        self,
        file_data: bytes,
        object_name: str,
        content_type: str = SAFE_CONTENT_TYPE,
    ) -> str:
        """
        Upload raw bytes to the artifacts bucket.

        Only suitable for small payloads — large evidence files must go through
        upload_stream()/upload_file() so they never fully reside in RAM.
        """
        self.client.put_object(
            ARTIFACTS_BUCKET,
            object_name,
            io.BytesIO(file_data),
            length=len(file_data),
            content_type=force_safe_content_type(content_type),
        )
        return object_name

    def upload_stream(
        self,
        stream: BinaryIO,
        object_name: str,
        length: int = -1,
        bucket: str = ARTIFACTS_BUCKET,
        part_size: int = 16 * 1024 * 1024,
    ) -> str:
        """
        Upload from an open binary stream without buffering it in memory.

        `length=-1` lets the MinIO SDK do a multipart upload of unknown size
        using `part_size` chunks, so a 5 GB dump costs 16 MB of RAM instead of
        5 GB (the previous `await file.read()` path let a single upload OOM-kill
        the API process).
        """
        self.client.put_object(
            bucket,
            object_name,
            stream,
            length=length,
            part_size=part_size if length == -1 else 0,
            content_type=SAFE_CONTENT_TYPE,
        )
        return object_name

    def upload_file(
        self,
        local_path: str,
        object_name: str,
        bucket: str = ARTIFACTS_BUCKET,
        content_type: str = SAFE_CONTENT_TYPE,
    ) -> str:
        """Upload a local file to MinIO (streamed by the SDK)."""
        self.client.fput_object(
            bucket,
            object_name,
            local_path,
            content_type=force_safe_content_type(content_type),
        )
        return object_name

    # ── Download / Presigned URL ───────────────────────────────────────────────

    def get_presigned_url(
        self,
        object_name: str,
        bucket: str = ARTIFACTS_BUCKET,
        expires: int = 3600,
    ) -> Optional[str]:
        """
        Generate a time-limited presigned download URL.

        Returns:
            Presigned URL string or None on error.
        """
        try:
            return self.client.presigned_get_object(
                bucket, object_name, expires=timedelta(seconds=expires)
            )
        except S3Error as e:
            logger.warning(
                "[MinIO] Could not generate presigned URL for %s: %s", object_name, e
            )
            return None

    # ── Delete ─────────────────────────────────────────────────────────────────

    def delete_artifact(self, object_name: str, bucket: str = ARTIFACTS_BUCKET):
        """Delete an object from MinIO."""
        try:
            self.client.remove_object(bucket, object_name)
        except S3Error as e:
            logger.warning("[MinIO] Could not delete %s: %s", object_name, e)

    def delete_prefix(self, prefix: str, bucket: str = ARTIFACTS_BUCKET) -> int:
        """
        Delete every object under `prefix`. Returns the number deleted.

        Used when a case is deleted: removing only the objects referenced by
        Artifact rows leaves behind anything whose row was lost, so the evidence
        would outlive the case it belonged to in object storage.
        """
        deleted = 0
        try:
            for obj in self.client.list_objects(bucket, prefix=prefix, recursive=True):
                try:
                    self.client.remove_object(bucket, obj.object_name)
                    deleted += 1
                except S3Error as e:
                    logger.warning(
                        "[MinIO] Could not delete %s: %s", obj.object_name, e
                    )
        except S3Error as e:
            logger.warning("[MinIO] Could not list prefix %s: %s", prefix, e)
        return deleted

    # ── Utilities ──────────────────────────────────────────────────────────────

    @staticmethod
    def compute_hashes(data: bytes) -> tuple[str, str]:
        """Return (md5_hex, sha256_hex) for given bytes."""
        md5 = hashlib.md5(data, usedforsecurity=False).hexdigest()
        sha256 = hashlib.sha256(data).hexdigest()
        return md5, sha256

    @staticmethod
    def build_object_name(
        case_id: int,
        filename: str,
        sha256: Optional[str] = None,
    ) -> str:
        """
        Build a MinIO object path: case-{id}/{sha256}/{safe_filename}

        The content hash is part of the key because the old
        `case-{id}/{filename}` scheme made uploads collide: re-uploading
        `dump.raw` to the same case silently overwrote the stored bytes of the
        first artifact while the DB happily kept both rows — the earlier piece
        of evidence was destroyed and every downstream reference to it now
        resolved to different content. Keying on the hash makes a re-upload of
        identical bytes idempotent and a re-upload of *different* bytes land on
        a distinct key.

        The filename is sanitised here as well so no caller can inject path
        separators into the key.
        """
        safe_name = sanitize_filename(filename)
        if sha256:
            return f"case-{case_id}/{sha256}/{safe_name}"
        return f"case-{case_id}/{safe_name}"

    @staticmethod
    def case_prefix(case_id: int) -> str:
        """Object-key prefix owning every artifact of a case."""
        return f"case-{case_id}/"


# Singleton
_minio_service: Optional[MinioService] = None


def get_minio_service() -> MinioService:
    """Return (and lazily create) the singleton MinioService."""
    global _minio_service
    if _minio_service is None:
        _minio_service = MinioService()
    return _minio_service
