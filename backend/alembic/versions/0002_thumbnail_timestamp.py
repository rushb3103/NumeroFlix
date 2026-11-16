"""Store a video thumbnail timestamp.

Revision ID: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    # The initial revision creates current metadata on new databases.
    if "thumbnail_seconds" not in {column["name"] for column in sa.inspect(op.get_bind()).get_columns("movie")}:
        op.add_column("movie", sa.Column("thumbnail_seconds", sa.Float(), nullable=True))


def downgrade():
    op.drop_column("movie", "thumbnail_seconds")
