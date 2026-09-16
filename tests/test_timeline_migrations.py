import tempfile
import unittest
from pathlib import Path
from uuid import uuid4
from alembic import command
from sqlalchemy import MetaData, select, text
from app.core.config import BACKEND_DIR, Settings
from app.db.migrate import migration_config, upgrade_database
from app.db.session import build_engine, build_session_factory
from app.models import Evidence, Incident, User, TimelineEvent, EvidenceIntegrityCheck
from app.models.common import utc_now
from app.schemas.investigation import AnnotationPatch, NoteCreate
from app.services.evidence_metadata import annotate, add_note
from app.services.custody import verify_chain


class TimelineMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=BACKEND_DIR)
        self.settings = Settings(_env_file=None, database_url=f'sqlite:///{Path(self.temp.name).as_posix()}/test.db')
        self.engine = build_engine(self.settings)

    def tearDown(self):
        self.engine.dispose(); self.temp.cleanup()

    def test_populated_0003_preserves_every_old_column_and_custody_chain(self):
        with self.engine.begin() as connection: command.upgrade(migration_config(connection), '0003')
        with build_session_factory(self.engine)() as db:
            user = User(email='migration@example.test', display_name='Original owner', password_hash='!disabled')
            db.add(user); db.flush()
            incident_id = uuid4()
            frozen = MetaData(); frozen.reflect(db.connection(), only=['incidents'])
            db.execute(frozen.tables['incidents'].insert(), dict(id=incident_id.hex, created_by_id=user.id.hex,
                title='Original case', description='', status='open', severity='medium', created_at=utc_now()))
            evidence = Evidence(incident_id=incident_id, collected_by_id=user.id, filename='original.bin',
                                size_bytes=3, sha256='a' * 64, storage_key='untouched')
            db.add(evidence); db.flush()
            annotate(db, evidence.id, user, AnnotationPatch(expected_revision=0, tags=['original']))
            add_note(db, evidence.id, user, NoteCreate(expected_revision=1, body='Original note'))
            db.add(EvidenceIntegrityCheck(evidence_id=evidence.id, requested_by_id=user.id,
                                         expected_sha256=evidence.sha256, expected_size_bytes=3))
            db.commit(); evidence_id, user_id = evidence.id, user.id
        with self.engine.begin() as connection:
            metadata = MetaData(); metadata.reflect(connection)
            connection.execute(metadata.tables['timeline_events'].insert(), dict(id=uuid4().hex,
                incident_id=incident_id.hex, recorded_by_id=user_id.hex, occurred_at=utc_now(),
                title='Legacy event', description='Original account', source='Unknown relationship', created_at=utc_now()))
            before = {name: connection.execute(select(table)).all() for name, table in metadata.tables.items() if name != 'alembic_version'}
        upgrade_database(self.settings); upgrade_database(self.settings)
        with self.engine.connect() as connection:
            for name, rows in before.items():
                self.assertEqual(connection.execute(select(metadata.tables[name])).all(), rows, name)
            self.assertEqual(connection.exec_driver_sql('PRAGMA foreign_key_check').all(), [])
            self.assertEqual(connection.scalar(text('SELECT version_num FROM alembic_version')), '0008')
        with build_session_factory(self.engine)() as db:
            legacy = db.scalar(select(TimelineEvent))
            self.assertEqual(legacy.origin, 'legacy')
            for field in ('evidence_id', 'reported_time', 'recorded_by_label', 'source_locator', 'submission_id', 'request_sha256'):
                self.assertIsNone(getattr(legacy, field))
            self.assertTrue(verify_chain(db, evidence_id))

    def test_0004_downgrade_is_forward_only(self):
        with self.engine.begin() as connection: command.upgrade(migration_config(connection), '0004')
        with self.engine.begin() as connection:
            with self.assertRaisesRegex(RuntimeError, '0004 is forward-only'):
                command.downgrade(migration_config(connection), '0003')
            self.assertEqual(connection.scalar(text('SELECT version_num FROM alembic_version')), '0004')
