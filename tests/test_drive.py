import copy
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from urllib.error import HTTPError
from PIL import Image

from test_auth import ApplicationTest
import auth
import drive_store
import drive_migration


def png(colour='red'):
    result=io.BytesIO(); Image.new('RGB',(32,32),colour).save(result,'PNG'); return result.getvalue()


class FakeDrive:
    folder='test-folder'
    def __init__(self, root=None):
        self.files={}; self.writes=[]; self.trashed=[]
        if root:
            for path in Path(root).glob('*.json'):
                self.files['resource/'+path.name]=(path.read_bytes(),'application/json')
    def lookup(self,path):
        if path not in self.files: raise drive_store.DriveMissing()
        return {'id':path,'mimeType':self.files[path][1]}
    def read(self,path):
        self.lookup(path); return self.files[path]
    def document(self,path): return json.loads(self.read(path)[0])
    def write(self,path,body,mime): self.writes.append(path); self.files[path]=(body,mime); return path
    def write_document(self,path,body): return self.write(path,json.dumps(body).encode(),'application/json')
    def trash(self,path): self.lookup(path); del self.files[path]; self.trashed.append(path)
    def referenced_elsewhere(self,image,excluded):
        return any(image in body.decode() for path,(body,mime) in self.files.items() if path!=excluded and mime=='application/json')


