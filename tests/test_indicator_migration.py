import unittest,tempfile
from pathlib import Path
from alembic import command
from sqlalchemy import MetaData,select,text
from app.core.config import BACKEND_DIR,Settings
from app.db.session import build_engine
from app.db.migrate import migration_config,upgrade_database

class IndicatorMigrationTests(unittest.TestCase):
    def test_populated_0007_upgrade_preserves_all_rows_and_guards(self):
        with tempfile.TemporaryDirectory(dir=BACKEND_DIR) as directory:
            settings=Settings(_env_file=None,database_url=f'sqlite:///{Path(directory).as_posix()}/test.db')
            engine=build_engine(settings)
            try:
                with engine.begin() as c:
                    command.upgrade(migration_config(c),'0007')
                    c.execute(text("INSERT INTO users VALUES ('fixture@example.test','Owner','!',1,:id,'2026-09-01')"),{'id':'a'*32})
                    c.execute(text("INSERT INTO incidents (id,created_by_id,title,description,status,severity,revision,created_at) VALUES (:id,:owner,'Case','','open','low',0,'2026-09-01')"),{'id':'b'*32,'owner':'a'*32})
                    frozen=MetaData();frozen.reflect(c)
                    before={n:c.execute(select(t)).all() for n,t in frozen.tables.items() if n!='alembic_version'}
                upgrade_database(settings);upgrade_database(settings)
                with engine.connect() as c:
                    for n,rows in before.items():self.assertEqual(c.execute(select(frozen.tables[n])).all(),rows)
                    self.assertEqual(c.scalar(text('select count(*) from indicator_observations')),0)
                    self.assertEqual(c.scalar(text('select version_num from alembic_version')),'0008')
                    self.assertEqual(c.exec_driver_sql('pragma integrity_check').scalar(),'ok')
                    self.assertEqual(c.exec_driver_sql('pragma foreign_key_check').all(),[])
                    with self.assertRaisesRegex(RuntimeError,'0008 is forward-only'):command.downgrade(migration_config(c),'0007')
            finally:engine.dispose()
