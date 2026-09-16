"""Add optimistic case revision without rebuilding or replacing existing records."""
from alembic import op
import sqlalchemy as sa

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('incidents', sa.Column('revision', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    raise RuntimeError('Revision 0005 is forward-only: restore a reviewed backup to preserve case revisions')
