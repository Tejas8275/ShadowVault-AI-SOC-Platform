"""Track case updates without inventing historical edit times."""
from alembic import op
import sqlalchemy as sa

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('incidents', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    raise RuntimeError('Revision 0006 is forward-only: restore a reviewed backup to preserve update timestamps')
