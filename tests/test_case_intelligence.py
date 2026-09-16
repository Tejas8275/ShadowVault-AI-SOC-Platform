from datetime import datetime, timezone
from uuid import UUID, uuid4
from unittest.mock import patch
import unittest
from sqlalchemy import MetaData, select
from sqlalchemy.exc import OperationalError
import test_incidents
from app.models import Evidence, TimelineEvent, Incident, Agent, CollectionJob
from app.services.custody import ensure_baseline

class IntelligenceTests(unittest.TestCase):
    setUp = test_incidents.CaseTests.setUp
    tearDown = test_incidents.CaseTests.tearDown

    def detail(self, id=None, **params):
        return self.client.get(self.base+'/'+(id or self.id), headers=self.headers, params=params)

    def test_default_contract_and_empty_summary(self):
        before=self.detail().json()
        self.assertNotIn('intelligence',before)
        response=self.detail(include_intelligence=True)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.headers['cache-control'],'no-store')
        summary=response.json().pop('intelligence')
        self.assertEqual(summary['evidence_count'],0)
        self.assertEqual(summary['timeline_count'],0)
        self.assertEqual(summary['history_revision_count'],0)
        self.assertIsNone(summary['history_started_revision'])
        self.assertTrue(summary['latest_activity_at'].endswith('Z'))
        self.assertEqual(self.detail().json(),before)

    def test_authorization_and_failure_are_sanitized(self):
        with patch('app.services.case_intelligence.summarize',side_effect=AssertionError('must not run')):
            self.assertEqual(self.detail(self.foreign,include_intelligence=True).status_code,404)
            self.assertEqual(self.client.get(self.base+'/'+self.id+'?include_intelligence=true').status_code,401)
            self.assertEqual(self.detail().status_code,200)
        with patch('app.services.case_intelligence.summarize',side_effect=OperationalError('private path',{},Exception('secret'))):
            response=self.detail(include_intelligence=True)
            self.assertEqual(response.status_code,503)
            self.assertEqual(response.json(),{'detail':'Case overview unavailable'})

    def test_history_count_is_not_revision_and_read_is_immutable(self):
        with self.factory() as db:
            db.get(Incident,UUID(self.id)).revision=9; db.commit()
        response=self.client.patch(self.base+'/'+self.id,headers=self.headers,json={'expected_revision':9,'severity':'high','title':'Own','status':'open'})
        self.assertEqual(response.status_code,200,response.text)
        with self.engine.connect() as c:
            metadata=MetaData();metadata.reflect(c)
            before={name:c.execute(select(table)).all() for name,table in metadata.tables.items()}
        summary=self.detail(include_intelligence=True).json()['intelligence']
        self.assertEqual(summary['history_revision_count'],1)
        self.assertEqual(summary['history_started_revision'],10)
        with self.engine.connect() as c:
            for name,rows in before.items():self.assertEqual(c.execute(select(metadata.tables[name])).all(),rows,name)

    def test_scoped_counts_and_recording_time_not_occurrence(self):
        stamp=datetime(2035,1,1,tzinfo=timezone.utc)
        with self.factory() as db:
            own=db.get(Incident,UUID(self.id)); foreign=db.get(Incident,UUID(self.foreign))
            agent=Agent(name='test',collector_version='1',registered_by_id=foreign.created_by_id,token_sha256='a'*64,token_expires_at=stamp)
            db.add(agent);db.flush()
            job=CollectionJob(incident_id=own.id,agent_id=agent.id,requested_by_id=foreign.created_by_id,selected_files=[])
            db.add(job);db.flush()
            visible=Evidence(incident_id=own.id,collected_by_id=own.created_by_id,filename='visible',size_bytes=0,sha256='b'*64,storage_key='never-read',created_at=stamp)
            hidden=Evidence(incident_id=own.id,collection_job_id=job.id,collection_item_id=uuid4(),source_path='fixture',collected_at=stamp,verified_at=stamp,verification_status='verified',collected_by_id=foreign.created_by_id,filename='hidden',size_bytes=0,sha256='c'*64,storage_key='private',created_at=datetime(2090,1,1,tzinfo=timezone.utc))
            db.add_all([visible,hidden]);db.flush()
            for evidence in (visible,hidden):
                db.add(TimelineEvent(incident_id=own.id,evidence_id=evidence.id,recorded_by_id=own.created_by_id,occurred_at=datetime(2099,1,1,tzinfo=timezone.utc),created_at=evidence.created_at,title='test',source='legacy'))
                with patch('app.services.custody.utc_now',return_value=evidence.created_at):ensure_baseline(db,evidence,uuid4())
            db.commit()
        summary=self.detail(include_intelligence=True).json()['intelligence']
        self.assertEqual(summary['evidence_count'],1)
        self.assertEqual(summary['timeline_count'],1)
        self.assertEqual(summary['latest_activity_at'],'2035-01-01T00:00:00Z')



