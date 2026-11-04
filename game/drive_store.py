"""Drive-only media and resource documents. Image bytes stay in request memory."""
import base64
import hashlib
import io
import json
import os
from pathlib import PurePosixPath
import secrets
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

from cryptography.fernet import Fernet, InvalidToken
from flask import (Blueprint, abort, current_app, jsonify, redirect, render_template,
                   request, session, url_for)
from PIL import Image, UnidentifiedImageError
from auth import connect, user, valid_csrf, _json_request

SCOPE = 'https://www.googleapis.com/auth/drive'
DEFAULT_FOLDER = '1hueCpVN5ez5aFRGAxbjc2hjK-Yaw3rA0'
MAX_IMAGE = 32 * 1024 * 1024
MUTATIONS = threading.RLock()


class DriveUnavailable(Exception):
    pass


class DriveMissing(Exception):
    pass


def admin():
    account = user()
    emails = {e.strip().casefold() for e in os.environ.get('ADMIN_EMAILS', '').split(',') if e.strip()}
    return bool(account and account['email'].casefold() in emails)


def require_admin():
    if not user():
        abort(401)
    if not admin():
        abort(403)


def valid_path(path):
    return (isinstance(path, str) and len(path) < 512 and '\\' not in path
            and not PurePosixPath(path).is_absolute()
            and all(p not in ('', '.', '..') for p in path.split('/')))


