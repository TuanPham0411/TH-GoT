"""Verify progression is meaningful, stage-scoped and cannot be forged by the client."""
import json,random
from test_auth import ApplicationTest
from auth import connect
from world_content import ACTIVITIES,JOURNEYS,PROFILES
from world_rounds import make_round,correct


class JourneyTests(ApplicationTest):
 def setUp(self):
  super().setUp();self.google_login()
  with self.client.session_transaction() as session:self.csrf=session['csrf']
  self.headers={'X-CSRF-Token':self.csrf}
 def session(self,profile):
  response=self.client.post('/api/sessions',json={'profile':profile,'csrf':self.csrf,'duration_minutes':10})
  self.assertEqual(response.status_code,200)
  return response.json['launch_url'].split('session=')[1]
 def post(self,path,body):return self.client.post('/api/world/'+path,json=body,headers=self.headers)
 def test_eight_stages_have_four_coherent_chapters_and_allowed_activities(self):
  self.assertEqual(len(PROFILES),8)
  for stage,journey in JOURNEYS.items():
   self.assertEqual(len(journey['chapters']),4);self.assertTrue(journey['intro'])
   for chapter in journey['chapters']:
    self.assertTrue(chapter['setup']);self.assertEqual(len(chapter['steps']),3)
    for step in chapter['steps'][:2]:
     activity=next(a for a in ACTIVITIES if a['id']==step['activity']);self.assertIn(stage,activity['profiles'])
     for seed in range(4):
      random.seed(seed);task,expected=make_round(activity,stage)
      self.assertTrue(task['prompt']);self.assertNotIn('answer',task)
      if not isinstance(expected,dict):self.assertTrue(correct(expected,expected))
    self.assertEqual(chapter['steps'][-1]['kind'],'reflection')
 def test_client_cannot_skip_steps_or_forge_grade_activity_or_completion(self):
  token=self.session('kindergarten-3');base={'session':token,'chapter':'chapter-1','step':'share','reflected':True}
  self.assertEqual(self.post('journey/reflect',base).status_code,409)
  self.assertEqual(self.post('round',{'session':token,'activity':'shape-garden','journey':{'chapter':'chapter-1','step':'try-2'}}).status_code,400)
  self.assertEqual(self.post('round',{'session':token,'activity':'decimal-market','profile':'grade-5'}).status_code,404)
  for index,activity in enumerate(['shape-garden','color-lantern'],1):
   response=self.post('round',{'session':token,'activity':activity,'journey':{'chapter':'chapter-1','step':'try-'+str(index)}});self.assertEqual(response.status_code,200)
   with self.app.app_context(),connect() as db:expected=json.loads(db.execute('SELECT expected FROM world_rounds WHERE id=?',(response.json['round'],)).fetchone()['expected'])
   answer=self.post('answer',{'session':token,'round':response.json['round'],'answer':expected});self.assertTrue(answer.json['ok']);self.assertIsNotNone(answer.json['journey'])
  reflected=self.post('journey/reflect',base);self.assertEqual(reflected.status_code,200);self.assertEqual(len(reflected.json['completed']),3)
  self.assertEqual(len(self.post('journey/reflect',base).json['completed']),3)
  self.assertEqual(self.client.get('/api/world/journey?profile=grade-1').json['completed'],[])
  other=self.app.test_client();self.google_login(other,sub='other-account',email='other@example.invalid')
  self.assertEqual(other.get('/api/world/journey?profile=kindergarten-3').json['completed'],[])
 def test_grade_changes_questions_not_only_labels(self):
  activity=next(a for a in ACTIVITIES if a['kind']=='count')
  for stage,limit in [('kindergarten-3',3),('kindergarten-4',5),('kindergarten-5',10)]:
   for _ in range(20):self.assertLessEqual(make_round(activity,stage)[0]['visual']['count'],limit)
  for kind in ['decimal','percent','volume','speed']:
   activity=next(a for a in ACTIVITIES if a['kind']==kind)
   task,expected=make_round(activity,'grade-5');self.assertIn(expected,[o['id'] for o in task['options']])
 def test_legacy_sessions_and_channel_permissions_remain_usable(self):
  for old in ['preschool','early-primary','middle-primary','upper-primary']:self.session(old)
  token=self.session('grade-5')
  self.assertEqual(self.post('round',{'session':token,'activity':'percent-city'}).status_code,200)
 def test_only_owner_can_end_a_session_and_previous_deadline_is_closed(self):
  token=self.session('grade-1')
  other=self.app.test_client();self.google_login(other,sub='other-end',email='other@example.invalid')
  with other.session_transaction() as session:csrf=session['csrf']
  response=other.post('/api/world/session/end',json={'session':token},headers={'X-CSRF-Token':csrf});self.assertEqual(response.status_code,404)
  self.assertEqual(self.post('session/end',{'session':token}).status_code,200)
  self.assertEqual(self.client.get('/api/sessions/'+token).status_code,410)
  self.assertEqual(self.post('round',{'session':token,'activity':'add-market'}).status_code,410)
