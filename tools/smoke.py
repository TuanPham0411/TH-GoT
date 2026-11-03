#!/usr/bin/env python3
import argparse,io,json,wave
from urllib.request import urlopen
from urllib.error import HTTPError
p=argparse.ArgumentParser();p.add_argument('--origin',default='http://127.0.0.1:5082');a=p.parse_args()
def get(path):
    with urlopen(a.origin.rstrip('/')+path,timeout=30) as r:
        assert r.status==200;return r.read()
assert json.loads(get('/healthz'))['ok']
assert b'Google' in get('/')
assert b'session-clock.js' in get('/play')
data=json.loads(get('/api/bootstrap'));assert len(data['games'])==18 and len(data['topics'])==10
image=json.loads(get('/api/topic/'+data['topics'][0]['id']))['items'][0]['image']
assert len(get('/resource/'+image))>1000
assert get('/thumb/'+image)[8:12]==b'WEBP'
for lang in ('vi','en'):
    with wave.open(io.BytesIO(get('/api/tts?text=Xin%20chao&lang='+lang))) as audio:assert audio.getnframes()>0
try:
    get('/api/sessions/'+'x'*32);raise AssertionError('Unknown session accepted')
except HTTPError as e:assert e.code==404
print('PASS: standalone introduction/play pages, 18 games, 10 topics, image/thumbnail, VI/EN WAV, local sessions API')
