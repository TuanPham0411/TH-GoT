"""Google OIDC authentication backed only by this application's own SQLite volume."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request

from flask import abort, current_app, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix


@contextmanager
def connect():
    connection = sqlite3.connect(current_app.config['DATABASE'], timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys=ON')
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def user():
    if 'account' not in g:
        uid = session.get('uid')
        with connect() as connection:
            g.account = connection.execute('SELECT id,email,name,picture FROM users WHERE id=?', (uid,)).fetchone() if uid else None
    return g.account


def csrf_token():
    if not session.get('csrf'):
        session['csrf'] = secrets.token_urlsafe(32)
    return session['csrf']


def valid_csrf(value=None):
    supplied = value if value is not None else request.headers.get('X-CSRF-Token') or request.form.get('csrf', '')
    expected = session.get('csrf', '')
    return isinstance(supplied, str) and bool(expected) and secrets.compare_digest(expected, supplied)


def safe_next(value):
    if isinstance(value, str) and value.startswith('/') and not value.startswith('//') and '\\' not in value and not any(x in value for x in '\r\n'):
        return value
    return '/'


def _json_request(url, data=None):
    req = urllib.request.Request(url, data=data, headers={'Accept':'application/json','User-Agent':'TH-Standalone/1.0'})
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read(1_000_001))


def configure(app, data_directory):
    os.umask(0o077)
    data = Path(data_directory)
    data.mkdir(parents=True, exist_ok=True, mode=0o700)
    data.chmod(0o700)
    secret = os.environ.get('FLASK_SECRET_KEY')
    if not secret:
        key = data / 'session.key'
        try:
            descriptor = os.open(key, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'w') as stream:
                stream.write(secrets.token_hex(32))
        except FileExistsError:
            pass
        secret = key.read_text().strip()
        if len(secret) < 32:
            raise RuntimeError('Persistent session.key is incomplete; restore a valid key')
    app.secret_key = secret
    app.config['DATABASE'] = str(data / 'app.db')
    public_url = os.environ.get('PUBLIC_URL', '').rstrip('/')
    app.config.update(
        PUBLIC_URL=public_url,
        SESSION_COOKIE_NAME='th_got',
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=public_url.startswith('https://'),
        MAX_CONTENT_LENGTH=2*1024*1024,
    )
    # Exactly one trusted reverse proxy by explicit opt-in; direct Docker is the default.
    if os.environ.get('TRUST_PROXY', '0') == '1':
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    with app.app_context(), connect() as connection:
        connection.execute('CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,google_sub TEXT UNIQUE NOT NULL,email TEXT NOT NULL,name TEXT NOT NULL,picture TEXT NOT NULL,created_at INTEGER NOT NULL)')

    @app.context_processor
    def account_context():
        return {'me':user(), 'csrf_token':csrf_token(), 'google_configured':bool(os.environ.get('GOOGLE_CLIENT_ID') and os.environ.get('GOOGLE_CLIENT_SECRET'))}

    @app.get('/login')
    def login():
        client_id = os.environ.get('GOOGLE_CLIENT_ID')
        if not client_id or not os.environ.get('GOOGLE_CLIENT_SECRET'):
            return render_template('auth_unavailable.html'), 503
        # Use a registered, deployment-specific redirect URI, never an old site hostname.
        callback = os.environ.get('GOOGLE_REDIRECT_URI') or (public_url + '/auth/callback' if public_url else url_for('oauth_callback', _external=True))
        verifier = secrets.token_urlsafe(48)
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        session['oauth'] = {'state':state,'nonce':nonce,'verifier':verifier,'created':int(time.time()),'callback':callback,'next':safe_next(request.args.get('next'))}
        import base64
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        query = urllib.parse.urlencode({'client_id':client_id,'redirect_uri':callback,'response_type':'code','scope':'openid email profile','state':state,'nonce':nonce,'code_challenge':challenge,'code_challenge_method':'S256'})
        return redirect('https://accounts.google.com/o/oauth2/v2/auth?' + query)

    @app.get('/auth/callback')
    def oauth_callback():
        attempt = session.pop('oauth', None)
        supplied = request.args.get('state', '')
        if not attempt or not supplied or not secrets.compare_digest(supplied, attempt['state']) or not 0 <= time.time()-attempt['created'] <= 600:
            abort(400, 'Invalid or expired OAuth state')
        code = request.args.get('code')
        if not code:
            abort(400, 'Google sign-in was not completed')
        client_id = os.environ.get('GOOGLE_CLIENT_ID', '')
        try:
            tokens = _json_request('https://oauth2.googleapis.com/token', urllib.parse.urlencode({'code':code,'client_id':client_id,'client_secret':os.environ.get('GOOGLE_CLIENT_SECRET',''),'redirect_uri':attempt['callback'],'grant_type':'authorization_code','code_verifier':attempt['verifier']}).encode())
            identity = _json_request('https://oauth2.googleapis.com/tokeninfo?' + urllib.parse.urlencode({'id_token':tokens['id_token']}))
            verified = str(identity.get('email_verified','')).lower() == 'true'
            if (identity.get('aud') != client_id or identity.get('iss') not in ('accounts.google.com','https://accounts.google.com') or int(identity.get('exp',0)) <= time.time() or not verified or not identity.get('sub') or not identity.get('email') or not secrets.compare_digest(str(identity.get('nonce','')),attempt['nonce'])):
                abort(403, 'Google identity verification failed')
        except (OSError, ValueError, KeyError, urllib.error.URLError):
            return render_template('auth_unavailable.html'), 502
        with connect() as connection:
            connection.execute('INSERT INTO users(google_sub,email,name,picture,created_at) VALUES(?,?,?,?,?) ON CONFLICT(google_sub) DO UPDATE SET email=excluded.email,name=excluded.name,picture=excluded.picture', (identity['sub'],identity['email'],identity.get('name',''),identity.get('picture',''),int(time.time())))
            uid = connection.execute('SELECT id FROM users WHERE google_sub=?',(identity['sub'],)).fetchone()['id']
        destination = attempt['next']
        session.clear()
        session['uid'] = uid
        session['csrf'] = secrets.token_urlsafe(32)
        return redirect(destination)

    @app.post('/logout')
    def logout():
        if not valid_csrf():
            abort(400)
        session.clear()
        return redirect('/')

    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        if response.mimetype == 'text/html' or request.path.startswith(('/auth/','/login','/account')):
            response.headers['Cache-Control'] = 'no-store'
        return response
