import json,random,os,time
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from test_auth import ApplicationTest
import auth,drive_store,learning_world
from world_content import ACTIVITIES,STORIES,PROFILES
from world_rounds import make_round,correct

class WorldTests(ApplicationTest):
 def setUp(self):
  super().setUp();self.google_login()
  with self.client.session_transaction() as s:self.csrf=s['csrf']
  self.headers={'X-CSRF-Token':self.csrf}
 def start(self,profile='preschool'):
  return self.client.post('/api/sessions',json={'csrf':self.csrf,'profile':profile,'duration_minutes':10}).json['launch_url'].split('session=')[1]
 def post(self,path,body):return self.client.post('/api/world/'+path,json=body,headers=self.headers)
 def admin(self):os.environ['ADMIN_EMAILS']='person@example.invalid'
 def test_catalog_and_all_activity_generators_have_real_valid_answers(self):
  self.assertGreaterEqual(len(ACTIVITIES),65);self.assertGreaterEqual(len(STORIES),24)
  for a in ACTIVITIES:
   for profile in a['profiles']:
    for seed in range(3):
     random.seed(seed);task,expected=make_round(a,profile)
     self.assertTrue(task['prompt']);self.assertNotIn('answer',task)
     if not isinstance(expected,dict):self.assertTrue(correct(expected,expected))
     if task['kind']=='choice':self.assertIn(expected,[x['id'] for x in task['options']]);self.assertEqual(len({x['label'] for x in task['options']}),len(task['options']))
  for story in STORIES:self.assertIn(len(story['pages']),range(4,9));self.assertIn(story['answer'],range(len(story['choices'])))
 def test_session_owner_expiry_round_profile_and_duplicate_progress(self):
  token=self.start();started=self.post('round',{'session':token,'activity':'count-garden'});self.assertEqual(started.status_code,200)
  with self.app.app_context(),auth.connect() as db:row=db.execute('SELECT expected FROM world_rounds WHERE id=?',(started.json['round'],)).fetchone();expected=json.loads(row['expected'])
  body={'session':token,'round':started.json['round'],'answer':expected}
  self.assertTrue(self.post('answer',body).json['ok']);self.assertEqual(self.post('answer',body).status_code,409)
  self.assertEqual(self.client.get('/api/world/progress').json['count-garden'],1)
  self.assertEqual(self.post('round',{'session':token,'activity':'word-problems'}).status_code,404)
  other=self.app.test_client();self.google_login(other,sub='google-user-2',email='other@example.invalid')
  with other.session_transaction() as s:other_csrf=s['csrf']
  self.assertEqual(other.post('/api/world/round',json={'session':token,'activity':'count-garden'},headers={'X-CSRF-Token':other_csrf}).status_code,404)
  self.assertEqual(other.get('/api/sessions/'+token).status_code,404)
  with self.app.app_context(),auth.connect() as db:db.execute('UPDATE game_sessions SET expires_at=? WHERE token=?',('2000-01-01T00:00:00+00:00',token))
  self.assertEqual(self.post('round',{'session':token,'activity':'count-garden'}).status_code,410)
 def test_robot_bridge_creative_and_typed_answers(self):
  task,expected=make_round(next(a for a in ACTIVITIES if a['kind']=='robot'),'middle-primary')
  self.assertTrue(correct(expected,['right']*3+['down']*3));self.assertFalse(correct(expected,['down','right','down','right','down','right']))
  self.assertFalse(correct(expected,['left']));self.assertFalse(correct(expected,['bad']))
  self.assertTrue(correct({'kind':'bridge'},list(range(6))));self.assertFalse(correct({'kind':'bridge'},[0,1,2,3,4,11]))
  self.assertTrue(correct({'kind':'draw'},{'strokes':3}));self.assertFalse(correct({'kind':'draw'},{'strokes':True}))
  self.assertFalse(correct({'kind':'journal'},{'characters':2}))
 def test_admin_csrf_and_secret_redaction(self):
  self.assertEqual(self.client.get('/parents').status_code,403);self.assertEqual(self.client.get('/api/world/admin/settings').status_code,403)
  self.admin();self.assertEqual(self.client.get('/parents').status_code,200)
  self.assertEqual(self.client.post('/api/world/admin/settings',json={'aiKey':'secret-value-for-test'}).status_code,403)
  result=self.post('admin/settings',{'aiProvider':'openai','aiModel':'gpt-4.1-mini','aiKey':'secret-value-for-test','youtubeKey':'youtube-secret-test','aiEnabled':True})
  self.assertEqual(result.status_code,200);self.assertNotIn('secret-value',result.data.decode());self.assertTrue(result.json['aiKeyConfigured'])
  with self.app.app_context():raw=learning_world.document('settings',{});self.assertNotEqual(raw['aiKey'],'secret-value-for-test');self.assertEqual(learning_world.decrypt(raw['aiKey']),'secret-value-for-test')
  self.assertNotIn('secret-value',self.client.get('/api/world/catalog').data.decode())
  self.assertEqual(self.post('admin/settings',{'aiProvider':'evil','aiModel':'http://internal'}).status_code,400)
 def test_video_allowlist_is_enforced_for_id_channel_age_and_revocation(self):
  token=self.start();channel='UC'+'a'*22;video='b'*11
  with self.app.app_context():learning_world.save('settings',{'channels':[{'id':channel,'title':'Approved','profiles':['preschool'],'enabled':True}],'videos':[{'id':video,'channelId':channel,'title':'Approved video','channelTitle':'Approved'},{'id':'c'*11,'channelId':'UC'+'z'*22,'title':'Other'}]})
  self.assertEqual(len(self.client.get('/api/world/videos?profile=preschool').json['videos']),1)
  self.assertEqual(len(self.client.get('/api/world/videos?profile=upper-primary').json['videos']),0)
  self.assertEqual(self.post('video',{'session':token,'id':video}).status_code,200)
  self.assertEqual(self.post('video',{'session':token,'id':'c'*11}).status_code,404)
  self.admin();self.assertEqual(self.post('admin/channels',{'id':channel,'action':'delete'}).status_code,200)
  self.assertEqual(self.post('video',{'session':token,'id':video}).status_code,404)
 def test_video_sync_rejects_wrong_channel_private_age_restricted_and_unembeddable(self):
  self.admin();channel='UC'+'a'*22;other='UC'+'z'*22;ids=[str(i)*11 for i in range(6)]
  with self.app.app_context():learning_world.save('settings',{'channels':[{'id':channel,'title':'Approved','profiles':['preschool'],'enabled':True,'uploads':'UPLOADS'}],'youtubeKey':drive_store.cipher().encrypt(b'test-key-for-youtube').decode()})
  items=[]
  for i,id in enumerate(ids):items.append({'id':id,'snippet':{'channelId':other if i==1 else channel,'title':'Video','liveBroadcastContent':'live' if i==5 else 'none'},'status':{'privacyStatus':'private' if i==2 else 'public','embeddable':i!=3},'contentDetails':{'contentRating':{'ytRating':'ytAgeRestricted'} if i==4 else {}}})
  with patch.object(learning_world,'youtube_api',side_effect=[{'items':[{'contentDetails':{'videoId':id}} for id in ids]},{'items':items}]):result=self.post('admin/videos/sync',{'id':channel})
  self.assertEqual(result.json['count'],1)
 def draft(self):return {'title':'Hạt mầm nhỏ','value':'Kiên nhẫn','pages':[{'title':'Một ngày','text':'Bạn nhỏ chăm sóc hạt mầm và quan sát điều mới.'} for _ in range(4)],'question':'Bạn nhỏ đã làm gì?','choices':['Chăm cây','Bỏ mặc cây'],'answer':0,'illustrations':[]}
 def test_ai_is_admin_only_disabled_by_default_and_drafts_need_explicit_review_and_drive_ack(self):
  self.assertEqual(self.post('admin/generate',{'kind':'story','profile':'preschool','topic':'Hạt mầm'}).status_code,403)
  self.admin();self.assertEqual(self.post('admin/generate',{'kind':'story','profile':'preschool','topic':'Hạt mầm'}).status_code,400)
  value=self.post('admin/drafts',{'kind':'story','profile':'preschool','content':self.draft()});self.assertEqual(value.status_code,200);draft=value.json['draft']
  self.assertNotIn(draft['id'],[s['id'] for s in self.client.get('/api/world/catalog').json['stories']])
  self.assertEqual(self.post('admin/publish',{'draftId':draft['draftId']}).status_code,400)
  with patch.object(drive_store,'connected',return_value='admin'),patch.object(drive_store,'store') as store:
   store.return_value.write_document.side_effect=drive_store.DriveUnavailable('Drive unavailable')
   self.assertEqual(self.post('admin/publish',{'draftId':draft['draftId'],'reviewed':True}).status_code,503)
  self.assertNotIn(draft['id'],[s['id'] for s in self.client.get('/api/world/catalog').json['stories']])
  with patch.object(drive_store,'connected',return_value='admin'),patch.object(drive_store,'store') as store:self.assertEqual(self.post('admin/publish',{'draftId':draft['draftId'],'reviewed':True}).status_code,200);store.return_value.write_document.assert_called_once()
  self.assertIn(draft['id'],[s['id'] for s in self.client.get('/api/world/catalog').json['stories']])
  edited=self.draft();edited['title']='Hạt mầm đã sửa';result=self.post('admin/drafts',{'draftId':draft['draftId'],'kind':'story','profile':'preschool','content':edited});self.assertEqual(result.json['draft']['id'],draft['id'])
 def test_provider_request_and_untrusted_draft_shape_validation(self):
  self.admin();self.post('admin/settings',{'aiProvider':'openai','aiModel':'gpt-4.1-mini','aiKey':'test-ai-secret-value','aiEnabled':True})
  import io
  payload=json.dumps({'choices':[{'message':{'content':json.dumps(self.draft())}}]}).encode()
  with patch.object(learning_world.urllib.request,'urlopen',return_value=io.BytesIO(payload)) as provider:
   response=self.post('admin/generate',{'kind':'story','profile':'preschool','topic':'Hạt mầm kiên nhẫn'})
  self.assertEqual(response.status_code,200);self.assertEqual(provider.call_args.args[0].full_url,'https://api.openai.com/v1/chat/completions');self.assertNotIn('test-ai-secret-value',response.data.decode())
  invalid=self.draft();invalid['pages']=[None]*4
  self.assertEqual(self.post('admin/drafts',{'kind':'story','profile':'preschool','content':invalid}).status_code,400)
  invalid=self.draft();invalid['title']='<script>alert(1)</script>'
  self.assertEqual(self.post('admin/drafts',{'kind':'story','profile':'preschool','content':invalid}).status_code,400)
  self.assertEqual(self.post('round',[]).status_code,400)
 def test_vietnamese_font_has_all_precomposed_tone_letters(self):
  from PIL import ImageFont
  from pathlib import Path
  for weight in ['Regular','Bold']:
   font=ImageFont.truetype(str(Path(__file__).parents[1]/'game/static/fonts'/f'NotoSans-{weight}.ttf'),32)
   missing=bytes(font.getmask('\uffff'))
   for character in 'ăâđêôơưĂÂĐÊÔƠƯ'+''.join(chr(i) for i in range(0x1ea0,0x1efa)):
    self.assertNotEqual(bytes(font.getmask(character)),missing,f'{weight}: {character}')
 def test_gemini_adapter_and_provider_switch_do_not_reuse_wrong_key(self):
  import io
  self.admin();self.post('admin/settings',{'aiProvider':'gemini','aiModel':'gemini-2.5-flash','aiKey':'gemini-test-secret','aiEnabled':True})
  payload=json.dumps({'candidates':[{'content':{'parts':[{'text':json.dumps(self.draft())}]}}]}).encode()
  with patch.object(learning_world.urllib.request,'urlopen',return_value=io.BytesIO(payload)) as provider:
   response=self.post('admin/generate',{'kind':'story','profile':'preschool','topic':'Chia sẻ cùng bạn'})
  self.assertEqual(response.status_code,200);self.assertEqual(provider.call_args.args[0].full_url,'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent')
  response=self.post('admin/settings',{'aiProvider':'openai','aiModel':'gpt-4.1-mini','aiEnabled':True});self.assertFalse(response.json['aiKeyConfigured'])
