# alembic/env.py
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import the models. This import is deliberately NOT wrapped in
# try/except ImportError: the old version fell back to target_metadata = None,
# which is indistinguishable from "the database should be empty" — running
# `alembic revision --autogenerate` after a trivial import error would emit a
# migration that DROPS EVERY TABLE. A broken import must stop the tool.
from forensicstack.core.models import Base  # noqa: E402

target_metadata = Base.metadata

# Read the connection settings from the environment, exactly like
# forensicstack.core.database does. The previous hardcoded
# "postgresql://forensicstack:<password>@localhost:5433/forensicstack" embedded
# a credential in version control and pointed at the host's published port, so
# migrations could not run inside the container (where the host is `postgres`),
# and they silently targeted whatever database happened to listen on localhost.
from forensicstack.core.database import DATABASE_URL  # noqa: E402

# '%' must be escaped: alembic stores this in a ConfigParser, which would
# otherwise treat a '%' in the password as interpolation syntax and raise.
config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
