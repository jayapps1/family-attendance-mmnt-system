from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config
from sqlalchemy import pool

from config.database import DATABASE_URL
from models.base import Base
import models


# ---------------------------------------------------------
# ALEMBIC CONFIGURATION
# ---------------------------------------------------------

config = context.config


# ---------------------------------------------------------
# LOGGING
# ---------------------------------------------------------

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# ---------------------------------------------------------
# DATABASE URL
# ---------------------------------------------------------

# Alembic reads database configuration from our application
# instead of storing credentials in alembic.ini.
config.set_main_option(
    "sqlalchemy.url",
    DATABASE_URL.render_as_string(hide_password=False).replace("%", "%%"),
)


# ---------------------------------------------------------
# MODEL METADATA
# ---------------------------------------------------------

target_metadata = Base.metadata


# ---------------------------------------------------------
# OFFLINE MIGRATIONS
# ---------------------------------------------------------

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------
# ONLINE MIGRATIONS
# ---------------------------------------------------------

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(
            config.config_ini_section,
            {}
        ),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------
# EXECUTION
# ---------------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()