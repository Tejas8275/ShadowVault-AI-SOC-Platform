import tempfile
import unittest
from pathlib import Path
from alembic import command
from sqlalchemy import MetaData, select, text
from app.core.config import BACKEND_DIR, Settings
from app.db.migrate import migration_config, upgrade_database
from app.db.session import build_engine


class IncidentMigrationTests(unittest.TestCase):
    def test_0005_upgrade_preserves_records_and_unknown_update_time(self):
        with tempfile.TemporaryDirectory(dir=BACKEND_DIR) as directory:
            settings=Settings(_env_file=None,database_url=f'sqlite:///{Path(directory).as_posix()}/test.db')
            engine=build_engine(settings)
            try:
                with engine.begin() as c:
                    command.upgrade(migration_config(c),'0005')
                    c.execute(text("INSERT INTO users VALUES ('old@example.test','Owner','!disabled',1,:id,'2026-09-06')"),{'id':'a'*32})
                    c.execute(text("INSERT INTO incidents (title,description,status,severity,created_by_id,id,created_at,revision) VALUES ('Old','','closed','medium',:owner,:id,'2026-09-06',7)"),{'owner':'a'*32,'id':'b'*32})
                    old=MetaData(); old.reflect(c)
                    before={name:c.execute(select(table)).all() for name,table in old.tables.items() if name!='alembic_version'}
                
                with engine.begin() as c: command.upgrade(migration_config(c),'0006')
                with engine.begin() as c:
                    for name,rows in before.items(): self.assertEqual(c.execute(select(old.tables[name])).all(),rows)
                    self.assertIsNone(c.scalar(text('select updated_at from incidents')))
                    self.assertEqual(c.scalar(text('select version_num from alembic_version')),'0006')
                    self.assertEqual(c.exec_driver_sql('pragma integrity_check').scalar(),'ok')
                    self.assertEqual(c.exec_driver_sql('pragma foreign_key_check').all(),[])
                    with self.assertRaisesRegex(RuntimeError,'0006 is forward-only'): command.downgrade(migration_config(c),'0005')
            finally: engine.dispose()

    def test_populated_0004_upgrade_preserves_original_columns_and_defaults_revision(self):
        with tempfile.TemporaryDirectory(dir=BACKEND_DIR) as directory:
            settings=Settings(_env_file=None,database_url=f'sqlite:///{Path(directory).as_posix()}/test.db')
            engine=build_engine(settings)
            try:
                with engine.begin() as c:
                    command.upgrade(migration_config(c),'0004')
                    c.execute(text("INSERT INTO users VALUES ('old@example.test','Owner','!disabled',1,:id,'2026-09-06')"),{'id':'a'*32})
                    c.execute(text("INSERT INTO incidents VALUES ('Old','','closed','medium',:owner,:id,'2026-09-06')"),{'owner':'a'*32,'id':'b'*32})
                    old=MetaData(); old.reflect(c)
                    before={name:c.execute(select(table)).all() for name,table in old.tables.items() if name!='alembic_version'}
                
                with engine.begin() as c: command.upgrade(migration_config(c),'0005')
                with engine.begin() as c:
                    for name,rows in before.items(): self.assertEqual(c.execute(select(old.tables[name])).all(),rows)
                    self.assertEqual(c.scalar(text('select revision from incidents')),0)
                    self.assertEqual(c.exec_driver_sql('pragma foreign_key_check').all(),[])
                    with self.assertRaisesRegex(RuntimeError,'0005 is forward-only'): command.downgrade(migration_config(c),'0004')
            finally: engine.dispose()
