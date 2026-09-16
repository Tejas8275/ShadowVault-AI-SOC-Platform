"""Extend the existing timeline; preserve legacy rows without inferred provenance."""
from alembic import op
import sqlalchemy as sa

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    # An index supplies the composite parent key without rebuilding evidence or its children.
    op.create_index('uq_evidence_id_incident', 'evidence', ['id', 'incident_id'], unique=True)
    with op.batch_alter_table('timeline_events') as batch:
        batch.add_column(sa.Column('evidence_id', sa.Uuid(), nullable=True))
        batch.add_column(sa.Column('origin', sa.String(16), nullable=False, server_default='legacy'))
        batch.add_column(sa.Column('reported_time', sa.String(64), nullable=True))
        batch.add_column(sa.Column('source_locator', sa.String(512), nullable=True))
        batch.add_column(sa.Column('recorded_by_label', sa.String(120), nullable=True))
        batch.add_column(sa.Column('submission_id', sa.Uuid(), nullable=True))
        batch.add_column(sa.Column('request_sha256', sa.String(64), nullable=True))
        batch.create_foreign_key('fk_timeline_evidence_incident', 'evidence', ['evidence_id', 'incident_id'], ['id', 'incident_id'], ondelete='RESTRICT')
        batch.create_unique_constraint('uq_timeline_recorder_submission', ['recorded_by_id', 'submission_id'])
        batch.create_check_constraint(op.f('ck_timeline_events_origin'), "origin IN ('legacy', 'investigator')")
        batch.create_check_constraint(op.f('ck_timeline_events_provenance'),
            "origin = 'legacy' OR (evidence_id IS NOT NULL AND reported_time IS NOT NULL "
            "AND recorded_by_label IS NOT NULL AND submission_id IS NOT NULL "
            "AND request_sha256 IS NOT NULL AND length(request_sha256) = 64)")
        batch.create_index('ix_timeline_incident_occurred_id', ['incident_id', 'occurred_at', 'id'])
        batch.create_index('ix_timeline_evidence_occurred_id', ['evidence_id', 'occurred_at', 'id'])


def downgrade():
    raise RuntimeError('Revision 0004 is forward-only: restore a reviewed backup rather than discard timeline provenance')
