import hashlib
import io
from pathlib import Path
from unittest.mock import Mock, patch
from PIL import Image
from test_auth import ApplicationTest
import realm_media


class RealmTests(ApplicationTest):
    def test_verified_copy_is_optimized_and_revalidated(self):
        output=io.BytesIO();Image.new('RGB',(80,50),'green').save(output,format='PNG');body=output.getvalue()
        asset={'path':'images/realm-v13/test.png','sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'mime':'image/png'}
        source=Mock();source.read.return_value=(body,'image/png')
        with patch.dict(realm_media.MANIFEST,{'test-art':asset}),patch.object(realm_media.drive_store,'store',return_value=source):
            first=self.client.get('/world-assets/test-art');self.assertEqual(first.status_code,200);self.assertEqual(first.mimetype,'image/webp');self.assertEqual(Image.open(io.BytesIO(first.data)).size,(80,50));first.close()
            second=self.client.get('/world-assets/test-art');self.assertEqual(second.status_code,200);second.close()
            self.assertEqual(source.read.call_count,1);self.assertEqual(source.view_cache.lookup.call_count,2)
            source.view_cache.lookup.side_effect=realm_media.drive_store.DriveMissing()
            self.assertNotEqual(self.client.get('/world-assets/test-art').status_code,200)

    def test_corrupt_source_is_not_cached(self):
        source=Mock();source.read.return_value=(b'wrong','image/png')
        asset={'path':'images/realm-v13/test.png','sha256':'0'*64,'bytes':5,'mime':'image/png'}
        with patch.dict(realm_media.MANIFEST,{'bad':asset}),patch.object(realm_media.drive_store,'store',return_value=source):
            self.assertEqual(self.client.get('/world-assets/bad').status_code,503)
            self.assertFalse(list((Path(self.directory.name)/'realm-media').glob('*.webp')))
        self.assertEqual(self.client.get('/world-assets/unknown').status_code,404)

    def test_cinema_supports_range_requests(self):
        body=b'first-party-test-video-bytes';source=Mock();source.read.return_value=(body,'video/mp4')
        asset={'path':'videos/realm-v13/test.mp4','sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'mime':'video/mp4'}
        with patch.dict(realm_media.MANIFEST,{'film-test':asset}),patch.object(realm_media.drive_store,'store',return_value=source):
            response=self.client.get('/world-assets/film-test',headers={'Range':'bytes=0-5'})
            self.assertEqual(response.status_code,206);self.assertEqual(response.data,body[:6]);self.assertEqual(response.headers['CDN-Cache-Control'],'no-store');response.close()

    def test_child_world_keeps_library_and_source_notes(self):
        page=self.client.get('/').get_data(as_text=True)
        self.assertIn('realm-stage',page);self.assertIn('/play?view=library',page);self.assertIn('realmBackpack',page)
        catalog=self.client.get('/api/world/catalog').json
        self.assertGreaterEqual(len(catalog['activities']),48);self.assertEqual(len(catalog['stories']),16)
        for story in catalog['stories']:
            self.assertTrue(story['sourceUrl'].startswith('https://'));self.assertTrue(story['editionNote']);self.assertEqual(len(story['pages']),4)
            if story.get('atlas'):self.assertIn(story['atlas'],realm_media.MANIFEST)

    def test_importer_preserves_originals_and_rejects_extra_files(self):
        import importlib.util,sys,tarfile
        from types import SimpleNamespace
        tool=Path(__file__).resolve().parents[1]/'tools/install_realm_media.py'
        with patch.dict(sys.modules,{'app':SimpleNamespace(app=self.app)}):
            spec=importlib.util.spec_from_file_location('realm_import_test',tool);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        body=b'original';asset={'path':'images/realm-v13/test.png','sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'mime':'image/png'}
        def archive(extra=False):
            import json
            stream=io.BytesIO()
            with tarfile.open(fileobj=stream,mode='w:gz') as tar:
                for name,data in [('realm-assets.json',json.dumps({'test':asset}).encode()),('test',body)]+([('../bad',b'x')] if extra else []):
                    info=tarfile.TarInfo(name);info.size=len(data);tar.addfile(info,io.BytesIO(data))
            stream.seek(0);return stream
        source=Mock();source.read.return_value=(body,'image/png')
        with patch.object(module,'store',return_value=source):
            module.install(archive());source.write.assert_not_called()
            with self.assertRaises(ValueError):module.install(archive(extra=True))
            source.read.return_value=(b'conflicting existing original','image/png')
            with self.assertRaisesRegex(ValueError,'Refusing to replace'):module.install(archive())
            source.write.assert_not_called()
