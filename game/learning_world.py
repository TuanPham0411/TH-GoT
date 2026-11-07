"""Learning world, reviewed AI drafts and administrator-curated video catalog."""
from datetime import datetime,timezone
import json,os,re,secrets,time,urllib.request,urllib.parse,urllib.error
from flask import request,jsonify,render_template,current_app,abort,session
from auth import connect,user,valid_csrf
import drive_store
import journeys
from learning_profiles import LEGACY, STAGES, canonical, expand, allowed as profile_allowed
from world_content import ACTIVITIES,STORIES,PROFILES,SUBJECTS,ART,JOURNEYS
from world_rounds import make_round,correct

MODELS={'openai':['gpt-4.1-mini','gpt-4.1'],'gemini':['gemini-2.5-flash','gemini-2.5-pro']}

def payload():
 value=request.get_json(silent=True)
 if not isinstance(value,dict):raise ValueError('Dữ liệu gửi lên chưa hợp lệ.')
 return value

def document(name,default):
 with connect() as db:row=db.execute('SELECT value FROM world_documents WHERE name=?',(name,)).fetchone()
 return json.loads(row['value']) if row else default

def save(name,value):
 with connect() as db:db.execute('INSERT INTO world_documents(name,value) VALUES(?,?) ON CONFLICT(name) DO UPDATE SET value=excluded.value',(name,json.dumps(value,ensure_ascii=False)))

def require_admin():
 drive_store.require_admin()
 if request.method!='GET' and not valid_csrf():abort(403)

def throttle(key,limit=5,window=60):
 now=int(time.time())
 with connect() as db:
  db.execute('DELETE FROM world_requests WHERE created<?',(now-window,))
  if db.execute('SELECT COUNT(*) FROM world_requests WHERE owner=? AND kind=?',(user()['id'],key)).fetchone()[0]>=limit:abort(429,description='Vui lòng chờ trước khi thử lại')
  db.execute('INSERT INTO world_requests VALUES(?,?,?)',(user()['id'],key,now))

def decrypt(value):
 return drive_store.cipher().decrypt(value.encode()).decode() if value else ''

def settings(public=False):
 value=document('settings',{'channels':[],'videos':[],'aiProvider':'openai','aiModel':'gpt-4.1-mini','aiEnabled':False})
 for channel in value.get('channels',[]):channel['profiles']=expand(channel.get('profiles',[]))
 if public:return {'channels':value.get('channels',[]),'videos':value.get('videos',[])}
 return value

def catalogs():
 extra=document('published',{'stories':[],'activities':[]})
 return {key:[dict(item,profiles=expand(item.get('profiles',[]))) for item in builtin+extra.get(key,[])] for key,builtin in [('activities',ACTIVITIES),('stories',STORIES)]}

def verified_session(token):
 if not user():abort(401)
 if not isinstance(token,str) or not 32<=len(token)<=96:abort(400)
 with connect() as db:row=db.execute('SELECT * FROM game_sessions WHERE token=? AND user_id=?',(token,user()['id'])).fetchone()
 if not row:abort(404)
 if datetime.fromisoformat(row['expires_at'])<=datetime.now(timezone.utc):abort(410)
 return row

def youtube_api(resource,params,key):
 if not key:raise ValueError('Hãy cấu hình YouTube Data API key trước khi đồng bộ kênh.')
 url='https://www.googleapis.com/youtube/v3/'+resource+'?'+urllib.parse.urlencode({**params,'key':key})
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'Accept':'application/json'}),timeout=15) as response:return json.loads(response.read(2_000_001))
 except Exception:raise ValueError('YouTube chưa trả dữ liệu hợp lệ. Kiểm tra API key, quota và quyền nhúng video.') from None

