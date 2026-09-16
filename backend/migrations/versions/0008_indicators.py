"""Evidence-linked observations only; no changes to original tables or data."""
from alembic import op
import sqlalchemy as sa
revision='0008'
down_revision='0007'
branch_labels=None
depends_on=None

def upgrade():
    if op.get_bind().dialect.name != 'sqlite':
        raise RuntimeError('Indicator guards require a reviewed SQLite deployment')
    op.create_table('indicator_observations',
        sa.Column('id',sa.Uuid(),primary_key=True),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('incident_id',sa.Uuid(),sa.ForeignKey('incidents.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('evidence_id',sa.Uuid(),nullable=False),
        sa.Column('kind',sa.String(16),nullable=False),
        sa.Column('raw_value',sa.String(255),nullable=False),
        sa.Column('normalized_value',sa.String(255),nullable=False),
        sa.Column('source_kind',sa.String(32),nullable=False),
        sa.Column('source_locator',sa.String(512)),
        sa.Column('created_by_id',sa.Uuid(),sa.ForeignKey('users.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('actor_label',sa.String(120),nullable=False),
        sa.Column('schema_version',sa.Integer(),nullable=False),
        sa.Column('submission_id',sa.Uuid(),nullable=False),
        sa.Column('request_sha256',sa.String(64),nullable=False),
        sa.Column('supersedes_id',sa.Uuid(),sa.ForeignKey('indicator_observations.id',ondelete='RESTRICT')),
        sa.ForeignKeyConstraint(['evidence_id','incident_id'],['evidence.id','evidence.incident_id'],ondelete='RESTRICT',name='fk_indicator_evidence_incident'),
        sa.UniqueConstraint('created_by_id','submission_id',name='uq_indicator_submission'),
        sa.UniqueConstraint('supersedes_id',name='uq_indicator_successor'),
        sa.CheckConstraint("kind IN ('sha256','ip','domain','filename')",name='kind'),
        sa.CheckConstraint("source_kind = 'manual' OR (source_kind = 'evidence_sha256' AND kind = 'sha256') OR (source_kind = 'evidence_filename' AND kind = 'filename')",name='source_kind'),
        sa.CheckConstraint('length(raw_value) BETWEEN 1 AND 255 AND length(normalized_value) BETWEEN 1 AND 255',name='value_length'),
        sa.CheckConstraint('schema_version = 1 AND length(request_sha256) = 64',name='version_digest'),
        sa.CheckConstraint('length(actor_label) BETWEEN 1 AND 120',name='actor_label'),
        sa.CheckConstraint('source_locator IS NULL OR length(source_locator) BETWEEN 1 AND 512',name='locator_length'))
    for name,columns in [('case_created',['incident_id','created_at','id']),('evidence_created',['evidence_id','created_at','id']),('case_value',['incident_id','kind','normalized_value'])]:
        op.create_index('ix_indicator_'+name,'indicator_observations',columns)
    for operation in ('UPDATE','DELETE'):
        op.execute(f"CREATE TRIGGER indicator_no_{operation.lower()} BEFORE {operation} ON indicator_observations BEGIN SELECT RAISE(ABORT, 'Indicator observations are append-only'); END")

def downgrade():
    raise RuntimeError('Revision 0008 is forward-only: restore a reviewed backup to preserve indicator observations')
