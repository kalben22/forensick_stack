"""
Finding models — deliberately free of any ORM or database dependency.

They used to live under ``core/models/``, whose ``__init__`` eagerly imports the
SQLAlchemy models, which in turn imports ``core/database.py``, which calls
``create_engine()`` at module scope. The effect was that importing a plain value
object required a live Postgres driver: a normalizer — code whose whole job is to
turn a file into records — could not be imported, or unit-tested, without a
database. Keeping findings in their own package removes that.
"""

from forensicstack.core.findings.finding import Finding, Severity, TimestampKind
from forensicstack.core.findings.timeparse import map_artifact_type, parse_timestamp

__all__ = [
    "Finding",
    "Severity",
    "TimestampKind",
    "parse_timestamp",
    "map_artifact_type",
]
