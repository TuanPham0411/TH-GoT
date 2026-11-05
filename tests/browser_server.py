import sys,json,os,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'game')]
from test_auth import ApplicationTest
case=ApplicationTest();case.setUp();case.google_login()
with case.client.session_transaction() as session:csrf=session['csrf']
response=case.client.post('/api/sessions',json={'csrf':csrf,'duration_minutes':60,'profile':'preschool'}).json
cookie=case.client.get_cookie(case.app.config['SESSION_COOKIE_NAME'])
Path('/tmp/got-browser-session.json').write_text(json.dumps({'launch':response['launch_url'],'cookie':{'name':cookie.key,'value':cookie.value,'domain':'127.0.0.1','path':'/'}}))
case.app.config['SESSION_COOKIE_SECURE']=False
case.app.config['TEMPLATES_AUTO_RELOAD']=True
case.app.run(host='127.0.0.1',port=5099,use_reloader=False)
