import gzip
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image

TEST_DATA=tempfile.TemporaryDirectory()
os.environ['DATA_DIR']=TEST_DATA.name
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

spec = importlib.util.spec_from_file_location('game_app', Path(__file__).resolve().parents[1] / 'app.py')
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.client = module.app.test_client()
        self.assets_temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.assets_temp.cleanup)
        assets = Path(self.assets_temp.name)
        for prefix in ('resource/images', 'static/images'):
            (assets / prefix).mkdir(parents=True)
        asset_patch = patch.object(module, 'ASSET_DIR', assets)
        asset_patch.start()
        self.addCleanup(asset_patch.stop)

    def test_readiness(self):
        self.assertEqual(self.client.get('/healthz').status_code, 200)
        with tempfile.TemporaryDirectory() as directory, patch.object(module, 'RESOURCE', Path(directory)):
            self.assertEqual(self.client.get('/healthz').status_code, 503)

    def test_gzip_negotiation(self):
        url = '/api/bootstrap'
        plain = self.client.get(url)
        denied = self.client.get(url, headers={'Accept-Encoding': 'gzip;q=0'})
        self.assertNotIn('Content-Encoding', denied.headers)
        encoded = self.client.get(url, headers={'Accept-Encoding': 'gzip'})
        self.assertEqual(encoded.headers['Content-Encoding'], 'gzip')
        self.assertEqual(gzip.decompress(encoded.data), plain.data)
        for response in (plain, denied, encoded):
            self.assertIn('Accept-Encoding', response.headers['Vary'])

    def test_traversal_and_missing_topics(self):
        for url in ('/thumb/../app.py', '/resource/../app.py', '/api/topic/not-a-topic'):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.headers['Cache-Control'], 'no-store')

    def test_audio_text_cannot_be_a_command_option(self):
        result = subprocess.CompletedProcess([], 0, stdout=b'RIFF-test')
        with patch.object(module.subprocess, 'run', return_value=result) as run:
            response = self.client.get('/api/tts?text=--version')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(run.call_args.args[0][-2:], ['--', '--version'])
            self.assertIn('max-age=86400', response.headers['Cache-Control'])

    def test_template_and_catalog(self):
        response = self.client.get('/play')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'app-v89.js', response.data)
        for topic in self.client.get('/api/bootstrap').json['topics']:
            self.assertEqual(self.client.get('/api/topic/' + topic['id']).status_code, 200)

    def test_external_asset_mapping_and_readiness(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for prefix in ('resource/images', 'static/images'):
                path = root / prefix / 'external.png'
                path.parent.mkdir(parents=True)
                Image.new('RGB', (16, 16), 'red').save(path)
            lock = root / 'lock.json'
            lock.write_text('{"sha256":"expected"}')
            with patch.object(module, 'ASSET_DIR', root), patch.object(module, 'THUMB_CACHE', root / 'thumbs'), patch.dict(os.environ, {'ASSETS_LOCK': str(lock)}):
                self.assertEqual(self.client.get('/healthz').status_code, 503)
                (root / '.verified').write_text('expected')
                self.assertEqual(self.client.get('/healthz').status_code, 200)
                for url in ('/resource/images/external.png', '/static/images/external.png', '/thumb/images/external.png'):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 200)
                    self.assertIn('image/', response.content_type)
                    response.close()
                for url in ('/resource/images/../../app.py', '/static/images/../../app.py', '/thumb/games.json'):
                    self.assertEqual(self.client.get(url).status_code, 404)

    def test_range_is_not_compressed(self):
        response = self.client.get('/static/js/app-v89.js', headers={'Range': 'bytes=0-99', 'Accept-Encoding': 'gzip'})
        self.assertEqual(response.status_code, 206)
        self.assertEqual(len(response.data), 100)
        self.assertNotIn('Content-Encoding', response.headers)
        response.close()


if __name__ == '__main__':
    unittest.main()
