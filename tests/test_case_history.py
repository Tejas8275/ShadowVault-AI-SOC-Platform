import unittest
import json
from io import StringIO
from uuid import UUID
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from sqlalchemy import select, text, func
from sqlalchemy.exc import OperationalError, IntegrityError
from app.models import CaseHistoryEvent, Incident, User
from app.services import case_history
import test_incidents as fixtures


class HistoryTests(unittest.TestCase):
    setUp=fixtures.CaseTests.setUp
    tearDown=fixtures.CaseTests.tearDown
    edit=fixtures.CaseTests.edit
    get=fixtures.CaseTests.get

    def history(self,id=None,**params):
        return self.get('/'+(id or self.id)+'/history',**params)

    def test_created_attribution_and_read_only_revision_zero(self):
        response=self.client.post(self.base,headers=self.headers,json={'title':'Created'})
        record=response.json();history=self.history(record['id'])
        self.assertEqual(history.headers['cache-control'],'no-store')
        event=history.json()['items'][0]
        self.assertEqual(event['revision'],0);self.assertEqual(event['event_type'],'case_created')
        self.assertEqual(event['actor_user_id'],str(self.settings.operator_user_id))
        self.assertEqual(event['actor_label'],'Owner');self.assertEqual(event['source'],'api')
        self.assertEqual(event['recorded_at'],record['created_at'])
        self.assertEqual(event['changes']['title'],{'before':None,'after':'Created'})
        with self.factory() as db:db.get(User,self.settings.operator_user_id).display_name='Renamed';db.commit()
        self.assertEqual(self.history(record['id']).json()['items'][0]['actor_label'],'Owner')
        self.assertEqual(self.get('/'+record['id']).json(),record)

    def test_updates_group_changes_close_reopen_and_noop(self):
        initial=self.get('/'+self.id).json()
        for status,rev in [('investigating',0),('closed',1),('investigating',2),('investigating',3)]:
            self.assertEqual(self.edit(status=status,expected_revision=rev).status_code,200)
        rows=self.history().json()['items']
        self.assertEqual([r['revision'] for r in rows],[1,2,3,4])
        self.assertEqual(set(rows[0]['changes']),{'title','description','status','severity'})
        self.assertEqual(rows[0]['changes']['title']['before'],initial['title'])
        self.assertEqual(rows[1]['changes'],{'status':{'before':'investigating','after':'closed'}})
        self.assertEqual(rows[-1]['changes'],{})
        self.assertEqual(rows[-1]['recorded_at'],self.get('/'+self.id).json()['updated_at'])

    def test_history_authorization_bounds_and_no_mutation_routes(self):
        for headers in ({},{'Authorization':'Bearer sv_agent_wrong'}):
            self.assertEqual(self.client.get(self.base+'/'+self.id+'/history',headers=headers).status_code,401)
        self.assertEqual(self.history(self.foreign).status_code,404)
        for params in ({'limit':0},{'limit':101},{'after_revision':-1}):self.assertEqual(self.history(**params).status_code,422)
        self.assertEqual(self.history().json(),{'items':[],'tracking_started':False,'tracking_started_revision':None,'next_revision':None})
        for method in ('POST','PATCH','DELETE'):
            self.assertEqual(self.client.request(method,self.base+'/'+self.id+'/history',headers=self.headers,json={}).status_code,405)
        with self.factory() as db:db.get(User,self.settings.operator_user_id).is_active=False;db.commit()
        self.assertEqual(self.history().status_code,401)

    def test_history_failure_and_commit_failure_roll_back_case(self):
        initial=self.get('/'+self.id).json()
        def fail(db,*args,**kwargs):
            original(db,*args,**kwargs)
            raise OperationalError('private',{},Exception('secret'))
        original=case_history.append
        with patch('app.services.case_history.append',side_effect=fail):
            self.assertEqual(self.edit().status_code,503)
            self.assertEqual(self.client.post(self.base,headers=self.headers,json={'title':'failed'}).status_code,503)
        with patch('sqlalchemy.orm.Session.commit',side_effect=OperationalError('private',{},Exception('secret'))):
            self.assertEqual(self.edit().status_code,503)
        self.assertEqual(self.get('/'+self.id).json(),initial)
        self.assertEqual(self.history().json()['items'],[])
        self.assertEqual(self.get().json()['total'],1)

    def test_concurrent_writes_and_stale_replay_produce_one_event(self):
        barrier=Barrier(2)
        def save(_):barrier.wait();return self.edit().status_code
        with ThreadPoolExecutor(max_workers=2) as pool:codes=list(pool.map(save,range(2)))
        self.assertEqual(sorted(codes),[200,409])
        self.assertEqual(self.edit().status_code,409)
        self.assertEqual(len(self.history().json()['items']),1)

    def test_append_only_orm_and_sql_and_unique_revision(self):
        self.assertEqual(self.edit().status_code,200)
        with self.factory() as db:
            row=db.scalar(select(CaseHistoryEvent))
            row.actor_label='tampered'
            with self.assertRaisesRegex(ValueError,'append-only'):db.flush()
            db.rollback();row=db.scalar(select(CaseHistoryEvent));db.delete(row)
            with self.assertRaisesRegex(ValueError,'append-only'):db.flush()
            db.rollback()
        for sql in ('update case_history_events set actor_label=actor_label','delete from case_history_events'):
            with self.engine.begin() as c:
                with self.assertRaisesRegex(IntegrityError,'append-only'):c.execute(text(sql))
        with self.engine.begin() as c:
            with self.assertRaises(IntegrityError):
                c.execute(text("INSERT INTO case_history_events SELECT replace(id,substr(id,1,1),'f'),incident_id,revision,event_type,schema_version,actor_type,actor_user_id,actor_label,system_actor,recorded_at,changes,source FROM case_history_events"))

    def test_pagination_and_rejected_audit_fields(self):
        self.assertEqual(self.edit(actor_label='spoof').status_code,422)
        self.assertEqual(self.edit(status='closed').status_code,422)
        for rev in range(3):self.assertEqual(self.edit(expected_revision=rev).status_code,200)
        first=self.history(limit=1).json();second=self.history(limit=1,after_revision=first['next_revision']).json()
        self.assertEqual(first['tracking_started_revision'],1)
        self.assertEqual(second['items'][0]['revision'],2)
        self.assertEqual(self.history(after_revision=3).json()['items'],[])

    def test_trusted_cli_creation_is_tracked_without_output_change(self):
        from app.cli import main
        output=StringIO()
        with patch('app.cli.Settings',return_value=self.settings),patch('sys.argv',['cli','create-incident','--title','CLI case']),patch('sys.stdout',output):main()
        result=json.loads(output.getvalue());self.assertEqual(set(result),{'incident_id','title'})
        row=self.history(result['incident_id']).json()['items'][0]
        self.assertEqual(row['source'],'trusted_cli');self.assertEqual(row['actor_user_id'],str(self.settings.operator_user_id))
