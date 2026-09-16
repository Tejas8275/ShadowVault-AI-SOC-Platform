import tempfile
import unittest
from pathlib import Path
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text
from app.core.config import BACKEND_DIR, Settings
from app.db.base import Base
from app.db.migrate import migration_config, upgrade_database
from app.db.session import build_engine


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=BACKEND_DIR)
        self.settings = Settings(_env_file=None, database_url=f"sqlite:///{Path(self.temp.name).as_posix()}/test.db")
        self.engine = build_engine(self.settings)

    def tearDown(self):
        self.engine.dispose()
        self.temp.cleanup()

    def test_fresh_upgrade_matches_models_and_is_repeatable(self):
        upgrade_database(self.settings)
        upgrade_database(self.settings)
        with self.engine.connect() as connection:
            self.assertEqual(connection.scalar(text("SELECT version_num FROM alembic_version")), "0008")
            self.assertEqual(compare_metadata(MigrationContext.configure(connection), Base.metadata), [])
            names = {item['name'] for item in inspect(connection).get_check_constraints('evidence')}
            self.assertIn('ck_evidence_collection_provenance', names)
            self.assertEqual(connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall(), [])

    def test_legacy_adoption_preserves_data(self):
        with self.engine.begin() as connection:
            command.upgrade(migration_config(connection), "0001")
            connection.execute(text("INSERT INTO users VALUES ('old@example.com', 'Old user', '!disabled', 1, :id, '2026-09-06 00:00:00')"), {'id': 'a' * 32})
            connection.execute(text("INSERT INTO incidents VALUES ('Old incident', '', 'open', 'medium', :owner, :id, '2026-09-06 00:00:00')"), {'owner': 'a' * 32, 'id': 'b' * 32})
            connection.execute(text("INSERT INTO evidence VALUES (:incident, :owner, 'old.bin', 'application/octet-stream', 1, :hash, 'legacy-key', '', :id, '2026-09-06 00:00:00')"), {'incident': 'b' * 32, 'owner': 'a' * 32, 'hash': 'd' * 64, 'id': 'c' * 32})
            connection.exec_driver_sql("DROP TABLE alembic_version")
        with self.assertRaises(RuntimeError):
            upgrade_database(self.settings)
        upgrade_database(self.settings, adopt_phase1=True)
        with self.engine.connect() as connection:
            self.assertEqual(connection.scalar(text("SELECT email FROM users")), "old@example.com")
            self.assertEqual(connection.scalar(text("SELECT verification_status FROM evidence")), "legacy")
            self.assertEqual(connection.scalar(text("SELECT storage_key FROM evidence")), "legacy-key")

    def test_unknown_schema_adoption_is_refused_without_changes(self):
        with self.engine.begin() as connection:
            connection.exec_driver_sql("CREATE TABLE unrelated (id INTEGER)")
        with self.assertRaises(RuntimeError):
            upgrade_database(self.settings, adopt_phase1=True)
        self.assertEqual(inspect(self.engine).get_table_names(), ['unrelated'])
