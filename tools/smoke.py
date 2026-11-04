#!/usr/bin/env python3
"""Check web independently of Drive; --media requires a real initialized connection."""
import argparse,io,json,wave
from urllib.request import urlopen
from urllib.error import HTTPError
p=argparse.ArgumentParser();p.add_argument('--origin',default='http://127.0.0.1:5082');p.add_argument('--media',action='store_true');a=p.parse_args()
def get(path):
    with urlopen(a.origin.rstrip('/')+path,timeout=60) as r:
        assert r.status==200
        if path.startswith(('/resource/images/','/static/images/','/thumb/')):
            assert r.headers['Cache-Control']=='no-store'
        return r.read()
assert json.loads(get('/healthz'))['ok']
assert b'Google' in get('/')
assert b'session-clock.js' in get('/play')
data=json.loads(get('/api/bootstrap'));assert len(data['games'])==18 and len(data['topics'])==10
for lang in ('vi','en'):
    with wave.open(io.BytesIO(get('/api/tts?text=Xin%20chao&lang='+lang))) as audio:assert audio.getnframes()>0
try:
    get('/api/sessions/'+'x'*32);raise AssertionError('Unknown session accepted')
except HTTPError as e:assert e.code==404
print('PASS: web/database, introduction/play pages, 18 games, 10 topics, VI/EN WAV, local sessions API')
if a.media:
    assert json.loads(get('/readyz'))['ok']
    image=json.loads(get('/api/topic/'+data['topics'][0]['id']))['items'][0]['image']
    assert len(get('/resource/'+image))>1000
    assert get('/thumb/'+image)[8:12]==b'WEBP'
    print('PASS: real Drive readiness, image and memory-only thumbnail with no-store headers')
else:
    print('Drive media not tested; run --media after connecting and initializing Drive.')
