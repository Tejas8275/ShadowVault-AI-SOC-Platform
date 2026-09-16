"""Case history baselines and append-only guards; original tables are unchanged."""
from datetime import datetime, timezone
from uuid import uuid4
from alembic import op
import sqlalchemy as sa

revision='0007'
down_revision='0006'
branch_labels=None
depends_on=None


def upgrade():
    connection=op.get_bind()
    if connection.dialect.name!='sqlite':
        raise RuntimeError('Case history guards require a reviewed SQLite deployment')
    # Frozen baseline contract; never import application models into migrations.
    incidents=sa.table('incidents',sa.column('id',sa.Uuid()),sa.column('revision',sa.Integer()),
        *(sa.column(field,sa.Text()) for field in ('title','description','status','severity')))
    limits={'title':200,'description':10000,'status':16,'severity':16}
    allowed={'status':{'open','investigating','closed'},'severity':{'low','medium','high','critical'}}
    # Validate before DDL; do not truncate legacy data or expose its values in errors.
    for record in connection.execute(sa.select(incidents)).mappings():
        for field,limit in limits.items():
            value=record[field]
            if not isinstance(value,str) or len(value)>limit or '\x00' in value or (field in allowed and value not in allowed[field]):
                raise RuntimeError('Legacy case values exceed history bounds; review before migration')
    table=op.create_table('case_history_events',
        sa.Column('id',sa.Uuid(),primary_key=True),
        sa.Column('incident_id',sa.Uuid(),sa.ForeignKey('incidents.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('revision',sa.Integer(),nullable=False),sa.Column('event_type',sa.String(32),nullable=False),
        sa.Column('schema_version',sa.Integer(),nullable=False),sa.Column('actor_type',sa.String(16),nullable=False),
        sa.Column('actor_user_id',sa.Uuid(),sa.ForeignKey('users.id',ondelete='RESTRICT')),
        sa.Column('actor_label',sa.String(120),nullable=False),sa.Column('system_actor',sa.String(32)),
        sa.Column('recorded_at',sa.DateTime(timezone=True),nullable=False),sa.Column('changes',sa.JSON(),nullable=False),
        sa.Column('source',sa.String(16),nullable=False),
        sa.UniqueConstraint('incident_id','revision',name='uq_case_history_incident_revision'),
        sa.CheckConstraint('revision >= 0 AND schema_version = 1',name='revision_version'),
        sa.CheckConstraint("(event_type = 'baseline_registered' AND actor_type = 'system' AND actor_user_id IS NULL AND system_actor IS NOT NULL AND system_actor = 'migration:0007' AND source = 'migration') OR "
                           "(event_type IN ('case_created','case_updated') AND actor_type = 'user' AND actor_user_id IS NOT NULL AND system_actor IS NULL AND source IN ('api','trusted_cli'))",name='event_actor'),
        sa.CheckConstraint("event_type != 'case_created' OR revision = 0",name='creation_revision'),
        sa.CheckConstraint("event_type != 'case_updated' OR revision >= 1",name='update_revision'),
        sa.CheckConstraint('length(actor_label) BETWEEN 1 AND 120',name='actor_label'))
    stamp=datetime.now(timezone.utc)
    for record in connection.execute(sa.select(incidents)).mappings():
        connection.execute(table.insert(),dict(id=uuid4(),incident_id=record['id'],revision=record['revision'],
            event_type='baseline_registered',schema_version=1,actor_type='system',actor_user_id=None,
            actor_label='Case history migration',system_actor='migration:0007',recorded_at=stamp,
            changes={field:{'before':None,'after':record[field]} for field in limits},source='migration'))
    for operation in ('UPDATE','DELETE'):
        op.execute(f"CREATE TRIGGER case_history_no_{operation.lower()} BEFORE {operation} ON case_history_events BEGIN SELECT RAISE(ABORT, 'Case history is append-only'); END")


def downgrade():
    raise RuntimeError('Revision 0007 is forward-only: restore a reviewed backup to preserve case history')
