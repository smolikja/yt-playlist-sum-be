from alembic.config import Config
from alembic import command
import os

def run_migrations_up(db_url: str):
    """
    Runs alembic upgrade head against the specified database URL.
    """
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")

def run_migrations_down(db_url: str):
    """
    Runs alembic downgrade base against the specified database URL.
    """
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.downgrade(alembic_cfg, "base")
