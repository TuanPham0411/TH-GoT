import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

ROOT=Path(__file__).resolve().parents[1]
APP_DIR=ROOT / 'game'
sys.path.insert(0,str(APP_DIR))
import auth


class ApplicationTest(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.environment=patch.dict(os.environ,{'DATA_DIR':self.directory.name,'PUBLIC_URL':'https://new-host.test','GOOGLE_CLIENT_ID':'unit-test-client-id','GOOGLE_CLIENT_SECRET':'unit-test-client-secret','FLASK_SECRET_KEY':'unit-tests-only-this-is-not-a-production-key'})
        self.environment.start()
        spec=importlib.util.spec_from_file_location('test_subject_app',APP_DIR/'app.py')
        self.module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.app=self.module.app
        self.app.config['TESTING']=True
        self.client=self.app.test_client()

    def tearDown(self):
        self.environment.stop()
        self.directory.cleanup()

    def google_login(self,client=None,**changes):
        client=client or self.client
        response=client.get('/login?next=/account')
        self.assertEqual(response.status_code,302)
        query=parse_qs(urlsplit(response.location).query)
        self.assertEqual(query['redirect_uri'],['https://new-host.test/auth/callback'])
        with client.session_transaction() as session:
            attempt=dict(session['oauth'])
        challenge=base64.urlsafe_b64encode(hashlib.sha256(attempt['verifier'].encode()).digest()).rstrip(b'=').decode()
        self.assertEqual(query['code_challenge'],[challenge])
        claims={'aud':'unit-test-client-id','iss':'https://accounts.google.com','exp':int(time.time())+3600,'nonce':attempt['nonce'],'email_verified':'true','email':'person@example.invalid','sub':'google-user-1','name':'Test Person'}
        claims.update(changes)
        with patch.object(auth,'_json_request',side_effect=[{'id_token':'mock-id-token'},claims]) as provider:
            response=client.get('/auth/callback?code=mock-code&state='+attempt['state'])
        return response,attempt,provider


class GoogleAuthTests(ApplicationTest):
    def test_pkce_verified_google_identity_and_one_use_state(self):
        response,attempt,provider=self.google_login()
        self.assertEqual(response.status_code,302)
        self.assertEqual(response.location,'/account')
        self.assertEqual(provider.call_count,2)
        self.assertIn(b'code_verifier=',provider.call_args_list[0].args[1])
        self.assertEqual(self.client.get('/account').status_code,200)
        self.assertEqual(self.client.get('/auth/callback?code=reused&state='+attempt['state']).status_code,400)
        with self.app.app_context(),auth.connect() as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM users').fetchone()[0],1)

    def test_rejects_unverified_or_wrong_google_claims(self):
        for change in ({'email_verified':'false'},{'aud':'other-client'},{'iss':'https://attacker.invalid'},{'nonce':'wrong'},{'exp':0}):
            with self.subTest(change=change):
                response,_,_=self.google_login(**change)
                self.assertEqual(response.status_code,403)
        with self.app.app_context(),auth.connect() as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM users').fetchone()[0],0)

    def test_rejects_wrong_state_and_expired_attempt(self):
        self.client.get('/login')
        self.assertEqual(self.client.get('/auth/callback?code=mock&state=wrong').status_code,400)
        self.client.get('/login')
        with self.client.session_transaction() as session:
            attempt=session['oauth'];attempt['created']=int(time.time())-601;session['oauth']=attempt
        self.assertEqual(self.client.get('/auth/callback?code=mock&state='+attempt['state']).status_code,400)

    def test_configuration_missing_and_next_cannot_redirect_offsite(self):
        with patch.dict(os.environ,{'GOOGLE_CLIENT_SECRET':''}):
            self.assertEqual(self.client.get('/login').status_code,503)
        self.client.get('/login?next=//attacker.invalid')
        with self.client.session_transaction() as session:
            self.assertEqual(session['oauth']['next'],'/')

    def test_cookie_and_profile_survive_application_restart(self):
        with patch.dict(os.environ,{'FLASK_SECRET_KEY':''}):
            spec=importlib.util.spec_from_file_location('restarted_app',APP_DIR/'app.py')
            first=importlib.util.module_from_spec(spec);spec.loader.exec_module(first)
            self.app=first.app;self.client=self.app.test_client()
            self.google_login()
            cookie=self.client.get_cookie(self.app.config['SESSION_COOKIE_NAME']).value
            second=importlib.util.module_from_spec(spec);spec.loader.exec_module(second)
            client=second.app.test_client()
            client.set_cookie(second.app.config['SESSION_COOKIE_NAME'],cookie)
            self.assertEqual(client.get('/account').status_code,200)
            mode=(Path(self.directory.name)/'session.key').stat().st_mode & 0o777
            self.assertEqual(mode,0o600)

    def test_logout_requires_csrf(self):
        self.google_login()
        self.assertEqual(self.client.post('/logout').status_code,400)
        with self.client.session_transaction() as session:token=session['csrf']
        self.assertEqual(self.client.post('/logout',data={'csrf':token}).status_code,302)
        self.assertEqual(self.client.get('/account').status_code,302)


if __name__=='__main__':unittest.main()
