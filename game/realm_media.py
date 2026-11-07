"""Pinned first-party art from Drive, with bounded disposable display copies."""
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import threading
from flask import abort, current_app, send_file
from PIL import Image
import drive_store

MANIFEST = json.loads(Path(__file__).with_name('realm-assets.json').read_text())
_LOCK = threading.Lock()
LIMIT = 96 * 1024 * 1024


def asset_response(name):
    asset = MANIFEST.get(name)
    if not asset:
        abort(404)
    source = drive_store.store()
    # Lookup on every request uses the shared, expiring Drive metadata index.
    # A deleted or revoked source must not become permanently public via a cache.
    source.view_cache.lookup(asset['path'])
    root = Path(os.environ.get('DATA_DIR', str(Path(__file__).resolve().parents[1] / 'data'))) / 'realm-media'
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    video = asset['mime'] == 'video/mp4'
    target = root / (asset['sha256'] + ('.mp4' if video else '.webp'))
    with _LOCK:
        if not target.exists():
            body, mime = source.read(asset['path'])
            if len(body) != asset['bytes'] or hashlib.sha256(body).hexdigest() != asset['sha256']:
                abort(503, description='Bản gốc minh họa chưa khớp phiên bản.')
            if not video:
                with Image.open(io.BytesIO(body)) as image:
                    if image.width * image.height > 16_000_000:
                        abort(413)
                    image.thumbnail((1920, 1920))
                    output = io.BytesIO()
                    image.save(output, format='WEBP', quality=87, method=4)
                    body = output.getvalue()
            fd, temp = tempfile.mkstemp(dir=root, prefix='.writing-')
            try:
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(body)
                os.replace(temp, target)
            finally:
                if os.path.exists(temp):
                    os.unlink(temp)
            files = sorted(root.glob('*.*'), key=lambda p: p.stat().st_mtime)
            size = sum(p.stat().st_size for p in files)
            for path in files:
                if size <= LIMIT:
                    break
                if path != target:
                    size -= path.stat().st_size
                    path.unlink(missing_ok=True)
        os.utime(target, None)
    response = send_file(target, mimetype='video/mp4' if video else 'image/webp', conditional=True, etag=asset['sha256'])
    response.headers['Cache-Control'] = 'private, no-cache, max-age=0, must-revalidate'
    response.headers['CDN-Cache-Control'] = 'no-store'
    return response


def register(app):
    app.add_url_rule('/world-assets/<name>', 'realm_asset', asset_response)
