import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError, StatementError

from app.core.config import Settings
from app.db.base import Base
from app.db.init_db import init_db
from app.db.session import build_engine, build_session_factory
from app.models import Evidence, Incident, IncidentStatus, TimelineEvent, User


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.engine = build_engine(Settings(_env_file=None, database_url="sqlite://"))
        Base.metadata.create_all(self.engine)
        self.session = build_session_factory(self.engine)()
        self.user = User(email=" Analyst@Example.com ", display_name="Analyst", password_hash="test-only-hash")
        self.incident = Incident(title="Test investigation", created_by=self.user)
        self.session.add(self.incident)
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def make_evidence(self, **overrides):
        values = dict(incident=self.incident, collected_by=self.user, filename="sample.bin",
                      size_bytes=42, sha256="a" * 64, storage_key=str(uuid4()))
        values.update(overrides)
        return Evidence(**values)

    def test_schema_relationships_and_utc_roundtrip(self):
        self.assertEqual(set(inspect(self.engine).get_table_names()),
                         {"users", "incidents", "evidence", "timeline_events", "agents", "collection_jobs",
                          "custody_events", "evidence_notes", "evidence_tags", "evidence_integrity_checks", "case_history_events", "indicator_observations"})
        occurred = datetime(2026, 9, 6, 12, 30, tzinfo=timezone(timedelta(hours=5, minutes=30)))
        event = TimelineEvent(incident=self.incident, recorded_by=self.user, occurred_at=occurred,
                              title="Observed login", source="test fixture")
        self.session.add_all([self.make_evidence(), event])
        self.session.commit()
        self.session.expire_all()
        self.assertEqual(self.user.email, "analyst@example.com")
        self.assertEqual(self.incident.status, IncidentStatus.OPEN)
        self.assertEqual(len(self.incident.evidence), 1)
        self.assertEqual(len(self.incident.timeline_events), 1)
        self.assertEqual(event.occurred_at.hour, 7)
        self.assertEqual(event.occurred_at.utcoffset(), timedelta(0))

    def test_duplicate_email_rejected(self):
        self.session.add(User(email="ANALYST@example.com", display_name="Duplicate", password_hash="test"))
        with self.assertRaises(IntegrityError):
            self.session.commit()

    def test_orphan_incident_rejected(self):
        self.session.add(Incident(title="Orphan", created_by_id=uuid4()))
        with self.assertRaises(IntegrityError):
            self.session.commit()

    def test_incident_delete_preserves_evidence(self):
        self.session.add(self.make_evidence())
        self.session.commit()
        self.session.delete(self.incident)
        with self.assertRaises(IntegrityError):
            self.session.commit()
        self.session.rollback()
        self.assertEqual(len(self.incident.evidence), 1)

    def test_negative_evidence_size_rejected(self):
        self.session.add(self.make_evidence(size_bytes=-1))
        with self.assertRaises(IntegrityError):
            self.session.commit()

    def test_invalid_digest_rejected(self):
        with self.assertRaises(ValueError):
            self.make_evidence(sha256="z" * 64)

    def test_naive_event_time_rejected(self):
        self.session.add(TimelineEvent(incident=self.incident, recorded_by=self.user,
                                      occurred_at=datetime(2026, 9, 6), title="No timezone", source="test"))
        with self.assertRaises(StatementError):
            self.session.commit()

    def test_production_bootstrap_refused(self):
        with self.assertRaises(RuntimeError):
            init_db(Settings(_env_file=None, environment="production", database_url="sqlite://"))
