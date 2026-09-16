import unittest
from uuid import UUID, uuid4
from datetime import datetime, timezone
from unittest.mock import patch
from sqlalchemy import select, MetaData, text
from sqlalchemy.exc import OperationalError, IntegrityError
import test_incidents
from app.models import Evidence, IndicatorObservation, Incident, Agent, CollectionJob
from app.schemas.indicator import normalize

class IndicatorTests(unittest.TestCase):
    setUp=test_incidents.CaseTests.setUp
    tearDown=test_incidents.CaseTests.tearDown

    def evidence(self,foreign=False,hidden=False):
        with self.factory() as db:
            case=db.get(Incident,UUID(self.foreign if foreign else self.id))
            item=Evidence(incident_id=case.id,collected_by_id=case.created_by_id,filename='Sample.txt',size_bytes=0,sha256='a'*64,storage_key=str(uuid4()))
            if hidden:
                other=db.get(Incident,UUID(self.foreign)).created_by_id
                stamp=datetime.now(timezone.utc)
                agent=Agent(name='hidden',collector_version='1',registered_by_id=other,token_sha256='b'*64,token_expires_at=stamp)
                db.add(agent);db.flush()
                job=CollectionJob(incident_id=case.id,agent_id=agent.id,requested_by_id=other,selected_files=[])
                db.add(job);db.flush()
                item.collection_job_id=job.id;item.collection_item_id=uuid4();item.source_path='fixture';item.collected_at=stamp;item.verified_at=stamp;item.verification_status='verified'
            db.add(item);db.commit();return str(item.id)

    def add(self,eid,**changes):
        body={'kind':'domain','raw_value':'Example.COM.','submission_id':str(uuid4()),**changes}
        return self.client.post('/api/v2/investigation/evidence/'+eid+'/indicators',headers=self.headers,json=body)

    def listing(self,case=None,**params):
        return self.client.get(self.base+'/'+(case or self.id)+'/indicators',headers=self.headers,params=params)

    def test_manual_kinds_metadata_and_utc(self):
        eid=self.evidence()
        for kind,raw,value in [('domain','Example.COM.','example.com'),('ip','2001:0db8::1','2001:db8::1'),('sha256','B'*64,'b'*64),('filename','Mixed.TXT','Mixed.TXT')]:
            result=self.add(eid,kind=kind,raw_value=raw)
            self.assertEqual(result.status_code,201,result.text)
            row=result.json();self.assertEqual(row['normalized_value'],value)
            self.assertEqual(row['created_by_id'],str(self.settings.operator_user_id))
            self.assertTrue(row['created_at'].endswith('Z'))
            self.assertNotIn('request_sha256',row)
        row=self.add(eid,kind='sha256',source_kind='evidence_sha256',raw_value=None).json()
        self.assertEqual(row['normalized_value'],'a'*64);self.assertEqual(row['source_locator'],'sha256')
        row=self.add(eid,kind='filename',source_kind='evidence_filename',raw_value=None).json()
        self.assertEqual(row['raw_value'],'Sample.txt')
        self.assertEqual(len(self.listing().json()['items']),6)

    def test_validation_and_no_spoofed_fields(self):
        eid=self.evidence()
        for kind,value in [('ip','127.1'),('ip','1.2.3.4:80'),('ip','fe80::1%eth0'),('ip','10.0.0.0/8'),('domain','https://example.com'),('domain','1.2.3.4'),('domain','*.example.com'),('domain','é.com'),('domain','example[.]com'),('sha256','a'*63),('filename','C:\\secret'),('filename','a\x00b')]:
            with self.subTest(value=value): self.assertEqual(self.add(eid,kind=kind,raw_value=value).status_code,422)
        self.assertEqual(self.add(eid,actor_label='spoof').status_code,422)
        self.assertEqual(self.add(eid,kind='sha256',source_kind='evidence_sha256',raw_value='b'*64).status_code,422)
        self.assertEqual(self.listing().json()['items'],[])

    def test_authorization_hidden_evidence_and_cross_case(self):
        own=self.evidence(); foreign=self.evidence(foreign=True); hidden=self.evidence(hidden=True)
        for eid in [foreign,hidden]:self.assertEqual(self.add(eid).status_code,404)
        self.assertEqual(self.listing(self.foreign).status_code,404)
        self.assertEqual(self.listing(evidence_id=foreign).status_code,404)
        self.assertEqual(self.listing(evidence_id=hidden).status_code,404)
        self.assertEqual(self.client.get(self.base+'/'+self.id+'/indicators').status_code,401)
        self.assertEqual(self.client.post('/api/v2/investigation/evidence/'+own+'/indicators',headers={'Authorization':'Bearer wrong'},json={'kind':'ip','raw_value':'1.2.3.4','submission_id':str(uuid4())}).status_code,401)
        self.add(own);self.assertEqual(len(self.listing().json()['items']),1)

    def test_idempotency_corrections_and_scope(self):
        eid=self.evidence();submission=str(uuid4())
        first=self.add(eid,submission_id=submission).json()
        self.assertEqual(self.add(eid,submission_id=submission).json(),first)
        self.assertEqual(self.add(eid,submission_id=submission,raw_value='other.example').status_code,409)
        other=self.evidence()
        self.assertEqual(self.add(other,supersedes_id=first['id']).status_code,404)
        correction=self.add(eid,supersedes_id=first['id'],raw_value='correct.example')
        self.assertEqual(correction.status_code,201)
        self.assertEqual(self.add(eid,supersedes_id=first['id']).status_code,409)
        self.assertEqual(len(self.listing().json()['items']),2)

    def test_pagination_filters_and_cursor_binding(self):
        eid=self.evidence()
        for i in range(3):self.add(eid,raw_value=f'{i}.example.com')
        first=self.listing(limit=1).json();second=self.listing(limit=1,cursor=first['next_cursor']).json()
        self.assertNotEqual(first['items'][0]['id'],second['items'][0]['id'])
        self.assertEqual(self.listing(kind='ip',cursor=first['next_cursor']).status_code,422)
        self.assertEqual(len(self.listing(kind='domain',value='0.EXAMPLE.COM.').json()['items']),1)
        self.assertEqual(self.listing(value='example.com').status_code,422)
        self.assertEqual(self.listing(limit=101).status_code,422)

    def test_read_write_preserve_original_tables_and_rollback(self):
        eid=self.evidence()
        with self.engine.connect() as c:
            frozen=MetaData();frozen.reflect(c)
            before={n:c.execute(select(t)).all() for n,t in frozen.tables.items() if n!='indicator_observations'}
        self.assertEqual(self.add(eid).status_code,201);self.listing()
        with patch('sqlalchemy.orm.Session.commit',side_effect=OperationalError('private',{},Exception('secret'))):
            response=self.add(eid)
            self.assertEqual(response.status_code,503);self.assertNotIn('secret',response.text)
        self.assertEqual(len(self.listing().json()['items']),1)
        with self.engine.connect() as c:
            for n,rows in before.items(): self.assertEqual(c.execute(select(frozen.tables[n])).all(),rows,n)

    def test_append_only_database_and_orm(self):
        eid=self.evidence();row=self.add(eid).json()
        for sql in ["update indicator_observations set raw_value='bad'","delete from indicator_observations"]:
            with self.engine.begin() as c:
                with self.assertRaises(IntegrityError):c.execute(text(sql))
        with self.factory() as db:
            record=db.get(IndicatorObservation,UUID(row['id']));record.raw_value='changed'
            with self.assertRaises(ValueError):db.flush()
            db.rollback()
        response=self.client.delete('/api/v2/investigation/evidence/'+eid+'/indicators',headers=self.headers)
        self.assertEqual(response.status_code,405)
    def test_concurrent_submission_and_correction_only_create_one_successor(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from app.models import User
        from app.schemas.indicator import IndicatorCreate
        from app.services.indicators import create
        from fastapi import HTTPException
        eid=self.evidence()
        original=self.add(eid).json()
        for correction in (False,True):
            barrier=Barrier(2);submission=str(uuid4())
            def submit(index):
                payload=IndicatorCreate(kind='domain',raw_value='concurrent.example',submission_id=str(uuid4()) if correction else submission,supersedes_id=original['id'] if correction else None)
                with self.factory() as db:
                    actor=db.get(User,self.settings.operator_user_id);barrier.wait(timeout=10)
                    try:
                        create(db,UUID(eid),actor,payload);db.commit();return 201
                    except (IntegrityError,OperationalError):db.rollback();return 409
                    except HTTPException as error:db.rollback();return error.status_code
            with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(submit,range(2)))
            self.assertIn(201,statuses);self.assertTrue(all(s in (201,409) for s in statuses))
        self.assertEqual(len(self.listing().json()['items']),3)
    def test_successor_visible_across_pages_value_filters_and_lookup(self):
        eid=self.evidence();original=self.add(eid,raw_value='old.example').json()
        for index in range(50):self.add(eid,raw_value=f'filler{index}.example')
        correction=self.add(eid,raw_value='new.example',supersedes_id=original['id']).json()
        self.assertNotIn('superseded_by_id',correction)  # POST contract is unchanged.
        first=self.listing(limit=1).json()
        self.assertEqual(first['items'][0]['superseded_by_id'],correction['id'])
        filtered=self.listing(kind='domain',value='old.example').json()['items']
        self.assertEqual(filtered[0]['superseded_by_id'],correction['id'])
        looked=self.listing(observation_id=correction['id']).json()['items']
        self.assertEqual(len(looked),1);self.assertEqual(looked[0]['supersedes_id'],original['id'])
        self.assertIsNone(looked[0]['superseded_by_id'])
        self.assertEqual(self.listing(cursor=first['next_cursor'],observation_id=original['id']).status_code,422)
        self.assertEqual(self.listing(observation_id=str(uuid4())).json()['items'],[])

    def test_successor_and_lookup_never_expose_hidden_or_cross_evidence_rows(self):
        visible=self.evidence();hidden=self.evidence(hidden=True)
        original=self.add(visible).json()
        # Defensive read behavior even for a wrongly linked row written outside the API.
        with self.factory() as db:
            row=IndicatorObservation(incident_id=UUID(self.id),evidence_id=UUID(hidden),kind='domain',raw_value='hidden.example',normalized_value='hidden.example',source_kind='manual',created_by_id=self.settings.operator_user_id,actor_label='Owner',submission_id=uuid4(),request_sha256='a'*64,supersedes_id=UUID(original['id']))
            db.add(row);db.commit();hidden_id=str(row.id)
        self.assertIsNone(self.listing(observation_id=original['id']).json()['items'][0]['superseded_by_id'])
        self.assertEqual(self.listing(observation_id=hidden_id).json()['items'],[])
        self.assertEqual(self.listing(self.foreign,observation_id=original['id']).status_code,404)
