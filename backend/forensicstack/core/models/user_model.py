from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from forensicstack.core.database import Base


# See orm_models._utcnow — datetime.utcnow is deprecated and returns a naive
# datetime, which mixes badly with the offset-aware datetimes used in JWT
# expiry handling.
def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """Platform user (investigator / admin)"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="analyst")   # analyst | admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    cases = relationship("Case", back_populates="owner")

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