def validate_draft(kind,value,profile):
 profile=canonical(profile)
 if not isinstance(value,dict):raise ValueError('Bản nháp phải là một đối tượng JSON.')
 def text(v,limit):
  if not isinstance(v,str) or not v.strip() or len(v)>limit or re.search(r'https?://|<[^>]+>',v):raise ValueError('Nội dung phải là văn bản thuần, có độ dài phù hợp.')
  return v.strip()
 clean={'title':text(value.get('title'),120),'profiles':[profile],'id':'custom-'+secrets.token_hex(8)}
 if kind=='story':
  pages=value.get('pages',[])
  if not isinstance(pages,list) or not 3<=len(pages)<=8 or any(not isinstance(p,dict) for p in pages):raise ValueError('Truyện cần 3–8 trang.')
  clean.update(origin='Sáng tác cho GoT',source='Nội dung do người lớn duyệt trước khi xuất bản.',value=text(value.get('value'),200),minutes=5,pages=[{'title':text(p.get('title'),100),'text':text(p.get('text'),1200)} for p in pages],question=text(value.get('question'),350))
  choices=value.get('choices',[])
  if not isinstance(choices,list) or not 2<=len(choices)<=4 or type(value.get('answer')) is not int or not 0<=value['answer']<len(choices):raise ValueError('Câu hỏi kết truyện cần đáp án hợp lệ.')
  clean.update(choices=[text(x,250) for x in choices],answer=value['answer'])
  pictures=value.get('illustrations',[])
  if not isinstance(pictures,list) or len(pictures)>8 or any(not drive_store.valid_path(x) or not x.startswith('images/') for x in pictures):raise ValueError('Minh họa phải dùng đường dẫn ảnh trong thư viện Drive.')
  clean['illustrations']=pictures
 else:
  questions=value.get('questions',[])
  if not isinstance(questions,list) or not 3<=len(questions)<=10 or any(not isinstance(q,dict) for q in questions):raise ValueError('Bài học cần 3–10 câu hỏi.')
  clean.update(subject=value.get('subject','language'),kind='ai_quiz',goal=text(value.get('goal'),300),lesson=text(value.get('lesson'),1500),home=text(value.get('home'),350),minutes=8,questions=[])
  if clean['subject'] not in SUBJECTS:raise ValueError('Lĩnh vực chưa hợp lệ.')
  for q in questions:
   choices=q.get('choices',[])
   if not isinstance(choices,list) or not 2<=len(choices)<=4 or type(q.get('answer')) is not int or not 0<=q['answer']<len(choices):raise ValueError('Câu hỏi cần đáp án hợp lệ.')
   clean['questions'].append({'prompt':text(q.get('prompt'),500),'choices':[text(x,250) for x in choices],'answer':q['answer'],'explanation':text(q.get('explanation'),500)})
 return clean

def ai_generate(kind,profile,topic):
 profile=canonical(profile)
 config=settings()
 if not config.get('aiEnabled') or not config.get('aiKey'):raise ValueError('AI chưa được quản trị viên cấu hình và bật.')
 provider=config['aiProvider'];key=decrypt(config['aiKey']);model=config['aiModel']
 schema=({'title':'Tên truyện','value':'Điều học được','pages':[{'title':'Tên trang','text':'Đoạn kể tiếng Việt'}]*4,'question':'Câu hỏi suy ngẫm','choices':['Lựa chọn 1','Lựa chọn 2','Lựa chọn 3'],'answer':0,'illustrations':[]} if kind=='story' else {'title':'Tên bài','subject':'science','goal':'Mục tiêu cụ thể','lesson':'Giải thích ngắn, đúng kiến thức','home':'Hoạt động cùng người lớn','questions':[{'prompt':'Câu hỏi','choices':['A','B','C'],'answer':0,'explanation':'Vì sao đáp án đúng'}]*5})
 prompt=('Bạn biên soạn giáo dục tiếng Việt cho '+PROFILES[profile]+'. Trọng tâm giai đoạn: '+STAGES[profile]['focus']+' Bối cảnh hành trình: '+JOURNEYS[profile]['title']+'. Mây là bạn đồng hành, xưng Mây và gọi trẻ là bạn; không xưng tớ với con. Truyện tạo bằng AI phải ghi là sáng tác mới, không tự nhận là nguyên bản truyện cổ hay nguồn lịch sử đã xác minh. Chủ đề do người lớn chọn: '+topic+'. Tạo '+('truyện 4 trang, mỗi trang 50–90 từ' if kind=='story' else 'bài học và 5 câu hỏi có đáp án đúng duy nhất')+'. Giọng ấm áp, không định kiến, không dọa nạt, không bạo lực hay nội dung tình dục, không quảng cáo, không xin thông tin cá nhân, không hướng dẫn hoạt động nguy hiểm hoặc chẩn đoán y tế. Mẫu giáo dùng từ ngắn và tình huống cụ thể; trẻ lớn có lập luận và câu hỏi mở. Nội dung mới, không sao chép tác phẩm còn bản quyền. Không bịa kiến thức; nếu không chắc thì chọn ví dụ đơn giản đã biết. Kết quả là bản nháp để người lớn kiểm tra, không gửi thẳng cho trẻ. Chỉ trả JSON theo cấu trúc: '+json.dumps(schema,ensure_ascii=False))
 if provider=='openai':
  url='https://api.openai.com/v1/chat/completions';payload={'model':model,'messages':[{'role':'system','content':'Soạn giáo dục phù hợp lứa tuổi, tuân thủ các ràng buộc và chỉ trả JSON.'},{'role':'user','content':prompt}],'response_format':{'type':'json_object'},'max_tokens':3500};headers={'Authorization':'Bearer '+key}
 else:
  url='https://generativelanguage.googleapis.com/v1beta/models/'+model+':generateContent';payload={'contents':[{'parts':[{'text':prompt}]}],'generationConfig':{'responseMimeType':'application/json','maxOutputTokens':3500}};headers={'x-goog-api-key':key}
 try:
  req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json',**headers},method='POST')
  with urllib.request.urlopen(req,timeout=30) as response:value=json.loads(response.read(150001))
  raw=value['choices'][0]['message']['content'] if provider=='openai' else ''.join(p.get('text','') for p in value['candidates'][0]['content']['parts'])
  result=json.loads(raw.strip().removeprefix('```json').removeprefix('```').removesuffix('```'))
 except Exception:raise ValueError('AI chưa tạo được bản nháp hợp lệ. Kiểm tra cấu hình hoặc thử lại sau; chưa có nội dung nào xuất bản.') from None
 return validate_draft(kind,result,profile)

