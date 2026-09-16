import tempfile
import unittest
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone
from alembic import command
from sqlalchemy import MetaData, select, text
from app.core.config import BACKEND_DIR, Settings
from app.db.migrate import migration_config, upgrade_database
from app.db.session import build_engine, build_session_factory
from app.models import CustodyEvent, Evidence
from app.services.custody import verify_chain


class InvestigationMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=BACKEND_DIR)
        self.settings = Settings(_env_file=None, database_url=f'sqlite:///{Path(self.temp.name).as_posix()}/test.db')
        self.engine = build_engine(self.settings)

    def tearDown(self):
        self.engine.dispose()
        self.temp.cleanup()

    def test_populated_phase2a_upgrade_preserves_every_original_column(self):
        now = datetime.now(timezone.utc)
        user, incident, agent, job, evidence = [uuid4().hex for _ in range(5)]
        with self.engine.begin() as connection:
            command.upgrade(migration_config(connection), '0002')
            metadata = MetaData()
            metadata.reflect(connection)
            tables = metadata.tables
            connection.execute(tables['users'].insert(), dict(id=user, email='fixture@example.com',
                display_name='Fixture', password_hash='!disabled', is_active=True, created_at=now))
            connection.execute(tables['incidents'].insert(), dict(id=incident, created_by_id=user,
                title='Case', description='Retain', status='open', severity='medium', created_at=now))
            connection.execute(tables['agents'].insert(), dict(id=agent, registered_by_id=user,
                name='Windows', platform='windows', collector_version='0.1', token_sha256='a' * 64,
                token_expires_at=now, is_active=True, created_at=now))
            connection.execute(tables['collection_jobs'].insert(), dict(id=job, incident_id=incident,
                agent_id=agent, requested_by_id=user, selected_files=[], status='complete', created_at=now))
            connection.execute(tables['evidence'].insert(), dict(id=evidence, incident_id=incident,
                collected_by_id=user, filename='fixture.bin', media_type='application/octet-stream',
                size_bytes=3, sha256='b' * 64, storage_key='original-key', description='Original',
                collection_job_id=job, collection_item_id=uuid4().hex, source_path=r'C:\fixture.bin',
                collected_at=now, verified_at=now, verification_status='verified', created_at=now))
            before = {name: connection.execute(select(table)).mappings().all()
                      for name, table in tables.items() if name != 'alembic_version'}
        upgrade_database(self.settings)
        upgrade_database(self.settings)
        with self.engine.connect() as connection:
            for name, rows in before.items():
                self.assertEqual(connection.execute(select(tables[name])).mappings().all(), rows, name)
            self.assertEqual(connection.exec_driver_sql('PRAGMA foreign_key_check').all(), [])
        with build_session_factory(self.engine)() as db:
            record = db.scalar(select(Evidence))
            self.assertEqual((record.metadata_revision, record.review_state, record.custody_sequence), (0, 'unreviewed', 1))
            event = db.scalar(select(CustodyEvent))
            self.assertEqual(event.event_type, 'baseline_registered')
            self.assertEqual(event.system_actor, 'migration:0003')
            self.assertEqual(event.details['initial_verification_status'], 'verified')
            self.assertIsNone(event.source_at)
            self.assertTrue(verify_chain(db, record.id))

    def test_downgrade_refuses_to_discard_custody_schema(self):
        # Exercise revision 0003's original guard even when newer migrations exist.
        with self.engine.begin() as connection:
            command.upgrade(migration_config(connection), '0003')
        with self.engine.begin() as connection:
            with self.assertRaisesRegex(RuntimeError, 'forward-only'):
                command.downgrade(migration_config(connection), '0002')
            self.assertEqual(connection.scalar(text('SELECT version_num FROM alembic_version')), '0003')
