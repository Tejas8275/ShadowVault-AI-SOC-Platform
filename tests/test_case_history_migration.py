import tempfile
import unittest
from pathlib import Path
from alembic import command
from sqlalchemy import MetaData, select, text
from app.core.config import BACKEND_DIR, Settings
from app.db.migrate import migration_config, upgrade_database
from app.db.session import build_engine


class HistoryMigrationTests(unittest.TestCase):
    def test_populated_0006_upgrade_preserves_records_and_baselines(self):
        with tempfile.TemporaryDirectory(dir=BACKEND_DIR) as directory:
            settings=Settings(_env_file=None,database_url=f'sqlite:///{Path(directory).as_posix()}/test.db')
            engine=build_engine(settings)
            try:
                with engine.begin() as c:
                    command.upgrade(migration_config(c),'0006')
                    c.execute(text("INSERT INTO users VALUES ('legacy@example.test','Owner','!disabled',1,:id,'2026-09-01')"),{'id':'a'*32})
                    for id,rev in [('b'*32,0),('c'*32,7)]:
                        c.execute(text("INSERT INTO incidents (id,created_by_id,title,description,status,severity,revision,created_at) VALUES (:id,:owner,'Legacy','Original','closed','high',:rev,'2026-09-01')"),{'id':id,'owner':'a'*32,'rev':rev})
                    frozen=MetaData();frozen.reflect(c)
                    before={n:c.execute(select(t)).all() for n,t in frozen.tables.items() if n!='alembic_version'}
                with engine.begin() as c:
                    command.upgrade(migration_config(c),'0007');command.upgrade(migration_config(c),'0007')
                with engine.connect() as c:
                    for n,rows in before.items():self.assertEqual(c.execute(select(frozen.tables[n])).all(),rows)
                    self.assertEqual(c.execute(text('select revision,event_type,source,actor_type from case_history_events order by revision')).all(),[(0,'baseline_registered','migration','system'),(7,'baseline_registered','migration','system')])
                    self.assertEqual(c.exec_driver_sql('pragma integrity_check').scalar(),'ok')
                    self.assertEqual(c.exec_driver_sql('pragma foreign_key_check').all(),[])
                    self.assertEqual(c.scalar(text('select version_num from alembic_version')),'0007')
                    with self.assertRaisesRegex(RuntimeError,'0007 is forward-only'):command.downgrade(migration_config(c),'0006')
            finally:engine.dispose()

    def test_oversized_legacy_snapshot_stops_upgrade_without_partial_schema(self):
        with tempfile.TemporaryDirectory(dir=BACKEND_DIR) as directory:
            settings=Settings(_env_file=None,database_url=f'sqlite:///{Path(directory).as_posix()}/test.db')
            engine=build_engine(settings)
            try:
                with engine.begin() as c:
                    command.upgrade(migration_config(c),'0006')
                    c.execute(text("INSERT INTO users VALUES ('legacy@example.test','Owner','!disabled',1,:id,'2026-09-01')"),{'id':'a'*32})
                    c.execute(text("INSERT INTO incidents (id,created_by_id,title,description,status,severity,revision,created_at) VALUES (:id,:owner,'Legacy',:body,'open','high',0,'2026-09-01')"),{'id':'b'*32,'owner':'a'*32,'body':'x'*10001})
                with self.assertRaisesRegex(RuntimeError,'Legacy case values'):upgrade_database(settings)
                with engine.connect() as c:
                    self.assertEqual(c.scalar(text('select version_num from alembic_version')),'0006')
                    self.assertEqual(c.scalar(text("select count(*) from sqlite_master where name='case_history_events'")),0)
            finally:engine.dispose()
