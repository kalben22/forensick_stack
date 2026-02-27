"""
Centralised MinIO (S3-compatible) client for ForensicStack.

Two buckets are used:
  forensic-artifacts  — raw files uploaded by investigators via the API
  forensic-outputs    — analysis results produced by workers (used by worker.py)
"""
import hashlib
import io
import os
from datetime import timedelta
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from minio import Minio
from minio.error import S3Error

load_dotenv()

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "M1nI0f0R3ns1cStAck")

ARTIFACTS_BUCKET = "forensic-artifacts"
OUTPUTS_BUCKET = "forensic-outputs"


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
                    print(f"[MinIO] Created bucket: {bucket}")
            except S3Error as e:
                print(f"[MinIO] Could not create bucket {bucket}: {e}")

    # ── Upload ─────────────────────────────────────────────────────────────────

    def upload_artifact(
        self,
        file_data: bytes,
        object_name: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload raw bytes to the artifacts bucket.

        Args:
            file_data:    Raw file bytes
            object_name:  Destination path inside the bucket, e.g. "case-1/dump.dmp"
            content_type: MIME type

        Returns:
            object_name (the MinIO path to store in the DB)
        """
        self.client.put_object(
            ARTIFACTS_BUCKET,
            object_name,
            io.BytesIO(file_data),
            length=len(file_data),
            content_type=content_type,
        )
        return object_name

    def upload_file(self, local_path: str, object_name: str, bucket: str = ARTIFACTS_BUCKET) -> str:
        """Upload a local file to MinIO."""
        self.client.fput_object(bucket, object_name, local_path)
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

        Args:
            object_name: MinIO path of the object
            bucket:      Which bucket
            expires:     URL validity in seconds (default 1 hour)

        Returns:
            Presigned URL string or None on error
        """
        try:
            url = self.client.presigned_get_object(
                bucket, object_name, expires=timedelta(seconds=expires)
            )
            return url
        except S3Error as e:
            print(f"[MinIO] Could not generate presigned URL for {object_name}: {e}")
            return None

    # ── Delete ─────────────────────────────────────────────────────────────────

    def delete_artifact(self, object_name: str, bucket: str = ARTIFACTS_BUCKET):
        """Delete an object from MinIO."""
        try:
            self.client.remove_object(bucket, object_name)
        except S3Error as e:
            print(f"[MinIO] Could not delete {object_name}: {e}")

    # ── Utilities ──────────────────────────────────────────────────────────────

    @staticmethod
    def compute_hashes(data: bytes) -> tuple[str, str]:
        """Return (md5_hex, sha256_hex) for given bytes."""
        md5 = hashlib.md5(data).hexdigest()
        sha256 = hashlib.sha256(data).hexdigest()
        return md5, sha256

    @staticmethod
    def build_object_name(case_id: int, filename: str) -> str:
        """Build a deterministic MinIO object path: case-{id}/{filename}"""
        return f"case-{case_id}/{filename}"


# Singleton
_minio_service: Optional[MinioService] = None


def get_minio_service() -> MinioService:
    """Return (and lazily create) the singleton MinioService."""
    global _minio_service
    if _minio_service is None:
        _minio_service = MinioService()
    return _minio_service
