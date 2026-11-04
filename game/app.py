from flask import Flask, Request, render_template, jsonify, send_from_directory, send_file, abort, request
from pathlib import Path
import json
import io
import subprocess
import hashlib
import gzip
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from flask import session, redirect, url_for
from auth import configure, connect, user, valid_csrf
from werkzeug.http import parse_accept_header
from werkzeug.datastructures import Accept
from PIL import Image
import drive_store

app = Flask(__name__,root_path=str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parent
RESOURCE = ROOT / "resource"
class MemoryRequest(Request):
    def _get_file_stream(self, total_content_length, content_type, filename=None, content_length=None):
        return io.BytesIO()

app.request_class = MemoryRequest
configure(app, os.environ.get('DATA_DIR', str(ROOT.parent / 'data')))
app.config['MAX_CONTENT_LENGTH'] = drive_store.MAX_IMAGE + 1024 * 1024
app.config['RESOURCE_ROOT'] = RESOURCE
app.config['DRIVE_ARCHIVE_LOCK'] = Path(os.environ.get('DRIVE_ARCHIVE_LOCK', str(ROOT.parent / 'assets.lock.json' if (ROOT.parent / 'assets.lock.json').is_file() else ROOT / 'assets.lock.json')))
drive_store.register(app)
with app.app_context(), connect() as connection:
    connection.execute('CREATE TABLE IF NOT EXISTS game_sessions(token TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),config_json TEXT NOT NULL,created_at TEXT NOT NULL,expires_at TEXT NOT NULL)')

def load_json(path, default=None):
    if path.is_relative_to(RESOURCE) and drive_store.connected():
        return drive_store.store().document('resource/' + path.relative_to(RESOURCE).as_posix())
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {} if default is None else default

@app.get("/")
def index():
    return render_template("landing.html", game_library=load_json(RESOURCE / "games.json").get("games", []))

@app.get('/play')
def play():
    return render_template('index.html')

@app.get('/account')
def account():
    if not user():
        return redirect(url_for('login', next='/account'))
    with connect() as connection:
        sessions = connection.execute('SELECT created_at,expires_at FROM game_sessions WHERE user_id=? ORDER BY created_at DESC LIMIT 20',(user()['id'],)).fetchall()
    return render_template('account.html', sessions=sessions)

@app.post('/api/sessions')
def create_session():
    if not user():
        return jsonify(ok=False,message='Vui lòng đăng nhập Google để mở phiên'),401
    payload=request.get_json(silent=True)
    if not isinstance(payload,dict) or not valid_csrf(payload.get('csrf')):
        return jsonify(ok=False,message='Phiên làm việc không hợp lệ, vui lòng tải lại trang'),400
    minutes=payload.get('duration_minutes')
    if type(minutes) is not int or minutes not in (10,20,30,40,50,60):
        return jsonify(ok=False,message='Chọn thời lượng 10, 20, 30, 40, 50 hoặc 60 phút'),400
    games=load_json(RESOURCE/'games.json',{}).get('games',[])
    games=[{'id':game['id'],'name':game['name'].get('vi',game['id'])} for game in games if game.get('enabled',True)]
    config={'version':2,'games':games,'duration_minutes':minutes,'total_duration_minutes':minutes}
    token=secrets.token_urlsafe(32)
    created=datetime.now(timezone.utc).replace(microsecond=0)
    expires=created+timedelta(minutes=minutes)
    with connect() as connection:
        connection.execute('INSERT INTO game_sessions VALUES(?,?,?,?,?)',(token,user()['id'],json.dumps(config,ensure_ascii=False),created.isoformat(),expires.isoformat()))
    return jsonify(ok=True,launch_url=url_for('play',session=token),expires_at=expires.isoformat())

@app.get('/api/sessions/<token>')
def game_session(token):
    if not 32<=len(token)<=96:
        return jsonify(ok=False,message='Phiên không tồn tại'),404
    with connect() as connection:
        row=connection.execute('SELECT * FROM game_sessions WHERE token=?',(token,)).fetchone()
    if not row:
        return jsonify(ok=False,message='Phiên không tồn tại'),404
    if datetime.fromisoformat(row['expires_at'])<=datetime.now(timezone.utc):
        return jsonify(ok=False,message='Phiên đã kết thúc'),410
    response=jsonify(ok=True,status='started',config=json.loads(row['config_json']),created_at=row['created_at'],expires_at=row['expires_at'],server_now=datetime.now(timezone.utc).isoformat(timespec='milliseconds'))
    response.headers['Cache-Control']='no-store'
    return response

@app.get("/resource/<path:name>")
def resource_file(name):
    if not drive_store.valid_path(name):
        abort(404)
    if name.endswith('.json'):
        path = RESOURCE / name
        if not path.is_file():
            abort(404)
        return jsonify(load_json(path))
    return send_from_directory(RESOURCE, name)

def drive_image(path, thumbnail=False):
    if not drive_store.valid_path(path):
        abort(404)
    body, mime = drive_store.store().read(path)
    if not mime.startswith('image/'):
        abort(415)
    if thumbnail and mime != 'image/svg+xml':
        try:
            with Image.open(io.BytesIO(body)) as image:
                image.thumbnail((480, 320), Image.Resampling.LANCZOS)
                if image.mode not in ('RGB', 'RGBA'):
                    image = image.convert('RGB')
                output = io.BytesIO()
                image.save(output, 'WEBP', quality=80, method=4)
                body, mime = output.getvalue(), 'image/webp'
        except (OSError, ValueError, Image.DecompressionBombError):
            abort(415)
    response = send_file(io.BytesIO(body), mimetype=mime, max_age=0, etag=False, conditional=False)
    response.headers['Cache-Control'] = 'no-store'
    if mime == 'image/svg+xml':
        response.headers['Content-Security-Policy'] = "sandbox; default-src 'none'; style-src 'unsafe-inline'"
    return response

@app.get('/resource/images/<path:name>')
def resource_image(name):
    return drive_image('resource/images/' + name)

@app.get('/static/images/<path:name>')
def static_image(name):
    return drive_image('static/images/' + name)

@app.get('/thumb/<path:name>')
def resource_thumbnail(name):
    if not name.startswith('images/'):
        abort(404)
    return drive_image('resource/' + name, thumbnail=True)

@app.get("/api/bootstrap")
def bootstrap():
    return jsonify({
        "manifest": load_json(RESOURCE / "manifest.json", {}),
        "topics": load_json(RESOURCE / "topics.json", {}).get("topics", []),
        "games": load_json(RESOURCE / "games.json", {}).get("games", []),
    })

@app.get("/api/topic/<topic_id>")
def topic(topic_id):
    topics = load_json(RESOURCE / "topics.json", {}).get("topics", [])
    entry = next((x for x in topics if x.get("id") == topic_id), None)
    if not entry:
        abort(404)
    return jsonify(load_json(RESOURCE / entry["file"], {}))

@app.get("/api/game-topic/<topic_id>")
def game_topic(topic_id):
    topics = load_json(RESOURCE / "topics.json", {}).get("topics", [])
    entry = next((x for x in topics if x.get("id") == topic_id), None)
    if not entry:
        abort(404)
    data = load_json(RESOURCE / entry["file"], {})
    fields = ("id", "viName", "enName", "image", "enabled")
    items = [{key: item.get(key) for key in fields if key in item} for item in data.get("items", [])]
    return jsonify({"id": data.get("id", topic_id), "items": items})
@app.get("/api/game/<game_id>")
def game(game_id):
    games = load_json(RESOURCE / "games.json", {}).get("games", [])
    entry = next((x for x in games if x.get("id") == game_id), None)
    if not entry or not entry.get("configFile"):
        abort(404)
    return jsonify(load_json(RESOURCE / entry["configFile"], {}))

@app.get("/api/tts")
def text_to_speech():
    text = " ".join(request.args.get("text", "").split())[:500]
    lang = request.args.get("lang", "vi").lower()
    if not text:
        abort(400)
    voice = "en-us" if lang.startswith("en") else "vi"
    speed = "145" if voice == "en-us" else "155"
    try:
        result = subprocess.run(
            ["espeak-ng", "-v", voice, "-s", speed, "--stdout", "--", text],
            check=True, capture_output=True, timeout=10,
        )
    except (subprocess.SubprocessError, OSError):
        abort(503)
    response = send_file(io.BytesIO(result.stdout), mimetype="audio/wav", download_name="speech.wav", max_age=86400)
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response

@app.get("/api/status")
def status():
    manifest = load_json(RESOURCE / "manifest.json", {})
    return jsonify({"online": True, "schema": manifest.get("schemaVersion"), "counts": manifest.get("counts", {})})

@app.get("/healthz")
def health():
    required = ("manifest.json", "topics.json", "games.json")
    ready = all((RESOURCE / name).is_file() for name in required)
    try:
        with connect() as connection:
            connection.execute('SELECT 1 FROM users LIMIT 1')
    except sqlite3.Error:
        ready=False
    return jsonify({"ok": bool(ready), "media_connected": bool(drive_store.connected())}), 200 if ready else 503

@app.get('/readyz')
def media_ready():
    from drive_migration import MARKER
    marker = drive_store.store().document(MARKER)
    drive_store.store().document('resource/manifest.json')
    return jsonify(ok=marker.get('schema') == 1), 200 if marker.get('schema') == 1 else 503

@app.after_request
def cache_and_security_headers(response):
    content_type = response.headers.get("Content-Type", "").lower()
    compressible = content_type.startswith("text/") or "json" in content_type or "javascript" in content_type
    if compressible:
        response.vary.add("Accept-Encoding")
    encodings = parse_accept_header(request.headers.get("Accept-Encoding", ""), Accept)
    if (request.method == "GET" and response.status_code == 200 and not request.headers.get("Range") and not response.headers.get("Content-Encoding") and encodings.quality("gzip") > 0):
        content_type = response.headers.get("Content-Type", "").lower()
        if content_type.startswith("text/") or "json" in content_type or "javascript" in content_type:
            response.direct_passthrough = False
            data = response.get_data()
            if len(data) > 1024:
                compressed = gzip.compress(data, compresslevel=6)
                if len(compressed) < len(data):
                    response.set_data(compressed)
                    response.headers["Content-Encoding"] = "gzip"
                    response.headers["Content-Length"] = str(len(compressed))
                    # The ETag identifies bytes, so vary it for the encoded body.
                    response.set_etag(hashlib.sha256(compressed).hexdigest())
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "same-origin"
    request_path = request.path
    if request_path.startswith(("/api/admin/", "/admin/")):
        response.headers["Cache-Control"] = "no-store"
        return response
    if response.status_code == 200 and request_path.startswith(('/resource/images/', '/static/images/', '/thumb/')):
        response.headers['Cache-Control'] = 'no-store'
    elif response.status_code == 200 and request_path.startswith("/resource/"):
        response.headers["Cache-Control"] = "no-store"
    elif response.status_code == 200 and request_path.startswith("/static/"):
        response.headers["Cache-Control"] = "public, max-age=3600, must-revalidate"
    elif response.status_code >= 400:
        response.headers["Cache-Control"] = "no-store"
    elif "Cache-Control" not in response.headers:
        response.headers["Cache-Control"] = "no-cache"
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