class DriveResourceTests(ApplicationTest):
    def setUp(self):
        super().setUp()
        self.admin_env=patch.dict(os.environ,{'ADMIN_EMAILS':'person@example.invalid'})
        self.admin_env.start(); self.addCleanup(self.admin_env.stop)
        self.drive=FakeDrive(self.module.RESOURCE)
        self.app.extensions['drive_store']=self.drive
        with self.app.app_context(),auth.connect() as connection:
            connection.execute('INSERT INTO drive_connection VALUES(1,?,?)',('person@example.invalid',drive_store.cipher().encrypt(b'fake-refresh').decode()))
        self.first=self.drive.document('resource/topic-animal.json')['items'][0]
        self.drive.files['resource/'+self.first['image']]=(png(),'image/png')

    def login_admin(self):
        self.google_login()
        with self.client.session_transaction() as session: self.csrf=session['csrf']

    def fields(self):
        return {'viName':'Ảnh mới','enName':'New image','description':'Mô tả mới','descriptionEn':'New description'}

    def test_no_disk_images_and_no_browser_cache(self):
        for path in ('/resource/'+self.first['image'],'/thumb/'+self.first['image']):
            response=self.client.get(path)
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.headers['Cache-Control'],'no-store')
            self.assertNotIn('ETag',response.headers)
        self.drive.files['resource/'+self.first['image']]=(png('blue'),'image/png')
        self.assertEqual(self.client.get('/resource/'+self.first['image']).data,png('blue'))
        self.assertFalse(list(Path(self.directory.name).rglob('*.png')))
        self.assertFalse(list(Path(self.directory.name).rglob('*.webp')))

    def test_drive_failure_never_serves_a_local_fallback(self):
        with patch.object(self.drive,'read',side_effect=drive_store.DriveUnavailable('Drive unavailable')):
            response=self.client.get('/resource/'+self.first['image'])
        self.assertEqual(response.status_code,503)
        self.assertEqual(response.headers['Cache-Control'],'no-store')
        self.assertEqual(self.client.get('/resource/images/../../app.py').status_code,404)

    def test_admin_and_csrf_are_required_for_drive_mutation(self):
        self.assertEqual(self.client.post('/api/admin/resources/animal').status_code,401)
        self.google_login(email='other@example.invalid')
        self.assertEqual(self.client.get('/admin/resources').status_code,403)
        self.assertEqual(self.drive.writes,[])
        self.login_admin()
        self.assertEqual(self.client.post('/api/admin/resources/animal',data=self.fields()).status_code,400)
        self.assertEqual(self.drive.writes,[])

    def test_create_update_delete_changes_drive_and_live_catalog(self):
        self.login_admin()
        fields=self.fields(); fields['image']=(io.BytesIO(png()),'sample.png')
        response=self.client.post('/api/admin/resources/animal',data=fields,headers={'X-CSRF-Token':self.csrf})
        self.assertEqual(response.status_code,200,response.data)
        item=response.json['item']; image='resource/'+item['image']
        self.assertIn(image,self.drive.files)
        current=self.client.get('/api/topic/animal').json['items']
        self.assertIn(item['id'],[i['id'] for i in current])
        fields=self.fields(); fields['viName']='Tên đã sửa'; fields['image']=(io.BytesIO(png('blue')),'blue.png')
        response=self.client.post('/api/admin/resources/animal/'+item['id'],data=fields,headers={'X-CSRF-Token':self.csrf})
        self.assertEqual(response.status_code,200,response.data)
        replacement='resource/'+response.json['item']['image']
        self.assertIn(image,self.drive.trashed)
        self.assertEqual(self.drive.files[replacement][0],png('blue'))
        response=self.client.delete('/api/admin/resources/animal/'+item['id'],headers={'X-CSRF-Token':self.csrf})
        self.assertEqual(response.status_code,200,response.data)
        self.assertIn(replacement,self.drive.trashed)
        self.assertNotIn(item['id'],[i['id'] for i in self.client.get('/api/topic/animal').json['items']])

    def test_shared_image_is_not_trashed(self):
        self.login_admin()
        self.drive.files['resource/other.json']=(json.dumps({'image':self.first['image']}).encode(),'application/json')
        response=self.client.delete('/api/admin/resources/animal/'+self.first['id'],headers={'X-CSRF-Token':self.csrf})
        self.assertEqual(response.status_code,200)
        self.assertEqual(self.drive.trashed,[])

    def test_large_upload_never_spools_to_disk(self):
        self.login_admin()
        output=io.BytesIO(); Image.frombytes('RGB',(640,640),os.urandom(640*640*3)).save(output,'PNG')
        self.assertGreater(len(output.getvalue()),500_000)
        boundary='memory-upload-test'
        data=b''
        for key,value in self.fields().items():
            data+=f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
        data+=f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="image.png"\r\nContent-Type: image/png\r\n\r\n'.encode()+output.getvalue()+f'\r\n--{boundary}--\r\n'.encode()
        with patch('tempfile.TemporaryFile',side_effect=AssertionError('image spooled to disk')):
            response=self.client.post('/api/admin/resources/animal',data=data,content_type='multipart/form-data; boundary='+boundary,headers={'X-CSRF-Token':self.csrf})
        self.assertEqual(response.status_code,200,response.data)

    def test_invalid_image_cannot_create_a_drive_file(self):
        self.login_admin(); fields=self.fields(); fields['image']=(io.BytesIO(b'not an image'),'fake.png')
        response=self.client.post('/api/admin/resources/animal',data=fields,headers={'X-CSRF-Token':self.csrf})
        self.assertEqual(response.status_code,400); self.assertEqual(self.drive.writes,[])

    def test_drive_consent_is_separate_from_player_login_and_replay_safe(self):
        self.login_admin()
        self.assertEqual(self.client.get('/admin/resources').status_code,200)
        response=self.client.post('/admin/drive/connect',data={'csrf':self.csrf})
        query=parse_qs(urlsplit(response.location).query)
        self.assertIn(drive_store.SCOPE,query['scope'][0]); self.assertEqual(query['access_type'],['offline'])
        with self.client.session_transaction() as session: attempt=dict(session['drive_oauth'])
        identity={'aud':'unit-test-client-id','iss':'https://accounts.google.com','exp':int(time.time())+3600,'nonce':attempt['nonce'],'email_verified':'true','sub':'google-user-1'}
        tokens={'access_token':'fake-access','refresh_token':'new-fake-refresh','id_token':'fake-id','scope':drive_store.SCOPE}
        with patch.object(drive_store,'_json_request',side_effect=[tokens,identity]),patch.object(drive_store.DriveStore,'check_folder'):
            response=self.client.get('/admin/drive/callback?code=fake&state='+attempt['state'])
        self.assertEqual(response.status_code,302)
        with self.app.app_context(),auth.connect() as connection:
            saved=connection.execute('SELECT refresh_encrypted FROM drive_connection').fetchone()[0]
            self.assertNotIn('new-fake-refresh',saved)
            self.assertEqual(drive_store.cipher().decrypt(saved.encode()),b'new-fake-refresh')
        self.assertEqual(self.client.get('/admin/drive/callback?code=fake&state='+attempt['state']).status_code,400)


