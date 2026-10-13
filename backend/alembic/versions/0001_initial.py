"""Initial NumeroFlix schema.

Revision ID: 0001
"""
from alembic import op
from sqlmodel import SQLModel

from app import models  # noqa: F401

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    SQLModel.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    SQLModel.metadata.drop_all(bind=op.get_bind())

