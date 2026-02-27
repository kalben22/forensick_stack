from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from forensicstack.core.database import Base


class Case(Base):
    """Investigation Case"""
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    case_number = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="open")  # open, in_progress, closed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON)

    artifacts = relationship("Artifact", back_populates="case", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Case {self.case_number}: {self.title}>"


class Artifact(Base):
    """Forensic Artifact"""
    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    artifact_type = Column(String(50))  # disk_image, memory_dump, pcap, logs
    file_path = Column(String(500))     # Path in MinIO
    file_size = Column(Integer)         # Bytes
    file_hash_md5 = Column(String(32), index=True)
    file_hash_sha256 = Column(String(64), index=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(JSON)

    case = relationship("Case", back_populates="artifacts")
    analyses = relationship("Analysis", back_populates="artifact", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Artifact {self.filename} (Case {self.case_id})>"


class Analysis(Base):
    """Analysis Result"""
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    artifact_id = Column(Integer, ForeignKey("artifacts.id"), nullable=False, index=True)
    module_name = Column(String(100))   # volatility, plaso, tsk, yara…
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    result_path = Column(String(500))   # Path in MinIO
    result_summary = Column(JSON)
    error_message = Column(Text)

    artifact = relationship("Artifact", back_populates="analyses")

    def __repr__(self):
        return f"<Analysis {self.module_name} on Artifact {self.artifact_id}>"
