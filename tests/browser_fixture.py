"""Isolated browser-test API; never uses the development database or operator."""
import sys
import tempfile
import hashlib
from pathlib import Path
from uuid import UUID
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
import uvicorn
from app.core.config import BACKEND_DIR, Settings
from app.core.security import token_digest
from app.db.migrate import upgrade_database
from app.db.session import build_engine, build_session_factory
from app.main import create_app
from app.models import Evidence, Incident, User, TimelineEvent
from app.models.common import utc_now
from briefing_fixture import FixtureProvider

if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='browser-test-', dir=BACKEND_DIR) as directory:
        root = Path(directory)
        settings = Settings(_env_file=None, environment='test', database_url=f'sqlite:///{root.as_posix()}/test.db',
            ai_min_interval_seconds=0, ai_max_per_minute=60,
            evidence_dir=root / 'evidence', retrieval_dir=root / 'retrieval', cors_origins=['http://127.0.0.1:5179'],
            operator_token_sha256=token_digest('sv_operator_' + 'B' * 43))
        upgrade_database(settings)
        engine = build_engine(settings)
        try:
            with build_session_factory(engine)() as db:
                user = User(email='browser@example.test', display_name='Browser investigator', password_hash='!disabled')
                incident = Incident(id=UUID(int=20), title='Browser fixture', created_by=user)
                db.add(incident); db.flush()
                # Dedicated metadata source for report workflows. Keep the annotation,
                # timeline and retrieval fixtures' initial custody states independent.
                db.add(Evidence(id=UUID(int=5), incident_id=incident.id, collected_by_id=user.id,
                    filename='report-fixture.txt', size_bytes=0, sha256='d'*64, storage_key='report-fixture'))
                db.add(Evidence(id=UUID(int=1), incident_id=incident.id, collected_by_id=user.id,
                    filename='browser-fixture.bin', size_bytes=3, sha256='a' * 64, storage_key='fixture-only'))
                db.add(Evidence(id=UUID(int=2), incident_id=incident.id, collected_by_id=user.id,
                    filename='timeline-fixture.bin', size_bytes=3, sha256='b' * 64, storage_key='timeline-fixture-only'))
                db.add(TimelineEvent(id=UUID(int=3), incident_id=incident.id, recorded_by_id=user.id,
                    occurred_at=utc_now(), title='Legacy timeline fixture', source='Original fixture', description='Unlinked legacy observation'))
                content = b'Original browser evidence\x00\xff'
                settings.evidence_dir.mkdir(mode=0o700)
                key = 'c' * 32 + '.blob'
                (settings.evidence_dir / key).write_bytes(content)
                db.add(Evidence(id=UUID(int=4), incident_id=incident.id, collected_by_id=user.id,
                    filename='retrieval-fixture.bin', size_bytes=len(content), sha256=hashlib.sha256(content).hexdigest(), storage_key=key))
                db.commit(); settings.operator_user_id = user.id
            uvicorn.run(create_app(settings, ai_provider=FixtureProvider()), host='127.0.0.1', port=8769, log_level='error', access_log=False)
        finally:
            engine.dispose()
