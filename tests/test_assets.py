"""Asset integrity, safe extraction, offline cache and Drive link handling."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'game'))
import assets


class AssetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / 'game'
        for prefix in assets.PREFIXES:
            path = self.source / prefix / 'sample.png'
            path.parent.mkdir(parents=True)
            path.write_bytes(b'example-image-bytes')
        self.lock_path = self.base / 'assets.lock.json'
        self.lock = assets.pack(self.source, self.base / 'archives', self.lock_path)
        self.archive = self.base / 'archives' / self.lock['archive']
        self.root = self.base / 'installed'

    def test_install_then_restart_without_network_or_archive(self):
        installed = assets.ensure(self.lock_path, self.root, archive=self.archive)
        self.assertTrue(assets.verify_tree(installed, self.lock, full=True))
        self.archive.unlink()
        with patch.object(assets, 'download', side_effect=AssertionError('network used')):
            self.assertEqual(assets.ensure(self.lock_path, self.root), installed)
        self.assertEqual((self.root / 'current').resolve(), installed)

    def test_bad_archive_keeps_active_release(self):
        installed = assets.ensure(self.lock_path, self.root, archive=self.archive)
        self.lock['sha256'] = 'a' * 64
        self.lock_path.write_text(json.dumps(self.lock))
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            assets.ensure(self.lock_path, self.root, archive=self.archive)
        self.assertEqual((self.root / 'current').resolve(), installed)
        self.assertTrue(installed.is_dir())

    def test_incomplete_cache_is_not_accepted(self):
        installed = assets.ensure(self.lock_path, self.root, archive=self.archive)
        (installed / 'static/images/sample.png').unlink()
        with self.assertRaisesRegex(ValueError, 'ASSETS_URL'):
            assets.ensure(self.lock_path, self.root)
        assets.ensure(self.lock_path, self.root, archive=self.archive)
        self.assertTrue(assets.verify_tree(installed, self.lock, full=True))

    def test_full_verification_detects_same_size_corruption(self):
        installed = assets.ensure(self.lock_path, self.root, archive=self.archive)
        (installed / 'static/images/sample.png').write_bytes(b'x' * len(b'example-image-bytes'))
        self.assertFalse(assets.verify_tree(installed, self.lock, full=True))

    def test_rejects_traversal_links_duplicates_and_wrong_inventory(self):
        for kind in ('traversal', 'symlink', 'duplicate', 'missing', 'wrong-content'):
            with self.subTest(kind=kind):
                archive = self.base / (kind + '.tar.gz')
                with tarfile.open(archive, 'w:gz') as tar:
                    if kind != 'missing':
                        name = '../escaped' if kind == 'traversal' else 'resource/images/sample.png'
                        entry = tarfile.TarInfo(name)
                        content = b'wrong-image-content' if kind == 'wrong-content' else b'example-image-bytes'
                        entry.size = len(content)
                        if kind == 'symlink':
                            entry.type = tarfile.SYMTYPE
                            entry.linkname = '/etc/passwd'
                        tar.addfile(entry, io.BytesIO(content))
                        if kind == 'duplicate':
                            tar.addfile(entry, io.BytesIO(content))
                dest = self.base / ('extract-' + kind)
                dest.mkdir()
                with self.assertRaises(ValueError):
                    assets.extract(archive, dest, self.lock)
                self.assertFalse((self.base / 'escaped').exists())

    def test_rejects_missing_media_and_lfs_pointers(self):
        path = self.source / 'resource/images/sample.png'
        path.write_text('version https://git-lfs.github.com/spec/v1\noid sha256:abcd\n')
        with self.assertRaisesRegex(ValueError, 'Hydrate'):
            assets.pack(self.source, self.base / 'other', self.lock_path)
        with self.assertRaisesRegex(ValueError, 'No media'):
            assets.pack(self.base / 'absent', self.base / 'empty', self.lock_path)

    def test_deterministic_archive_and_inventory(self):
        other = assets.pack(self.source, self.base / 'again', self.base / 'again.json')
        self.assertEqual(other['sha256'], self.lock['sha256'])
        self.assertEqual(other['files'], self.lock['files'])

    def test_drive_share_link_and_confirmation_form(self):
        url = assets.download_url('https://drive.google.com/file/d/abc_123/view?usp=sharing&resourcekey=key')
        self.assertIn('id=abc_123', url)
        self.assertIn('resourcekey=key', url)
        self.assertIn('confirm=t', url)
        with self.assertRaisesRegex(ValueError, 'not a folder'):
            assets.download_url('https://drive.google.com/drive/folders/folder123')
        with self.assertRaisesRegex(ValueError, 'HTTPS'):
            assets.download_url('http://example.com/assets.tar.gz')
        form = assets.ConfirmForm()
        form.feed('<form id="download-form" action="https://drive.usercontent.google.com/download"><input name="id" value="abc"><input name="uuid" value="xyz"></form><input name="outside" value="no">')
        self.assertEqual(form.fields, {'id': 'abc', 'uuid': 'xyz'})

    def test_download_is_streamed_and_size_bounded(self):
        class Response(io.BytesIO):
            url = 'https://example.com/archive'
            headers = {'Content-Type': 'application/gzip'}
        opener = unittest.mock.Mock()
        for body in (b'ab', b'abcdef'):
            opener.open.return_value = Response(body)
            with patch.object(assets, 'build_opener', return_value=opener), self.assertRaises(ValueError):
                assets.download(Response.url, self.base / 'partial', 4)
        opener.open.return_value = Response(b'abcd')
        with patch.object(assets, 'build_opener', return_value=opener):
            assets.download(Response.url, self.base / 'complete', 4)
        self.assertEqual((self.base / 'complete').read_bytes(), b'abcd')

    def test_download_confirmation_and_insecure_redirect(self):
        class Response(io.BytesIO):
            url = 'https://drive.usercontent.google.com/download'
            headers = {'Content-Type': 'text/html'}
        html = b'<form id="download-form" action="https://drive.usercontent.google.com/download"><input name="id" value="abc"><input name="confirm" value="token"></form>'
        first = Response(html)
        second = Response(b'data')
        second.headers = {'Content-Type': 'application/octet-stream'}
        opener = unittest.mock.Mock()
        opener.open.side_effect = [first, second]
        with patch.object(assets, 'build_opener', return_value=opener):
            assets.download('https://drive.google.com/file/d/abc/view', self.base / 'confirmed', 4)
        self.assertIn('confirm=token', opener.open.call_args.args[0])
        with self.assertRaisesRegex(ValueError, 'insecure'):
            assets.HTTPSRedirect().redirect_request(None, None, 302, '', {}, 'http://example.com/archive')


if __name__ == '__main__':
    unittest.main()
