import tempfile
import unittest
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from sqlalchemy.exc import OperationalError
from app.core.config import BACKEND_DIR, Settings
from app.core.security import token_digest
from app.db.migrate import upgrade_database
from app.db.session import build_engine, build_session_factory
from app.main import create_app
from app.models import User, Incident


class CaseTests(unittest.TestCase):
    def test_severity_filter_is_owned_bound_and_read_only(self):
        from uuid import UUID
        with self.factory() as db:
            db.get(Incident,UUID(self.foreign)).severity='critical';db.commit()
        for title in ('First critical','Second critical'):
            self.assertEqual(self.client.post(self.base,headers=self.headers,json={'title':title,'severity':'critical'}).status_code,201)
        before=self.get().json()
        page=self.get(severity='critical',limit=1).json()
        self.assertEqual(page['total'],2)
        second=self.get(severity='critical',limit=1,cursor=page['next_cursor']).json()
        self.assertNotEqual(page['items'][0]['id'],second['items'][0]['id'])
        self.assertNotIn(self.foreign,[page['items'][0]['id'],second['items'][0]['id']])
        self.assertEqual(self.get(severity='low',cursor=page['next_cursor']).status_code,422)
        self.assertEqual(self.get(severity='urgent').status_code,422)
        self.assertEqual(self.get().json(),before)

    def test_timestamps_are_server_owned_atomic_and_preserved_on_failure(self):
        from datetime import datetime, timezone
        created=self.client.post(self.base,headers=self.headers,json={'title':'Timestamp'}).json()
        self.assertEqual(created['created_at'],created['updated_at'])
        initial=self.get('/'+self.id).json()
        stamp=datetime(2030,1,1,tzinfo=timezone.utc)
        with patch('app.services.incidents.utc_now',return_value=stamp):
            updated=self.edit().json()
        self.assertEqual(updated['updated_at'],'2030-01-01T00:00:00Z')
        self.assertEqual(updated['created_at'],initial['created_at'])
        self.assertEqual(self.edit().status_code,409)
        for field in ('created_at','updated_at'):
            self.assertEqual(self.edit(**{field:'2031-01-01T00:00:00Z'},expected_revision=1).status_code,422)
            self.assertEqual(self.client.post(self.base,headers=self.headers,json={'title':'spoof',field:'2031-01-01T00:00:00Z'}).status_code,422)
        with patch('sqlalchemy.orm.Session.commit',side_effect=OperationalError('test',{},Exception('private'))):
            self.assertEqual(self.edit(expected_revision=1).status_code,503)
        self.assertEqual(self.get('/'+self.id).json(),updated)
        # A migrated/untracked row remains readable without inventing a timestamp.
        from sqlalchemy import text
        with self.engine.begin() as c:
            c.execute(text('update incidents set updated_at=NULL where id=:id'),{'id':self.id.replace('-','')})
        self.assertIsNone(self.get('/'+self.id).json()['updated_at'])
        own=next(row for row in self.get().json()['items'] if row['id']==self.id)
        self.assertIsNone(own['updated_at'])

    def test_case_edit_preserves_evidence_timeline_and_custody(self):
        from uuid import UUID
        from sqlalchemy import MetaData
        from app.models import Evidence, TimelineEvent
        from app.models.common import utc_now
        from app.services.custody import ensure_baseline, verify_chain
        with self.factory() as db:
            evidence=Evidence(incident_id=UUID(self.id),collected_by_id=self.settings.operator_user_id,
                filename='original',size_bytes=0,sha256='a'*64,storage_key='unchanged')
            db.add(evidence);db.flush()
            ensure_baseline(db,evidence,uuid4())
            db.add(TimelineEvent(incident_id=UUID(self.id),evidence_id=evidence.id,
                recorded_by_id=self.settings.operator_user_id,occurred_at=utc_now(),title='Original',source='Legacy'))
            db.commit();eid=evidence.id
        with self.engine.connect() as c:
            old=MetaData();old.reflect(c)
            before={name:c.execute(select(table)).all() for name,table in old.tables.items() if name not in ('incidents','case_history_events')}
        self.assertEqual(self.edit().status_code,200)
        with self.engine.connect() as c:
            for name,rows in before.items():self.assertEqual(c.execute(select(old.tables[name])).all(),rows,name)
        with self.factory() as db:self.assertTrue(verify_chain(db,eid))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=BACKEND_DIR)
        self.settings = Settings(_env_file=None, environment='test', database_url=f'sqlite:///{Path(self.temp.name).as_posix()}/test.db',
            operator_token_sha256=token_digest('sv_operator_case'))
        upgrade_database(self.settings); self.engine = build_engine(self.settings); self.factory = build_session_factory(self.engine)
        with self.factory() as db:
            owner = User(email='case@example.test', display_name='Owner', password_hash='!disabled')
            other = User(email='other@example.test', display_name='Other', password_hash='!disabled')
            a = Incident(title='Own', created_by=owner); b = Incident(title='Foreign', created_by=other)
            db.add_all([a,b]); db.commit(); self.id, self.foreign = str(a.id), str(b.id); self.settings.operator_user_id = owner.id
        self.client = TestClient(create_app(self.settings)); self.client.__enter__()
        self.headers = {'Authorization': 'Bearer sv_operator_case'}; self.base = '/api/v2/investigation/incidents'

    def tearDown(self):
        self.client.__exit__(None,None,None); self.engine.dispose(); self.temp.cleanup()

    def get(self, suffix='', **params): return self.client.get(self.base+suffix, headers=self.headers, params=params)
    def edit(self, **values):
        return self.client.patch(self.base+'/'+self.id, headers=self.headers,
            json={'title':'Updated', 'description':'Explicit', 'severity':'high', 'status':'investigating', 'expected_revision':0, **values})

    def test_create_and_owner_scoped_list_detail(self):
        result = self.client.post(self.base, headers=self.headers, json={'title':' Created '})
        self.assertEqual(result.status_code,201); self.assertEqual(result.json()['title'],'Created')
        self.assertEqual(result.json()['status'],'open'); self.assertEqual(result.json()['revision'],0)
        self.assertEqual(result.json()['created_by_id'],str(self.settings.operator_user_id))
        self.assertEqual(self.get().json()['total'],2); self.assertEqual(self.get('/'+self.foreign).status_code,404)
        self.assertEqual(self.get('/'+str(uuid4())).status_code,404)

    def test_all_endpoints_require_operator_and_owner(self):
        for headers in [{}, {'Authorization':'Bearer sv_agent_fixture'}]:
            for method, suffix, payload in [('GET','',None),('GET','/'+self.id,None),('POST','',{'title':'x'}),
                ('PATCH','/'+self.id,{'title':'x','status':'open','expected_revision':0})]:
                self.assertEqual(self.client.request(method,self.base+suffix,headers=headers,json=payload).status_code,401)
        self.assertEqual(self.client.patch(self.base+'/'+self.foreign,headers=self.headers,
            json={'title':'stolen','status':'open','expected_revision':0}).status_code,404)
        with self.factory() as db: db.get(User,self.settings.operator_user_id).is_active=False; db.commit()
        self.assertEqual(self.get().status_code,401)

    def test_lifecycle_and_revision_conflicts(self):
        self.assertEqual(self.edit(status='closed').status_code,422)
        self.assertEqual(self.edit().json()['revision'],1)
        self.assertEqual(self.edit(title='stale').status_code,409)
        self.assertEqual(self.edit(status='closed',expected_revision=1).json()['revision'],2)
        self.assertEqual(self.edit(status='open',expected_revision=2).status_code,422)
        self.assertEqual(self.edit(status='investigating',expected_revision=2).json()['revision'],3)
        self.assertEqual(self.get('/'+self.id).json()['created_by_id'],str(self.settings.operator_user_id))

    def test_validation_rejects_owner_status_on_create_and_invalid_updates(self):
        for body in [{'title':' '},{'title':'x','status':'closed'},{'title':'x','created_by_id':str(uuid4())},
                     {'title':'x','revision':100},{'title':'x\u0000'},{'title':'x','description':'a'*10001}]:
            self.assertEqual(self.client.post(self.base,headers=self.headers,json=body).status_code,422)
        self.assertEqual(self.edit(expected_revision=True).status_code,422)
        self.assertEqual(self.edit(status='resolved').status_code,422)
        self.assertEqual(self.edit(created_by_id=str(uuid4())).status_code,422)

    def test_search_literal_filters_and_bound_cursor(self):
        for title in ['literal%_','literalAA','third']:
            self.client.post(self.base,headers=self.headers,json={'title':title,'severity':'critical'})
        self.assertEqual(self.get(q='%_').json()['total'],1)
        self.assertEqual(self.get(severity='critical').json()['total'],3)
        first=self.get(limit=1).json(); second=self.get(limit=1,cursor=first['next_cursor']).json()
        self.assertNotEqual(first['items'][0]['id'],second['items'][0]['id'])
        self.assertEqual(self.get(cursor=first['next_cursor'],q='changed').status_code,422)

    def test_commit_failure_rolls_back_and_preserves_revision(self):
        with patch('sqlalchemy.orm.Session.commit',side_effect=OperationalError('test',{},Exception('private'))):
            response=self.edit(); self.assertEqual(response.status_code,503); self.assertNotIn('private',response.text)
            self.assertEqual(self.client.post(self.base,headers=self.headers,json={'title':'failed'}).status_code,503)
        self.assertEqual(self.get('/'+self.id).json()['revision'],0)
        self.assertEqual(self.get().json()['total'],1)

    def test_compare_and_swap_failure_never_reports_success(self):
        from unittest.mock import Mock
        from sqlalchemy.sql.dml import Update
        from sqlalchemy.orm import Session
        original=Session.execute
        def execute(db, statement, *args, **kwargs):
            if isinstance(statement,Update) and statement.table.name=='incidents': return Mock(rowcount=0)
            return original(db,statement,*args,**kwargs)
        with patch.object(Session,'execute',execute): self.assertEqual(self.edit().status_code,409)
        self.assertEqual(self.get('/'+self.id).json()['revision'],0)

    def test_update_preserves_omitted_description_and_severity(self):
        self.assertEqual(self.edit().status_code,200)
        response=self.client.patch(self.base+'/'+self.id,headers=self.headers,
            json={'title':'Renamed','status':'investigating','expected_revision':1})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['description'],'Explicit')
        self.assertEqual(response.json()['severity'],'high')
        self.assertEqual(response.json()['revision'],2)
