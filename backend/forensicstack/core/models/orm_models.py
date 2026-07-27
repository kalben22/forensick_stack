from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from forensicstack.core.database import Base


# datetime.utcnow is deprecated in 3.12+ and returns a *naive* datetime, so
# values were stored without an offset and silently compared against
# offset-aware datetimes elsewhere (TypeError) or mis-rendered as local time in
# reports. Everything is now explicitly UTC-aware.
def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Case(Base):
    """Investigation Case"""
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    case_number = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="open")  # open, in_progress, closed
    # Without an owner column there was no way to answer "whose case is this?",
    # so every authenticated account could read, modify and delete every case in
    # the platform. NOT NULL means a case can never exist unattributed.
    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    metadata_json = Column(JSON)

    owner = relationship("User", back_populates="cases")
    artifacts = relationship("Artifact", back_populates="case", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Case {self.case_number}: {self.title}>"


class Artifact(Base):
    """Forensic Artifact"""
    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True, index=True)
    # ondelete=CASCADE at the DB level: SQLAlchemy's cascade only applies when
    # rows are deleted through a Session, so a raw-SQL/psql "DELETE FROM cases"
    # aborted with a foreign-key violation and left the DB unmaintainable.
    case_id = Column(
        Integer,
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename = Column(String(255), nullable=False)
    artifact_type = Column(String(50))  # disk_image, memory_dump, pcap, logs
    file_path = Column(String(500))     # Path in MinIO
    # BigInteger: a 32-bit column caps at 2 GiB - 1, but uploads are allowed up
    # to 5 GB, so a large disk image raised NumericValueOutOfRange *after* the
    # bytes had already been written to MinIO — an orphaned object plus a failed
    # upload the investigator could not retry.
    file_size = Column(BigInteger)      # Bytes
    file_hash_md5 = Column(String(32), index=True)
    file_hash_sha256 = Column(String(64), index=True)
    uploaded_at = Column(DateTime(timezone=True), default=_utcnow)
    metadata_json = Column(JSON)

    case = relationship("Case", back_populates="artifacts")
    analyses = relationship("Analysis", back_populates="artifact", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Artifact {self.filename} (Case {self.case_id})>"


class Analysis(Base):
    """Analysis Result"""
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    # See Artifact.case_id — same raw-SQL delete failure applies here.
    artifact_id = Column(
        Integer,
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    module_name = Column(String(100))   # volatility, plaso, tsk, yara…
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    result_path = Column(String(500))   # Path in MinIO
    result_summary = Column(JSON)
    error_message = Column(Text)

    artifact = relationship("Artifact", back_populates="analyses")

    def __repr__(self):
        return f"<Analysis {self.module_name} on Artifact {self.artifact_id}>"