class DriveApiTests(unittest.TestCase):
    def test_lookup_is_folder_scoped_and_traversal_is_rejected(self):
        store=drive_store.DriveStore(lambda:'not-a-real-token',folder='fixed-folder')
        with patch.object(store,'call',return_value=b'{"files":[{"id":"known"}]}') as api:
            self.assertEqual(store.lookup('resource/images/test.png')['id'],'known')
            self.assertIn("'fixed-folder' in parents",api.call_args.kwargs['q'])
            with self.assertRaises(drive_store.DriveMissing): store.lookup('../private.png')
            self.assertEqual(api.call_count,1)

    def test_provider_errors_are_sanitized(self):
        store=drive_store.DriveStore(lambda:'not-a-real-token',folder='fixed-folder')
        error=HTTPError('https://provider.invalid/secret',403,'secret message',{},None)
        with patch.object(drive_store,'urlopen',side_effect=error):
            with self.assertRaises(drive_store.DriveUnavailable) as caught: store.read('resource/images/a.png')
        self.assertNotIn('secret',str(caught.exception)); self.assertNotIn('not-a-real-token',str(caught.exception))


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(); self.addCleanup(self.directory.cleanup)
        self.root=Path(self.directory.name); self.resource=self.root/'resource'; self.resource.mkdir()
        (self.resource/'topics.json').write_text('{"topics":[]}')
        self.buffer=io.BytesIO(); self.image=png()
        self.name='resource/images/test.png'
        with tarfile.open(fileobj=self.buffer,mode='w:gz') as archive:
            entry=tarfile.TarInfo(self.name); entry.size=len(self.image); archive.addfile(entry,io.BytesIO(self.image))
        self.body=self.buffer.getvalue()
        self.lock={'bytes':len(self.body),'sha256':hashlib.sha256(self.body).hexdigest(),'files':{self.name:{'bytes':len(self.image),'sha256':hashlib.sha256(self.image).hexdigest()}}}
        self.lock_path=self.root/'lock.json'; self.lock_path.write_text(json.dumps(self.lock))
        self.drive=FakeDrive()

    def test_migration_verifies_and_uploads_from_memory_then_never_overwrites_edits(self):
        opener=lambda *_:io.BytesIO(self.body)
        drive_migration.migrate(self.drive,self.resource,self.lock_path,opener=opener)
        self.assertEqual(self.drive.files[self.name][0],self.image)
        self.assertIn(drive_migration.MARKER,self.drive.files)
        self.assertFalse(list(self.root.rglob('*.png')))
        self.drive.files[self.name]=(png('blue'),'image/png'); writes=len(self.drive.writes)
        drive_migration.migrate(self.drive,self.resource,self.lock_path,opener=lambda *_:self.fail('archive downloaded after initialization'))
        self.assertEqual(len(self.drive.writes),writes)
        self.assertEqual(self.drive.files[self.name][0],png('blue'))

    def test_bad_archive_uploads_nothing_and_missing_files_cannot_mark_ready(self):
        with self.assertRaises(ValueError):
            drive_migration.migrate(self.drive,self.resource,self.lock_path,opener=lambda *_:io.BytesIO(b'corrupt'))
        self.assertEqual(self.drive.writes,[])
        self.lock['files']['resource/images/missing.png']=self.lock['files'][self.name]
        self.lock_path.write_text(json.dumps(self.lock))
        with self.assertRaises(ValueError):
            drive_migration.migrate(self.drive,self.resource,self.lock_path,opener=lambda *_:io.BytesIO(self.body))
        self.assertNotIn(drive_migration.MARKER,self.drive.files)
