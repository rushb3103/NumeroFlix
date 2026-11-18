"""Store the dimensions of the first decoded video frame."""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    # The initial revision creates current metadata on new databases.
    columns = sa.inspect(op.get_bind()).get_columns("movie")
    if "first_frame_resolution" not in {column["name"] for column in columns}:
        op.add_column("movie", sa.Column("first_frame_resolution", sa.String(40), nullable=True))


def downgrade():
    op.drop_column("movie", "first_frame_resolution")
