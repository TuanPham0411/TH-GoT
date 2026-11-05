from datetime import datetime
from test_auth import ApplicationTest
import auth

class SessionTests(ApplicationTest):
    def test_google_login_is_required_to_open_a_free_session(self):
        self.assertEqual(self.client.get('/').status_code,200)
        self.assertEqual(self.client.get('/play').status_code,200)
        self.assertEqual(self.client.post('/api/sessions',json={'duration_minutes':30}).status_code,401)
        self.google_login()
        page=self.client.get('/').data.decode()
        self.assertIn('gotSessionDuration',page)
        self.assertNotIn('name="game"',page)
        self.assertNotIn('thienha.io.vn',page)

    def test_all_games_duration_steps_and_fixed_deadline(self):
        self.google_login()
        with self.client.session_transaction() as session:csrf=session['csrf']
        for minutes in (10,20,30,40,50,60):
            with self.subTest(minutes=minutes):
                response=self.client.post('/api/sessions',json={'csrf':csrf,'duration_minutes':minutes})
                self.assertEqual(response.status_code,200)
                self.assertTrue(response.json['launch_url'].startswith('/play?session='))
                token=response.json['launch_url'].split('session=')[1]
                result=self.client.get('/api/sessions/'+token).json
                self.assertEqual(len(result['config']['games']),18)
                self.assertEqual(result['config']['duration_minutes'],minutes)
                self.assertEqual((datetime.fromisoformat(result['expires_at'])-datetime.fromisoformat(result['created_at'])).total_seconds(),minutes*60)
                # Reading again, changing games, or reopening cannot extend the server deadline.
                self.assertEqual(self.client.get('/api/sessions/'+token).json['expires_at'],result['expires_at'])
        with self.app.app_context(),auth.connect() as connection:
            tables={row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertEqual(tables,{'users','game_sessions','drive_connection'})

    def test_csrf_limits_and_expiration(self):
        self.google_login()
        with self.client.session_transaction() as session:csrf=session['csrf']
        self.assertEqual(self.client.post('/api/sessions',json={'csrf':'wrong','duration_minutes':30}).status_code,400)
        for invalid in (None,0,5,15,61,70,True,'10',10.5,[],{}):
            with self.subTest(invalid=invalid):
                self.assertEqual(self.client.post('/api/sessions',json={'csrf':csrf,'duration_minutes':invalid}).status_code,400)
        token=self.client.post('/api/sessions',json={'csrf':csrf,'duration_minutes':10}).json['launch_url'].split('session=')[1]
        with self.app.app_context(),auth.connect() as connection:
            connection.execute('UPDATE game_sessions SET expires_at=? WHERE token=?',('2000-01-01T00:00:00+00:00',token))
        self.assertEqual(self.client.get('/api/sessions/'+token).status_code,410)
        self.assertEqual(self.client.get('/api/sessions/'+'x'*32).status_code,404)

    def test_no_parent_site_dependency_in_live_assets(self):
        from pathlib import Path
        for directory in (self.module.ROOT/'templates',self.module.ROOT/'static/js'):
            for file in directory.rglob('*'):
                if file.suffix in ('.html','.js'):
                    self.assertNotIn('thienha.io.vn',file.read_text(),str(file))
        html=self.client.get('/play').data
        self.assertIn(b'session-clock.js',html)
        self.assertNotIn(b'GOT_PORTAL_ORIGIN',html)

    def test_educational_profiles_are_validated_and_do_not_remove_games(self):
        self.google_login()
        with self.client.session_transaction() as session:csrf=session['csrf']
        data=self.client.get('/api/bootstrap').json
        self.assertEqual(len(data['education']['profiles']),4)
        ids={g['id'] for g in data['games']}
        self.assertEqual(set(data['education']['guides']),ids)
        for profile in data['education']['profiles']:
            self.assertTrue(set(profile['recommended'])<=ids)
            response=self.client.post('/api/sessions',json={'csrf':csrf,'duration_minutes':10,'profile':profile['id']})
            token=response.json['launch_url'].split('session=')[1]
            config=self.client.get('/api/sessions/'+token).json['config']
            self.assertEqual(config['profile'],profile['id'])
            self.assertEqual(len(config['games']),18)
        for value in ('unknown',None,[],{},True):
            self.assertEqual(self.client.post('/api/sessions',json={'csrf':csrf,'duration_minutes':10,'profile':value}).status_code,400)
