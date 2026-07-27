"""users table, case ownership, and FK/type hardening

Revision ID: 9f4c1b7a2e13
Revises: 5bdd8ff6878a
Create Date: 2026-07-27 12:00:00.000000+00:00

What this migration fixes:

  * The `users` table is absent from all three previous revisions, so a fresh
    `alembic upgrade head` produced a database with no users table at all. The
    application only worked because api/main.py calls
    Base.metadata.create_all() at startup — meaning the migration chain was
    never the source of truth for the schema.
  * `cases` had no owner column, so there was no authorization model: any
    authenticated account could read, modify and delete every case.
  * `artifacts.file_size` was a 32-bit INTEGER while uploads up to 5 GB are
    accepted — a large disk image failed with NumericValueOutOfRange after its
    bytes had already been written to object storage.
  * The foreign keys had no ON DELETE action, so deletion worked only through
    SQLAlchemy's in-Python cascade; any raw-SQL delete hit an FK violation.
  * All timestamps were naive (`datetime.utcnow`), losing the offset.

Every step is guarded with an inspector because existing deployments have a
schema created by `create_all`, not by these revisions: the objects this
migration adds may already be present.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9f4c1b7a2e13"
down_revision: Union[str, Sequence[str], None] = "5bdd8ff6878a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Timestamp columns migrated between naive and tz-aware.
_TIMESTAMP_COLUMNS = [
    ("cases", "created_at"),
    ("cases", "updated_at"),
    ("artifacts", "uploaded_at"),
    ("analyses", "started_at"),
    ("analyses", "completed_at"),
]

# Placeholder owner for pre-existing cases. The password hash is deliberately
# not a valid bcrypt digest, so the account can never be authenticated against;
# it exists only to satisfy the NOT NULL owner constraint for legacy rows.
_LEGACY_OWNER_USERNAME = "legacy-owner"
_UNUSABLE_PASSWORD_HASH = "!disabled-account-no-login"


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return name in _inspector().get_table_names()


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return column in {c["name"] for c in _inspector().get_columns(table)}


def _has_index(table: str, index: str) -> bool:
    if not _has_table(table):
        return False
    return index in {i["name"] for i in _inspector().get_indexes(table)}


def _fk_name(table: str, column: str) -> str | None:
    """Return the existing FK constraint name covering `column`, if any."""
    if not _has_table(table):
        return None
    for fk in _inspector().get_foreign_keys(table):
        if fk.get("constrained_columns") == [column] and fk.get("name"):
            return fk["name"]
    return None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    # ── 1. users ───────────────────────────────────────────────────────────────
    if not _has_table("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("username", sa.String(length=50), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("hashed_password", sa.String(length=255), nullable=False),
            sa.Column("role", sa.String(length=20), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _has_index("users", op.f("ix_users_id")):
        op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    if not _has_index("users", op.f("ix_users_username")):
        op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    if not _has_index("users", op.f("ix_users_email")):
        op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # ── 2. cases.owner_id ──────────────────────────────────────────────────────
    if not _has_column("cases", "owner_id"):
        # Added nullable first: an existing table with rows cannot take a NOT
        # NULL column without a value for every row.
        op.add_column("cases", sa.Column("owner_id", sa.Integer(), nullable=True))

        orphan_cases = bind.execute(
            sa.text("SELECT COUNT(*) FROM cases WHERE owner_id IS NULL")
        ).scalar_one()

        if orphan_cases:
            owner_id = bind.execute(
                sa.text("SELECT id FROM users ORDER BY id LIMIT 1")
            ).scalar()
            if owner_id is None:
                # No user exists to inherit the legacy cases. Create a locked
                # admin placeholder rather than dropping the evidence or leaving
                # the column nullable (which would reopen the authorization
                # hole this migration exists to close).
                owner_id = bind.execute(
                    sa.text(
                        "INSERT INTO users "
                        "(username, email, hashed_password, role, is_active, created_at) "
                        "VALUES (:u, NULL, :p, 'admin', FALSE, NOW()) "
                        "RETURNING id"
                    ),
                    {"u": _LEGACY_OWNER_USERNAME, "p": _UNUSABLE_PASSWORD_HASH},
                ).scalar_one()
            bind.execute(
                sa.text("UPDATE cases SET owner_id = :oid WHERE owner_id IS NULL"),
                {"oid": owner_id},
            )

        op.alter_column("cases", "owner_id", existing_type=sa.Integer(), nullable=False)
        op.create_index(op.f("ix_cases_owner_id"), "cases", ["owner_id"], unique=False)
        op.create_foreign_key(
            "fk_cases_owner_id_users",
            "cases",
            "users",
            ["owner_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    # ── 3. artifacts.file_size → BIGINT ────────────────────────────────────────
    op.alter_column(
        "artifacts",
        "file_size",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
    )

    # ── 4. ON DELETE CASCADE on the child foreign keys ─────────────────────────
    artifacts_fk = _fk_name("artifacts", "case_id")
    if artifacts_fk:
        op.drop_constraint(artifacts_fk, "artifacts", type_="foreignkey")
    op.create_foreign_key(
        "fk_artifacts_case_id_cases",
        "artifacts",
        "cases",
        ["case_id"],
        ["id"],
        ondelete="CASCADE",
    )

    analyses_fk = _fk_name("analyses", "artifact_id")
    if analyses_fk:
        op.drop_constraint(analyses_fk, "analyses", type_="foreignkey")
    op.create_foreign_key(
        "fk_analyses_artifact_id_artifacts",
        "analyses",
        "artifacts",
        ["artifact_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # ── 5. naive timestamps → timestamptz ──────────────────────────────────────
    # Existing values were written by datetime.utcnow(), so they are UTC wall
    # clock: interpret them as UTC instead of as the server's local timezone.
    for table, column in _TIMESTAMP_COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(),
            type_=sa.DateTime(timezone=True),
            existing_nullable=True,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    """Downgrade schema."""
    # ── 5. timestamptz → naive ─────────────────────────────────────────────────
    for table, column in _TIMESTAMP_COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(timezone=True),
            type_=sa.DateTime(),
            existing_nullable=True,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )

    # ── 4. restore FKs without ON DELETE ───────────────────────────────────────
    analyses_fk = _fk_name("analyses", "artifact_id")
    if analyses_fk:
        op.drop_constraint(analyses_fk, "analyses", type_="foreignkey")
    op.create_foreign_key(
        "analyses_artifact_id_fkey", "analyses", "artifacts", ["artifact_id"], ["id"]
    )

    artifacts_fk = _fk_name("artifacts", "case_id")
    if artifacts_fk:
        op.drop_constraint(artifacts_fk, "artifacts", type_="foreignkey")
    op.create_foreign_key(
        "artifacts_case_id_fkey", "artifacts", "cases", ["case_id"], ["id"]
    )

    # ── 3. BIGINT → INTEGER ────────────────────────────────────────────────────
    # NOTE: this fails if any artifact larger than 2 GiB has been stored — that
    # is the point, the value would otherwise be silently corrupted.
    op.alter_column(
        "artifacts",
        "file_size",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
    )

    # ── 2. drop cases.owner_id ─────────────────────────────────────────────────
    if _has_column("cases", "owner_id"):
        owner_fk = _fk_name("cases", "owner_id")
        if owner_fk:
            op.drop_constraint(owner_fk, "cases", type_="foreignkey")
        if _has_index("cases", op.f("ix_cases_owner_id")):
            op.drop_index(op.f("ix_cases_owner_id"), table_name="cases")
        op.drop_column("cases", "owner_id")

    # ── 1. drop users ──────────────────────────────────────────────────────────
    if _has_table("users"):
        if _has_index("users", op.f("ix_users_email")):
            op.drop_index(op.f("ix_users_email"), table_name="users")
        if _has_index("users", op.f("ix_users_username")):
            op.drop_index(op.f("ix_users_username"), table_name="users")
        if _has_index("users", op.f("ix_users_id")):
            op.drop_index(op.f("ix_users_id"), table_name="users")
        op.drop_table("users")