def register(app):
 import realm_media
 realm_media.register(app)
 @app.before_request
 def world_size_limit():
  if request.path.startswith('/api/world/') and request.content_length and request.content_length>60000:abort(413)
 with app.app_context(),connect() as db:
  db.executescript('''CREATE TABLE IF NOT EXISTS world_documents(name TEXT PRIMARY KEY,value TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS world_rounds(id TEXT PRIMARY KEY,owner INTEGER NOT NULL,session_token TEXT NOT NULL,activity TEXT NOT NULL,expected TEXT NOT NULL,expires INTEGER NOT NULL,completed INTEGER NOT NULL DEFAULT 0,attempts INTEGER NOT NULL DEFAULT 0);
  CREATE TABLE IF NOT EXISTS world_progress(owner INTEGER NOT NULL,activity TEXT NOT NULL,completed INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(owner,activity));
  CREATE TABLE IF NOT EXISTS world_requests(owner INTEGER NOT NULL,kind TEXT NOT NULL,created INTEGER NOT NULL);''')
 journeys.register(app,verified_session)
 @app.get('/world')
 def world():return render_template('world.html',profiles=PROFILES,subjects=SUBJECTS,is_admin=drive_store.admin())
 @app.get('/parents')
 def parents():
  drive_store.require_admin();return render_template('world_parents.html',profiles=PROFILES,subjects=SUBJECTS)
 @app.get('/api/world/catalog')
 def catalog():
  content=catalogs();content.update(profiles=PROFILES,subjects=SUBJECTS,stages=STAGES,journeys=JOURNEYS,legacyProfiles={key:canonical(key) for key in LEGACY})
  return jsonify(content)
 @app.get('/api/world/progress')
 def progress():
  if not user():return jsonify({})
  with connect() as db:rows=db.execute('SELECT activity,completed FROM world_progress WHERE owner=?',(user()['id'],)).fetchall()
  return jsonify({row['activity']:row['completed'] for row in rows})
 @app.post('/api/world/round')
 def start_round():
  body=payload()
  if not valid_csrf():abort(403)
  game_session=verified_session(body.get('session'));throttle('round',60);profile=canonical(json.loads(game_session['config_json'])['profile'])
  activity=next((x for x in catalogs()['activities'] if x['id']==body.get('activity') and profile in x['profiles']),None)
  if not activity:abort(404)
  context=body.get('journey')
  if context is not None:
   if not isinstance(context,dict):abort(400)
   journeys.validate_step(user()['id'],profile,context.get('chapter'),context.get('step'),activity=activity['id'])
  task,expected=make_round(activity,profile);token=secrets.token_urlsafe(24);expires=int(datetime.fromisoformat(game_session['expires_at']).timestamp())
  with connect() as db:
   db.execute('DELETE FROM world_rounds WHERE expires<?',(int(time.time()),))
   if db.execute('SELECT COUNT(*) FROM world_rounds WHERE owner=? AND completed=0',(user()['id'],)).fetchone()[0]>60:db.execute('DELETE FROM world_rounds WHERE owner=? AND completed=0',(user()['id'],))
   db.execute('INSERT INTO world_rounds(id,owner,session_token,activity,expected,expires) VALUES(?,?,?,?,?,?)',(token,user()['id'],game_session['token'],activity['id'],json.dumps(expected),expires))
   if context:db.execute('UPDATE world_rounds SET journey_chapter=?,journey_step=? WHERE id=?',(context['chapter'],context['step'],token))
  return jsonify(round=token,task=task)
 @app.post('/api/world/answer')
 def submit():
  body=payload()
  if not valid_csrf():abort(403)
  active_session=verified_session(body.get('session'))
  active_profile=canonical(json.loads(active_session['config_json'])['profile'])
  journey_state=None
  with connect() as db:
   db.execute('BEGIN IMMEDIATE')
   row=db.execute('SELECT * FROM world_rounds WHERE id=? AND owner=? AND session_token=?',(body.get('round',''),user()['id'],body['session'])).fetchone()
   if not row:abort(404)
   if row['completed'] or row['attempts']>=5:return jsonify(ok=False,message='Lượt này đã kết thúc. Hãy mở thử thách mới.'),409
   accepted=correct(json.loads(row['expected']),body.get('answer'))
   db.execute('UPDATE world_rounds SET attempts=attempts+1,completed=? WHERE id=?',(int(accepted),row['id']))
   if accepted:db.execute('INSERT INTO world_progress VALUES(?,?,1) ON CONFLICT(owner,activity) DO UPDATE SET completed=completed+1',(user()['id'],row['activity']))
   if accepted and row['journey_chapter']:
    journeys.record(db,user()['id'],active_profile,row['journey_chapter'],row['journey_step'])
    journey_state=journeys.state(user()['id'],active_profile,db)
  return jsonify(journey=journey_state,ok=accepted,message='Bạn đã hoàn thành! Kể cho Mây nghe cách bạn làm nhé.' if accepted else 'Chưa khớp. Thử đọc gợi ý, quan sát lại rồi làm từng bước nhé.',attempts=row['attempts']+1)
 @app.get('/api/world/videos')
 def videos():
  config=settings();channels={c['id']:c for c in config.get('channels',[]) if c.get('enabled',True)}
  profile=request.args.get('profile','preschool')
  return jsonify(channels=list(channels.values()),videos=[v for v in config.get('videos',[]) if v['channelId'] in channels and profile_allowed(channels[v['channelId']]['profiles'],profile)])
 @app.post('/api/world/video')
 def video():
  body=payload()
  if not valid_csrf():abort(403)
  row=verified_session(body.get('session'));profile=json.loads(row['config_json'])['profile'];config=settings()
  allowed={c['id'] for c in config.get('channels',[]) if c.get('enabled',True) and profile_allowed(c['profiles'],profile)}
  v=next((x for x in config.get('videos',[]) if x['id']==body.get('id') and x['channelId'] in allowed),None)
  if not v:abort(404)
  return jsonify(video=v,embed='https://www.youtube-nocookie.com/embed/'+v['id'])
 @app.route('/api/world/admin/settings',methods=['GET','POST'])
 def admin_settings():
  require_admin();config=settings()
  if request.method=='POST':
   body=payload();provider=body.get('aiProvider',config.get('aiProvider','openai'));model=body.get('aiModel',MODELS.get(provider,[''])[0])
   if provider not in MODELS or model not in MODELS[provider]:abort(400)
   for key in ['aiKey','youtubeKey']:
    if key in body and body[key]:
     if not isinstance(body[key],str) or not 10<=len(body[key])<=1000:abort(400)
     config[key]=drive_store.cipher().encrypt(body[key].strip().encode()).decode()
    if body.get('clear'+key[0].upper()+key[1:]) is True:config.pop(key,None)
   if provider!=config.get('aiProvider','openai') and not body.get('aiKey'):config.pop('aiKey',None)
   config.update(aiProvider=provider,aiModel=model,aiEnabled=body.get('aiEnabled') is True);save('settings',config)
  result={k:v for k,v in config.items() if k not in ['aiKey','youtubeKey']};result.update(aiKeyConfigured=bool(config.get('aiKey')),youtubeKeyConfigured=bool(config.get('youtubeKey')),models=MODELS)
  return jsonify(result)
 @app.post('/api/world/admin/channels')
 def channels():
  require_admin();throttle('channels',10);body=payload();config=settings();action=body.get('action','add');id=body.get('id','')
  if action in ('delete','update'):
   channel=next((c for c in config.get('channels',[]) if c['id']==id),None)
   if not channel:abort(404)
   if action=='delete':config['channels']=[c for c in config['channels'] if c['id']!=id];config['videos']=[v for v in config.get('videos',[]) if v['channelId']!=id]
   else:
    profiles=body.get('profiles',channel['profiles'])
    if not isinstance(profiles,list) or not profiles or any(x not in PROFILES for x in profiles):abort(400)
    channel.update(title=str(body.get('title',channel['title']))[:120],profiles=profiles,enabled=body.get('enabled',True) is True)
  else:
   value=str(body.get('url','')).strip();match=re.fullmatch(r'(?:https://(?:www\.)?youtube\.com/(?:channel/)?)?(UC[a-zA-Z0-9_-]{22}|@[\w.\-\u00c0-\u1ef9]{1,100})/?',value)
   if not match:raise ValueError('Dùng link youtube.com/channel/UC… hoặc youtube.com/@tenkenh, không dùng link video.')
   identifier=match.group(1);data=youtube_api('channels',{'part':'snippet,contentDetails',('forHandle' if identifier.startswith('@') else 'id'):identifier},decrypt(config.get('youtubeKey')))
   if len(data.get('items',[]))!=1:raise ValueError('Không tìm thấy kênh công khai tương ứng.')
   c=data['items'][0];id=c['id']
   if not re.fullmatch(r'UC[a-zA-Z0-9_-]{22}',id):raise ValueError('ID kênh chưa hợp lệ.')
   if any(x['id']==id for x in config.get('channels',[])):raise ValueError('Kênh này đã có trong danh sách.')
   channel={'id':id,'title':c['snippet']['title'],'profiles':list(PROFILES),'enabled':True,'uploads':c['contentDetails']['relatedPlaylists']['uploads']}
   config.setdefault('channels',[]).append(channel)
  save('settings',config);return jsonify(ok=True,channels=config['channels'])
 @app.post('/api/world/admin/videos/sync')
 def sync_videos():
  require_admin();throttle('sync',4);config=settings();body=payload();channel=next((c for c in config.get('channels',[]) if c['id']==body.get('id')),None)
  if not channel:abort(404)
  key=decrypt(config.get('youtubeKey'));listed=youtube_api('playlistItems',{'part':'contentDetails','playlistId':channel['uploads'],'maxResults':50},key)
  ids=[x.get('contentDetails',{}).get('videoId') for x in listed.get('items',[])];ids=[v for v in ids if isinstance(v,str) and re.fullmatch(r'[a-zA-Z0-9_-]{11}',v)]
  data=youtube_api('videos',{'part':'snippet,status,contentDetails','id':','.join(ids)},key) if ids else {'items':[]}
  imported=[]
  for v in data.get('items',[]):
   snippet=v.get('snippet',{});status=v.get('status',{});details=v.get('contentDetails',{})
   if (v.get('id') not in ids or snippet.get('channelId')!=channel['id'] or not status.get('embeddable') or status.get('privacyStatus')!='public' or snippet.get('liveBroadcastContent')!='none' or details.get('contentRating',{}).get('ytRating')=='ytAgeRestricted'):continue
   imported.append({'id':v['id'],'title':snippet['title'][:200],'channelId':channel['id'],'channelTitle':channel['title']})
  config['videos']=[v for v in config.get('videos',[]) if v['channelId']!=channel['id']]+imported;save('settings',config)
  return jsonify(ok=True,count=len(imported))
 @app.get('/api/world/admin/art')
 def admin_art():
  require_admin();items={v:k.replace('-',' ') for k,v in ART.items() if v}
  if drive_store.connected():
   topics=drive_store.store().document('resource/topics.json').get('topics',[])
   for topic in topics:
    filename=topic.get('file','')
    if not re.fullmatch(r'topic-[a-z0-9-]+\.json',filename):continue
    for item in drive_store.store().document('resource/'+filename).get('items',[]):
     path=item.get('image','')
     if drive_store.valid_path(path) and path.startswith('images/') and item.get('enabled',True):items[path]=str(item.get('viName',path))[:150]
  return jsonify(art=[{'label':name,'path':path} for path,name in items.items()])
 @app.get('/api/world/admin/drafts')
 def drafts():require_admin();return jsonify(drafts=document('drafts',[]),published=document('published',{'stories':[],'activities':[]}))
 @app.post('/api/world/admin/generate')
 def generate():
  require_admin();throttle('ai',3);body=payload();kind=body.get('kind');profile=body.get('profile');topic=body.get('topic','')
  if kind not in ['story','lesson'] or canonical(profile) not in PROFILES or not isinstance(topic,str) or not 3<=len(topic)<=200:abort(400)
  draft=ai_generate(kind,profile,topic);draft.update(draftId=secrets.token_hex(12),type=kind,reviewed=False)
  drafts=document('drafts',[]);drafts.append(draft);save('drafts',drafts[-50:]);return jsonify(draft=draft)
 @app.post('/api/world/admin/drafts')
 def edit_draft():
  require_admin();body=payload();kind=body.get('kind');profile=body.get('profile')
  if kind not in ['story','lesson'] or canonical(profile) not in PROFILES:abort(400)
  clean=validate_draft(kind,body.get('content'),profile);drafts=document('drafts',[]);existing=next((d for d in drafts if d['draftId']==body.get('draftId')),None)
  if body.get('publishedId'):
   old=next((item for items in document('published',{'stories':[],'activities':[]}).values() for item in items if item['id']==body['publishedId']),None)
   if not old:abort(404)
   clean['id']=old['id']
  clean.update(draftId=existing['draftId'] if existing else secrets.token_hex(12),type=kind,reviewed=False)
  if existing:
   clean['id']=existing['id']
   drafts=[clean if d['draftId']==existing['draftId'] else d for d in drafts]
  else:drafts.append(clean)
  save('drafts',drafts[-50:]);return jsonify(draft=clean)
 @app.post('/api/world/admin/publish')
 def publish():
  require_admin();body=payload()
  if body.get('reviewed') is not True:raise ValueError('Cần xác nhận đã đọc và kiểm tra nội dung cho đúng lứa tuổi.')
  drafts=document('drafts',[]);draft=next((d for d in drafts if d['draftId']==body.get('draftId')),None)
  if not draft:abort(404)
  published=document('published',{'stories':[],'activities':[]});group='stories' if draft['type']=='story' else 'activities';item={k:v for k,v in draft.items() if k not in ['draftId','type','reviewed']}
  published[group]=[d for d in published[group] if d['id']!=item['id']]+[item]
  if not drive_store.connected():raise ValueError('Cần kết nối Drive trước khi xuất bản nội dung.')
  drive_store.store().write_document('world/published.json',published)
  save('published',published);return jsonify(ok=True)
 @app.post('/api/world/admin/unpublish')
 def unpublish():
  require_admin();body=payload();published=document('published',{'stories':[],'activities':[]})
  for key in ['stories','activities']:published[key]=[x for x in published[key] if x['id']!=body.get('id')]
  if not drive_store.connected():raise ValueError('Cần kết nối Drive trước khi gỡ nội dung.')
  drive_store.store().write_document('world/published.json',published);save('published',published);return jsonify(ok=True)
 @app.errorhandler(ValueError)
 def bad_input(error):return jsonify(ok=False,message=str(error) if request.path.startswith('/api/world/') else 'Dữ liệu chưa hợp lệ'),400
 @app.after_request
 def world_headers(response):
  if request.path.startswith(('/api/world','/world','/parents')):
   response.headers['Cache-Control']='no-store'
   response.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
  return response
