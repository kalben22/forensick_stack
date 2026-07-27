import logging
import os
from typing import Generator, Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

load_dotenv()

logger = logging.getLogger(__name__)


# ── Required-configuration helper ─────────────────────────────────────────────

def require_env(name: str, *, min_length: Optional[int] = None) -> str:
    """
    Return a mandatory environment variable, or abort the process.

    Prevents the class of failure where a missing .env silently falls back to a
    hardcoded credential that is public in the git history: the API would boot
    "successfully" while signing JWTs with a known key and talking to storage
    with default passwords. Failing loudly at import/startup makes a
    misconfigured deployment impossible to run instead of quietly insecure.

    Args:
        name:       Environment variable name.
        min_length: Optional minimum length (used for key material).

    Raises:
        RuntimeError: if the variable is unset, empty/whitespace, or too short.
    """
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(
            f"Required environment variable {name} is not set. "
            f"Copy .env.example to .env and fill it in — there is no default "
            f"for secrets."
        )
    if min_length is not None and len(value) < min_length:
        raise RuntimeError(
            f"Environment variable {name} is too short: "
            f"{len(value)} chars, minimum {min_length}."
        )
    return value


# ── PostgreSQL configuration ──────────────────────────────────────────────────
# Non-secret values keep sensible defaults; the password never does.
POSTGRES_USER = os.getenv("POSTGRES_USER", "forensicstack")
# No default: a fallback password ("Al0n3lyPssw0rd") published in this repo
# would let anyone who can reach the DB port authenticate as the app.
POSTGRES_PASSWORD = require_env("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5433")
POSTGRES_DB = os.getenv("POSTGRES_DB", "forensicstack")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Logged at DEBUG rather than printed: an unconditional print writes the DSN
# (and, in any variant that forgets to mask it, the password) to container
# stdout, which is shipped to log aggregators readable by non-operators.
logger.debug(
    "Database URL: postgresql://%s:***@%s:%s/%s",
    POSTGRES_USER,
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_DB,
)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection() -> bool:
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("Database connection OK")
        return True
    except Exception as e:
        logger.error("Database connection failed: %s", e)
        return False
