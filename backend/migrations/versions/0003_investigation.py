"""Investigation metadata and custody structures; frozen schema revision."""
from alembic import op
import sqlalchemy as sa
import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('custody_events',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('evidence_id', sa.Uuid(), nullable=False),
    sa.Column('sequence', sa.Integer(), nullable=False),
    sa.Column('schema_version', sa.Integer(), server_default='1', nullable=False),
    sa.Column('event_type', sa.String(length=64), nullable=False),
    sa.Column('actor_type', sa.String(length=16), nullable=False),
    sa.Column('actor_user_id', sa.Uuid(), nullable=True),
    sa.Column('actor_agent_id', sa.Uuid(), nullable=True),
    sa.Column('system_actor', sa.String(length=64), nullable=True),
    sa.Column('actor_label', sa.String(length=120), nullable=False),
    sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('source_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('operation_id', sa.Uuid(), nullable=False),
    sa.Column('details', sa.JSON(), nullable=False),
    sa.Column('previous_hash', sa.String(length=64), nullable=True),
    sa.Column('event_hash', sa.String(length=64), nullable=False),
    sa.CheckConstraint("(actor_type = 'user' AND actor_user_id IS NOT NULL AND actor_agent_id IS NULL AND system_actor IS NULL) OR (actor_type = 'agent' AND actor_agent_id IS NOT NULL AND actor_user_id IS NULL AND system_actor IS NULL) OR (actor_type = 'system' AND system_actor IS NOT NULL AND actor_user_id IS NULL AND actor_agent_id IS NULL)", name=op.f('ck_custody_events_actor_identity')),
    sa.CheckConstraint('length(event_hash) = 64 AND (previous_hash IS NULL OR length(previous_hash) = 64)', name=op.f('ck_custody_events_hash_lengths')),
    sa.CheckConstraint('sequence > 0 AND schema_version = 1', name=op.f('ck_custody_events_sequence_version')),
    sa.ForeignKeyConstraint(['actor_agent_id'], ['agents.id'], name=op.f('fk_custody_events_actor_agent_id_agents'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], name=op.f('fk_custody_events_actor_user_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id'], name=op.f('fk_custody_events_evidence_id_evidence'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_custody_events')),
    sa.UniqueConstraint('evidence_id', 'operation_id', 'event_type', name='uq_custody_operation_type'),
    sa.UniqueConstraint('evidence_id', 'sequence', name='uq_custody_evidence_sequence')
    )
    op.create_table('evidence_integrity_checks',
    sa.Column('evidence_id', sa.Uuid(), nullable=False),
    sa.Column('requested_by_id', sa.Uuid(), nullable=False),
    sa.Column('status', sa.String(length=16), server_default='queued', nullable=False),
    sa.Column('result', sa.String(length=16), nullable=True),
    sa.Column('expected_sha256', sa.String(length=64), nullable=False),
    sa.Column('expected_size_bytes', sa.Integer(), nullable=False),
    sa.Column('observed_sha256', sa.String(length=64), nullable=True),
    sa.Column('observed_size_bytes', sa.Integer(), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('lease_token', sa.Uuid(), nullable=True),
    sa.Column('lease_expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
    sa.Column('error_code', sa.String(length=64), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("(status IN ('queued', 'running') AND result IS NULL AND completed_at IS NULL) OR (status IN ('completed', 'failed') AND result IS NOT NULL AND completed_at IS NOT NULL)", name=op.f('ck_evidence_integrity_checks_completion')),
    sa.CheckConstraint("result IS NULL OR result IN ('matches', 'mismatch', 'missing', 'unavailable')", name=op.f('ck_evidence_integrity_checks_result')),
    sa.CheckConstraint("status IN ('queued', 'running', 'completed', 'failed')", name=op.f('ck_evidence_integrity_checks_status')),
    sa.CheckConstraint('expected_size_bytes >= 0 AND attempts >= 0 AND (observed_size_bytes IS NULL OR observed_size_bytes >= 0)', name=op.f('ck_evidence_integrity_checks_nonnegative_values')),
    sa.CheckConstraint('length(expected_sha256) = 64 AND (observed_sha256 IS NULL OR length(observed_sha256) = 64)', name=op.f('ck_evidence_integrity_checks_digest_lengths')),
    sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id'], name=op.f('fk_evidence_integrity_checks_evidence_id_evidence'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['requested_by_id'], ['users.id'], name=op.f('fk_evidence_integrity_checks_requested_by_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_evidence_integrity_checks'))
    )
    with op.batch_alter_table('evidence_integrity_checks', schema=None) as batch_op:
        batch_op.create_index('ix_integrity_evidence_created_id', ['evidence_id', 'created_at', 'id'], unique=False)
        batch_op.create_index('ix_integrity_status_created', ['status', 'created_at'], unique=False)

    op.create_table('evidence_notes',
    sa.Column('evidence_id', sa.Uuid(), nullable=False),
    sa.Column('author_id', sa.Uuid(), nullable=False),
    sa.Column('author_label', sa.String(length=120), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('length(body) BETWEEN 1 AND 10000', name=op.f('ck_evidence_notes_body_length')),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], name=op.f('fk_evidence_notes_author_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id'], name=op.f('fk_evidence_notes_evidence_id_evidence'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_evidence_notes'))
    )
    with op.batch_alter_table('evidence_notes', schema=None) as batch_op:
        batch_op.create_index('ix_evidence_notes_evidence_created_id', ['evidence_id', 'created_at', 'id'], unique=False)

    op.create_table('evidence_tags',
    sa.Column('evidence_id', sa.Uuid(), nullable=False),
    sa.Column('tag', sa.String(length=64), nullable=False),
    sa.CheckConstraint('length(tag) BETWEEN 1 AND 64', name=op.f('ck_evidence_tags_tag_length')),
    sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id'], name=op.f('fk_evidence_tags_evidence_id_evidence'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('evidence_id', 'tag', name=op.f('pk_evidence_tags'))
    )
    with op.batch_alter_table('evidence_tags', schema=None) as batch_op:
        batch_op.create_index('ix_evidence_tags_tag_evidence', ['tag', 'evidence_id'], unique=False)

    with op.batch_alter_table('evidence', schema=None) as batch_op:
        batch_op.add_column(sa.Column('display_title', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('review_state', sa.String(length=16), server_default='unreviewed', nullable=False))
        batch_op.add_column(sa.Column('metadata_revision', sa.Integer(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('custody_sequence', sa.Integer(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('custody_head_hash', sa.String(length=64), nullable=True))
        batch_op.create_index('ix_evidence_incident_created_id', ['incident_id', 'created_at', 'id'], unique=False)
        batch_op.create_index('ix_evidence_review_state', ['review_state'], unique=False)
        batch_op.create_check_constraint(op.f('ck_evidence_review_state'), "review_state IN ('unreviewed', 'in_review', 'reviewed')")
        batch_op.create_check_constraint(op.f('ck_evidence_nonnegative_revisions'), "metadata_revision >= 0 AND custody_sequence >= 0")
        batch_op.create_check_constraint(op.f('ck_evidence_custody_head'),
            "(custody_sequence = 0 AND custody_head_hash IS NULL) OR "
            "(custody_sequence > 0 AND custody_head_hash IS NOT NULL AND length(custody_head_hash) = 64)")

    register_baselines()


def register_baselines():
    """Frozen v1 hash format; never import evolving application services in a migration."""
    bind = op.get_bind()
    metadata = sa.MetaData()
    evidence = sa.Table('evidence', metadata, autoload_with=bind)
    custody = sa.Table('custody_events', metadata, autoload_with=bind)
    for name in ('id', 'incident_id'):
        evidence.c[name].type = sa.Uuid()
    for name in ('id', 'evidence_id', 'operation_id', 'actor_user_id', 'actor_agent_id'):
        custody.c[name].type = sa.Uuid()
    last_id = None
    while True:
        query = sa.select(evidence).order_by(evidence.c.id).limit(500)
        if last_id is not None:
            query = query.where(evidence.c.id > last_id)
        rows = bind.execute(query).mappings().all()
        if not rows:
            break
        for row in rows:
            now = datetime.now(timezone.utc)
            event_id, operation_id = uuid4(), uuid4()
            payload = {
                'schema_version': 1, 'id': str(event_id), 'evidence_id': str(row['id']),
                'sequence': 1, 'event_type': 'baseline_registered', 'actor_type': 'system',
                'actor_user_id': None, 'actor_agent_id': None, 'system_actor': 'migration:0003',
                'actor_label': 'Phase 2B-1 migration',
                'recorded_at': now.isoformat(timespec='microseconds').replace('+00:00', 'Z'),
                'source_at': None, 'operation_id': str(operation_id), 'previous_hash': None,
                'details': {'reason': 'preexisting_at_0003', 'initial_verification_status': row['verification_status'],
                            'sha256': row['sha256'], 'size_bytes': row['size_bytes'], 'incident_id': str(row['incident_id'])},
            }
            digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'),
                                               ensure_ascii=True, allow_nan=False).encode('utf-8')).hexdigest()
            values = dict(payload, id=event_id, evidence_id=row['id'], operation_id=operation_id,
                          recorded_at=now, event_hash=digest)
            bind.execute(custody.insert().values(**values))
            bind.execute(evidence.update().where(evidence.c.id == row['id']).values(custody_sequence=1, custody_head_hash=digest))
        last_id = rows[-1]['id']


def downgrade():
    raise RuntimeError('Revision 0003 is forward-only: do not discard custody/annotations; restore a reviewed backup if required')
