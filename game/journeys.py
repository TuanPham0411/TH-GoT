"""Server-owned chapter steps, separate for each adult account and learning stage."""
from datetime import datetime, timezone
import json
from flask import abort,jsonify,request
from auth import connect,user,valid_csrf
from learning_profiles import canonical
from world_content import JOURNEYS


def resolve(profile, chapter_id, step_id):
 profile=canonical(profile)
 chapter=next((c for c in JOURNEYS.get(profile,{}).get('chapters',[]) if c['id']==chapter_id),None)
 step=next((s for s in chapter['steps'] if s['id']==step_id),None) if chapter else None
 if not step:abort(404)
 return profile,chapter,step


def state(owner,profile,db=None):
 profile=canonical(profile)
 if not owner:return {'profile':profile,'completed':[]}
 if db is None:
  with connect() as db:return state(owner,profile,db)
 rows=db.execute('SELECT chapter,step FROM journey_progress WHERE owner=? AND profile=?',(owner,profile)).fetchall()
 return {'profile':profile,'completed':[r['chapter']+'/'+r['step'] for r in rows]}


def validate_step(owner,profile,chapter_id,step_id,activity=None,db=None):
 profile,chapter,step=resolve(profile,chapter_id,step_id)
 if activity is not None and (step['kind']!='activity' or step['activity']!=activity):abort(400)
 completed=state(owner,profile,db)['completed']
 for previous in chapter['steps'][:chapter['steps'].index(step)]:
  if chapter_id+'/'+previous['id'] not in completed:abort(409,description='Hãy hoàn thành bước trước trong chương này.')
 return profile,chapter,step


def record(db,owner,profile,chapter_id,step_id):
 db.execute('INSERT OR IGNORE INTO journey_progress(owner,profile,chapter,step,completed_at) VALUES(?,?,?,?,?)',(owner,canonical(profile),chapter_id,step_id,datetime.now(timezone.utc).isoformat()))


def register(app,verified_session):
 with app.app_context(),connect() as db:
  db.execute('CREATE TABLE IF NOT EXISTS journey_progress(owner INTEGER NOT NULL,profile TEXT NOT NULL,chapter TEXT NOT NULL,step TEXT NOT NULL,completed_at TEXT NOT NULL,PRIMARY KEY(owner,profile,chapter,step))')
  columns={r['name'] for r in db.execute('PRAGMA table_info(world_rounds)').fetchall()}
  for name in ('journey_chapter','journey_step'):
   if name not in columns:db.execute('ALTER TABLE world_rounds ADD COLUMN '+name+' TEXT')
 @app.get('/api/world/journey')
 def journey_progress():
  profile=canonical(request.args.get('profile','kindergarten-4'))
  if profile not in JOURNEYS:abort(400)
  return jsonify(state(user()['id'] if user() else None,profile))
 @app.post('/api/world/journey/reflect')
 def reflect():
  if not valid_csrf():abort(403)
  body=request.get_json(silent=True)
  if not isinstance(body,dict) or body.get('reflected') is not True:abort(400)
  session=verified_session(body.get('session'))
  profile=json.loads(session['config_json'])['profile']
  with connect() as db:
   db.execute('BEGIN IMMEDIATE')
   profile,chapter,step=validate_step(user()['id'],profile,body.get('chapter'),body.get('step'),db=db)
   if step['kind']!='reflection':abort(400)
   record(db,user()['id'],profile,chapter['id'],step['id'])
   return jsonify(state(user()['id'],profile,db))

 @app.post('/api/world/session/end')
 def end_learning_session():
  if not valid_csrf():abort(403)
  body=request.get_json(silent=True)
  if not isinstance(body,dict):abort(400)
  active=verified_session(body.get('session'))
  with connect() as db:db.execute('UPDATE game_sessions SET expires_at=? WHERE token=? AND user_id=?',(datetime.now(timezone.utc).isoformat(),active['token'],user()['id']))
  return jsonify(ended=True)