def cipher():
    key = hashlib.sha256(str(current_app.secret_key).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


class DriveStore:
    def __init__(self, token_provider, folder=None):
        self.token_provider = token_provider
        self.folder = folder or os.environ.get('DRIVE_FOLDER_ID', DEFAULT_FOLDER)
        if not self.folder or not all(c.isalnum() or c in '-_' for c in self.folder):
            raise DriveUnavailable('Invalid Drive folder configuration')

    def call(self, method, path, data=None, mime=None, upload=False, **query):
        base = 'https://www.googleapis.com/' + ('upload/' if upload else '') + 'drive/v3/'
        query['supportsAllDrives'] = 'true'
        headers = {'Authorization': 'Bearer ' + self.token_provider()}
        if mime:
            headers['Content-Type'] = mime
        req = Request(base + path + '?' + urlencode(query), data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=45) as response:
                body = response.read(MAX_IMAGE + 1)
                if len(body) > MAX_IMAGE:
                    raise DriveUnavailable('Drive response exceeds request memory limit')
                return body
        except HTTPError as error:
            if error.code == 404:
                raise DriveMissing() from None
            raise DriveUnavailable('Drive request failed; check permission or quota') from None
        except (OSError, URLError):
            raise DriveUnavailable('Drive connection unavailable') from None

    def lookup(self, path):
        if not valid_path(path):
            raise DriveMissing()
        fingerprint = hashlib.sha256(path.encode()).hexdigest()
        q = ("'" + self.folder + "' in parents and trashed = false and "
             "appProperties has { key='gotPathHash' and value='" + fingerprint + "' }")
        data = json.loads(self.call('GET', 'files', q=q, pageSize=2,
                                   fields='files(id,mimeType,description,version),nextPageToken'))
        found = data.get('files', [])
        if len(found) > 1 or data.get('nextPageToken'):
            raise DriveUnavailable('Duplicate Drive resource path')
        if not found:
            raise DriveMissing()
        return found[0]

    def read(self, path):
        entry = self.lookup(path)
        return self.call('GET', 'files/' + quote(entry['id'], safe=''), alt='media'), entry.get('mimeType', 'application/octet-stream')

    def document(self, path):
        body, _ = self.read(path)
        try:
            value = json.loads(body)
            if not isinstance(value, dict):
                raise ValueError()
            return value
        except (ValueError, UnicodeError):
            raise DriveUnavailable('Invalid Drive resource document') from None

    def write(self, path, data, mime):
        if not valid_path(path) or len(data) > MAX_IMAGE:
            raise ValueError('Invalid resource path or size')
        try:
            existing = self.lookup(path)
        except DriveMissing:
            existing = None
        if existing:
            return json.loads(self.call('PATCH', 'files/' + quote(existing['id'], safe=''), data, mime,
                                        upload=True, uploadType='media', fields='id'))['id']
        metadata = {'name': PurePosixPath(path).name, 'parents': [self.folder], 'description': path,
                    'appProperties': {'gotPathHash': hashlib.sha256(path.encode()).hexdigest()}}
        boundary = 'got_' + secrets.token_hex(24)
        body = (f'--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n'.encode()
                + json.dumps(metadata).encode() + f'\r\n--{boundary}\r\nContent-Type: {mime}\r\n\r\n'.encode()
                + data + f'\r\n--{boundary}--\r\n'.encode())
        return json.loads(self.call('POST', 'files', body, 'multipart/related; boundary=' + boundary,
                                    upload=True, uploadType='multipart', fields='id'))['id']

    def write_document(self, path, document):
        return self.write(path, json.dumps(document, ensure_ascii=False).encode(), 'application/json')

    def trash(self, path):
        entry = self.lookup(path)
        self.call('PATCH', 'files/' + quote(entry['id'], safe=''), b'{"trashed":true}', 'application/json')

    def referenced_elsewhere(self, image, excluded_path):
        def contains(value):
            if isinstance(value, str):
                return value in (image, 'resource/' + image, '/resource/' + image)
            if isinstance(value, dict):
                return any(contains(v) for v in value.values())
            if isinstance(value, list):
                return any(contains(v) for v in value)
            return False
        query = "'" + self.folder + "' in parents and trashed=false and mimeType='application/json'"
        page = ''
        while True:
            result = json.loads(self.call('GET', 'files', q=query, pageSize=1000, pageToken=page,
                                           fields='files(id,description),nextPageToken'))
            for entry in result.get('files', []):
                path = entry.get('description', '')
                if path.startswith('resource/') and valid_path(path) and path != excluded_path:
                    if contains(self.document(path)):
                        return True
            page = result.get('nextPageToken')
            if not page:
                return False

    def check_folder(self):
        result = json.loads(self.call('GET', 'files/' + quote(self.folder, safe=''),
                                      fields='id,mimeType,capabilities(canAddChildren)'))
        if result.get('mimeType') != 'application/vnd.google-apps.folder' or not result.get('capabilities', {}).get('canAddChildren'):
            raise DriveUnavailable('The connected account cannot edit the configured Drive folder')


def store():
    return current_app.extensions['drive_store']


def connected():
    with connect() as connection:
        row = connection.execute('SELECT owner FROM drive_connection WHERE id=1').fetchone()
    return row['owner'] if row else None


def register(app):
    token_lock = threading.Lock()
    access = {'token': None, 'expires': 0}
    with app.app_context(), connect() as connection:
        connection.execute('CREATE TABLE IF NOT EXISTS drive_connection(id INTEGER PRIMARY KEY CHECK(id=1),owner TEXT NOT NULL,refresh_encrypted TEXT NOT NULL)')

    def access_token():
        with token_lock:
            if access['token'] and access['expires'] > time.time() + 60:
                return access['token']
            with connect() as connection:
                row = connection.execute('SELECT refresh_encrypted FROM drive_connection WHERE id=1').fetchone()
            if not row:
                raise DriveUnavailable('Connect a Drive editor account in resource administration')
            try:
                refresh = cipher().decrypt(row['refresh_encrypted'].encode()).decode()
                result = _json_request('https://oauth2.googleapis.com/token', urlencode({
                    'client_id': os.environ.get('GOOGLE_CLIENT_ID', ''),
                    'client_secret': os.environ.get('GOOGLE_CLIENT_SECRET', ''),
                    'refresh_token': refresh, 'grant_type': 'refresh_token'}).encode())
                access.update(token=result['access_token'], expires=time.time() + int(result.get('expires_in', 3600)))
            except (OSError, ValueError, KeyError, InvalidToken):
                raise DriveUnavailable('Reconnect the Drive account') from None
            return access['token']

    app.extensions['drive_store'] = DriveStore(access_token)
    bp = Blueprint('drive', __name__)
    migration = {'running': False, 'stage': 'idle', 'done': 0, 'total': 0}
    migration_lock = threading.Lock()

    @app.errorhandler(DriveUnavailable)
    def unavailable(error):
        return jsonify(ok=False, message=str(error)), 503

    @app.errorhandler(DriveMissing)
    def missing(error):
        return jsonify(ok=False, message='Tài nguyên không tồn tại trên Drive'), 404

    @app.context_processor
    def admin_context():
        return {'is_resource_admin': admin()}

    @bp.get('/admin/resources')
    def resources():
        require_admin()
        return render_template('resources.html', drive_owner=connected(), folder_id=store().folder)

    @bp.post('/admin/drive/connect')
    def connect_drive():
        require_admin()
        if not valid_csrf():
            abort(400)
        if not os.environ.get('GOOGLE_CLIENT_ID') or not os.environ.get('GOOGLE_CLIENT_SECRET'):
            abort(503)
        callback = ((current_app.config['PUBLIC_URL'] or request.url_root.rstrip('/'))
                    + '/admin/drive/callback')
        verifier = secrets.token_urlsafe(48)
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        session['drive_oauth'] = {'state': state, 'nonce': nonce, 'verifier': verifier,
                                 'created': int(time.time()), 'callback': callback, 'uid': user()['id']}
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        return redirect('https://accounts.google.com/o/oauth2/v2/auth?' + urlencode({
            'client_id': os.environ['GOOGLE_CLIENT_ID'], 'redirect_uri': callback,
            'response_type': 'code', 'scope': 'openid email profile ' + SCOPE,
            'access_type': 'offline', 'prompt': 'consent', 'state': state, 'nonce': nonce,
            'code_challenge': challenge, 'code_challenge_method': 'S256', 'login_hint': user()['email']}))

    @bp.get('/admin/drive/callback')
    def callback():
        require_admin()
        attempt = session.pop('drive_oauth', None)
        supplied = request.args.get('state', '')
        if (not attempt or not supplied or not secrets.compare_digest(supplied, attempt['state'])
                or not 0 <= time.time() - attempt['created'] <= 600 or attempt['uid'] != user()['id']):
            abort(400)
        if not request.args.get('code'):
            abort(400)
        try:
            result = _json_request('https://oauth2.googleapis.com/token', urlencode({
                'code': request.args['code'], 'client_id': os.environ['GOOGLE_CLIENT_ID'],
                'client_secret': os.environ['GOOGLE_CLIENT_SECRET'], 'redirect_uri': attempt['callback'],
                'grant_type': 'authorization_code', 'code_verifier': attempt['verifier']}).encode())
            identity = _json_request('https://oauth2.googleapis.com/tokeninfo?' + urlencode({'id_token': result['id_token']}))
            with connect() as connection:
                account = connection.execute('SELECT google_sub FROM users WHERE id=?', (user()['id'],)).fetchone()
            if (identity.get('aud') != os.environ['GOOGLE_CLIENT_ID']
                    or identity.get('iss') not in ('accounts.google.com', 'https://accounts.google.com')
                    or int(identity.get('exp', 0)) <= time.time()
                    or str(identity.get('email_verified')).lower() != 'true'
                    or identity.get('sub') != account['google_sub']
                    or not secrets.compare_digest(str(identity.get('nonce', '')), attempt['nonce'])
                    or SCOPE not in result.get('scope', '').split() or not result.get('refresh_token')):
                abort(403)
            candidate = DriveStore(lambda: result['access_token'])
            candidate.check_folder()
            encrypted = cipher().encrypt(result['refresh_token'].encode()).decode()
            with connect() as connection:
                connection.execute('INSERT INTO drive_connection VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET owner=excluded.owner,refresh_encrypted=excluded.refresh_encrypted', (user()['email'], encrypted))
            with token_lock:
                access.update(token=result['access_token'], expires=time.time() + int(result.get('expires_in', 3600)))
        except (OSError, ValueError, KeyError):
            raise DriveUnavailable('Không thể kết nối Drive; hãy cấp lại quyền') from None
        return redirect(url_for('drive.resources'))

    @bp.get('/api/admin/topics')
    def admin_topics():
        require_admin()
        return jsonify(json.loads((current_app.config['RESOURCE_ROOT'] / 'topics.json').read_text()))

    @bp.route('/api/admin/drive/migration', methods=['GET', 'POST'])
    def migration_job():
        require_admin()
        if request.method == 'GET':
            with migration_lock:
                return jsonify(migration)
        if not valid_csrf():
            abort(400)
        if not connected():
            raise DriveUnavailable('Kết nối Drive trước khi chuyển tài nguyên')
        application = current_app._get_current_object()
        with migration_lock:
            if migration['running']:
                return jsonify(migration), 202
            migration.update(running=True, stage='starting', done=0, total=0, message='')
        def update(**values):
            with migration_lock:
                migration.update(values)
        def worker():
            with application.app_context():
                try:
                    from drive_migration import migrate
                    with MUTATIONS:
                        migrate(store(), application.config['RESOURCE_ROOT'],
                                application.config['DRIVE_ARCHIVE_LOCK'], progress=update)
                except Exception:
                    # Never expose OAuth tokens, remote bodies or URLs in task errors.
                    update(stage='failed', message='Không thể chuyển tài nguyên. Kiểm tra quyền Drive, hạn mức và checksum; chạy lại để tiếp tục. Các tệp đã có không bị ghi đè.')
                finally:
                    update(running=False)
        threading.Thread(target=worker, name='drive-migration', daemon=True).start()
        return jsonify(ok=True), 202

    @bp.get('/api/admin/resources/<topic_id>')
    def list_items(topic_id):
        require_admin()
        path = topic_path(topic_id)
        return jsonify(store().document(path))

    def topic_path(topic_id):
        root = current_app.config['RESOURCE_ROOT']
        topics = json.loads((root / 'topics.json').read_text())['topics']
        topic = next((t for t in topics if t['id'] == topic_id), None)
        if not topic:
            abort(404)
        return 'resource/' + topic['file']

    @bp.route('/api/admin/resources/<topic_id>', methods=['POST'])
    @bp.route('/api/admin/resources/<topic_id>/<item_id>', methods=['POST', 'DELETE'])
    def edit_item(topic_id, item_id=None):
        require_admin()
        if not valid_csrf():
            abort(400)
        path = topic_path(topic_id)
        with MUTATIONS:
            document = store().document(path)
            items = document.get('items', [])
            previous = next((x for x in items if x.get('id') == item_id), None) if item_id else None
            if item_id and not previous:
                abort(404)
            if request.method == 'DELETE':
                image = previous.get('image', '')
                document['items'] = [x for x in items if x.get('id') != item_id]
                document['itemCount'] = len(document['items'])
                # Remove the catalogue reference first. Images go to Drive trash, never permanent delete.
                store().write_document(path, document)
                if image and not any(x.get('image') == image for x in document['items']) and not store().referenced_elsewhere(image, path):
                    try:
                        store().trash('resource/' + image)
                    except DriveMissing:
                        pass
                return jsonify(ok=True)
            item = dict(previous) if previous else {'id': 'user-' + secrets.token_hex(12), 'enabled': True, 'facts': [], 'topic': topic_id}
            for field in ('viName', 'enName', 'description', 'descriptionEn'):
                value = request.form.get(field, '').strip()
                if not value or len(value) > 5000:
                    return jsonify(ok=False, message='Điền đủ tên và mô tả tiếng Việt, tiếng Anh (tối đa 5000 ký tự)'), 400
                item[field] = value
            upload = request.files.get('image')
            if upload and upload.filename:
                body = upload.read(MAX_IMAGE + 1)
                if len(body) > MAX_IMAGE:
                    abort(413)
                try:
                    with Image.open(io.BytesIO(body)) as im:
                        im.verify()
                        fmt = im.format
                    formats = {'PNG': ('png', 'image/png'), 'JPEG': ('jpg', 'image/jpeg'), 'WEBP': ('webp', 'image/webp')}
                    extension, mime = formats[fmt]
                except (UnidentifiedImageError, OSError, ValueError, KeyError, Image.DecompressionBombError):
                    return jsonify(ok=False, message='Chọn ảnh PNG, JPEG hoặc WebP hợp lệ'), 400
                old_image = item.get('image')
                # Unique new path keeps a failed metadata write from replacing a live item's image.
                image = 'images/uploads/' + secrets.token_hex(16) + '.' + extension
                store().write('resource/' + image, body, mime)
                item.update(image=image, checksum=hashlib.sha256(body).hexdigest(), assetFormat=extension)
            else:
                old_image = None
                if not previous:
                    return jsonify(ok=False, message='Chọn ảnh cho tài nguyên mới'), 400
            item.setdefault('slug', item['id'])
            document['items'] = [item if x.get('id') == item_id else x for x in items] if previous else items + [item]
            document['itemCount'] = len(document['items'])
            store().write_document(path, document)
            if old_image and not any(x.get('image') == old_image for x in document['items']) and not store().referenced_elsewhere(old_image, path):
                try:
                    store().trash('resource/' + old_image)
                except DriveMissing:
                    pass
            return jsonify(ok=True, item=item)

    app.register_blueprint(bp)
