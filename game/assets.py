"""Versioned external media. Standard library only; never downloads during image build."""
import argparse
import fcntl
import gzip
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tarfile
import tempfile
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import build_opener, HTTPCookieProcessor, HTTPRedirectHandler

PREFIXES = ('resource/images/', 'static/images/')
CHUNK = 1024 * 1024


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def valid_path(name):
    return (isinstance(name, str) and name.startswith(PREFIXES)
            and '\\' not in name and all(p not in ('', '.', '..') for p in name.split('/'))
            and not PurePosixPath(name).is_absolute())


def read_lock(path):
    lock = json.loads(Path(path).read_text())
    if lock.get('schema') != 1 or not re.fullmatch(r'[0-9a-f]{64}', lock.get('sha256', '')):
        raise ValueError('Invalid assets lock/schema/checksum')
    files = lock.get('files', {})
    if not files or type(lock.get('bytes')) is not int or lock['bytes'] <= 0:
        raise ValueError('Empty assets lock')
    for name, item in files.items():
        if not valid_path(name) or type(item.get('bytes')) is not int or item['bytes'] < 0 or not re.fullmatch(r'[0-9a-f]{64}', item.get('sha256', '')):
            raise ValueError('Invalid asset inventory')
    return lock


def pack(source, output, lock_path):
    source, output = Path(source).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    files = {}
    archive = output / 'th-got-assets.tar.gz'
    temporary = archive.with_suffix('.partial')
    with temporary.open('wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0, compresslevel=1) as compressed, tarfile.open(fileobj=compressed, mode='w|') as tar:
        for prefix in PREFIXES:
            for path in sorted((source / prefix).rglob('*')):
                if path.is_symlink():
                    raise ValueError('Asset symlinks are not allowed')
                if not path.is_file():
                    continue
                with path.open('rb') as stream:
                    if stream.read(100).startswith(b'version https://git-lfs.github.com/spec/'):
                        raise ValueError('Hydrate LFS assets before packing')
                name = path.relative_to(source).as_posix()
                files[name] = {'bytes': path.stat().st_size, 'sha256': sha256(path)}
                info = tar.gettarinfo(str(path), arcname=name)
                info.uid = info.gid = info.mtime = 0
                info.uname = info.gname = ''
                info.mode = 0o644
                with path.open('rb') as stream:
                    tar.addfile(info, stream)
    if not files:
        temporary.unlink()
        raise ValueError('No media found')
    digest = sha256(temporary)
    archive = output / f'th-got-assets-{digest[:16]}.tar.gz'
    temporary.replace(archive)
    lock = {'schema': 1, 'archive': archive.name, 'url': '', 'sha256': digest,
            'bytes': archive.stat().st_size, 'files': files}
    Path(lock_path).write_text(json.dumps(lock, ensure_ascii=False, indent=2) + '\n')
    print(f'Packed {len(files)} files, {lock["bytes"]} bytes: {archive}')
    return lock


class ConfirmForm(HTMLParser):
    def __init__(self):
        super().__init__()
        self.action = None
        self.fields = {}
        self.in_form = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'form' and attrs.get('id') == 'download-form':
            self.action = attrs.get('action')
            self.in_form = True
        elif self.in_form and tag == 'input' and attrs.get('name'):
            self.fields[attrs['name']] = attrs.get('value', '')

    def handle_endtag(self, tag):
        if tag == 'form':
            self.in_form = False


def download_url(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('ASSETS_URL must be a public HTTPS URL')
    if parsed.hostname in ('drive.google.com', 'drive.usercontent.google.com'):
        query = parse_qs(parsed.query)
        match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', parsed.path)
        file_id = match.group(1) if match else query.get('id', [''])[0]
        if not re.fullmatch(r'[a-zA-Z0-9_-]+', file_id):
            raise ValueError('Use a Drive FILE share link, not a folder link')
        params = {'id': file_id, 'export': 'download', 'confirm': 't'}
        if query.get('resourcekey'):
            params['resourcekey'] = query['resourcekey'][0]
        return 'https://drive.usercontent.google.com/download?' + urlencode(params)
    return url


class HTTPSRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme != 'https':
            raise ValueError('Refusing insecure download redirect')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(url, target, expected_bytes):
    opener = build_opener(HTTPSRedirect(), HTTPCookieProcessor(http.cookiejar.CookieJar()))
    url = download_url(url)
    for _ in range(2):
        with opener.open(url, timeout=120) as response:
            # HTTPS redirect verification remains enabled through the system trust store.
            if urlsplit(response.url).scheme != 'https':
                raise ValueError('Refusing insecure download redirect')
            if 'text/html' in response.headers.get('Content-Type', ''):
                form = ConfirmForm()
                form.feed(response.read(CHUNK).decode('utf-8', errors='replace'))
                action = urlsplit(form.action or '')
                if action.scheme != 'https' or action.hostname != 'drive.usercontent.google.com' or not form.fields.get('id'):
                    raise ValueError('Drive did not return an archive; enable public file download and check quota')
                url = form.action + ('&' if '?' in form.action else '?') + urlencode(form.fields)
                continue
            count = 0
            with Path(target).open('wb') as stream:
                while block := response.read(CHUNK):
                    count += len(block)
                    if count > expected_bytes:
                        raise ValueError('Download exceeds pinned archive size')
                    stream.write(block)
            if count != expected_bytes:
                raise ValueError('Incomplete archive download')
            return
    raise ValueError('Drive download confirmation failed')


def verify_tree(directory, lock, full=False):
    directory = Path(directory)
    if not directory.is_dir() or directory.is_symlink():
        return False
    for name, item in lock['files'].items():
        path = directory / name
        if not path.is_file() or path.is_symlink() or directory.resolve() not in path.resolve().parents or path.stat().st_size != item['bytes']:
            return False
        if full and sha256(path) != item['sha256']:
            return False
    return True


def extract(archive, directory, lock):
    seen = set()
    with tarfile.open(archive, mode='r|gz') as tar:
        for entry in tar:
            expected = lock['files'].get(entry.name)
            if not entry.isfile() or not valid_path(entry.name) or expected is None or entry.name in seen or entry.size != expected['bytes']:
                raise ValueError('Unsafe or unexpected archive member')
            seen.add(entry.name)
            path = directory / entry.name
            path.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(entry) as source, path.open('xb') as destination:
                shutil.copyfileobj(source, destination, CHUNK)
            path.chmod(0o644)
            if sha256(path) != expected['sha256']:
                raise ValueError('Extracted asset checksum mismatch')
    if seen != set(lock['files']):
        raise ValueError('Archive is missing assets')


def ensure(lock_path, root, url=None, archive=None):
    lock = read_lock(lock_path)
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.install.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        releases = root / 'releases'
        releases.mkdir(exist_ok=True)
        release = releases / lock['sha256']
        marker = release / '.verified'
        if not (marker.is_file() and marker.read_text() == lock['sha256'] and verify_tree(release, lock)):
            url = url or lock.get('url')
            if not archive and not url:
                raise ValueError('Assets not installed. Set ASSETS_URL to the public Drive FILE link, or import with --archive')
            print(f'Installing {len(lock["files"])} media files ({lock["bytes"]} archive bytes)', flush=True)
            with tempfile.TemporaryDirectory(prefix='.install-', dir=root) as temp:
                temp = Path(temp)
                source = Path(archive) if archive else temp / 'assets.tar.gz'
                if not archive:
                    download(url, source, lock['bytes'])
                if source.stat().st_size != lock['bytes'] or sha256(source) != lock['sha256']:
                    raise ValueError('Archive size/SHA-256 mismatch; existing version is unchanged')
                staged = temp / 'release'
                staged.mkdir()
                extract(source, staged, lock)
                (staged / '.verified').write_text(lock['sha256'])
                # Only this version can be replaced, after complete verification.
                if release.exists():
                    shutil.rmtree(release)
                staged.replace(release)
        link = root / '.current-new'
        link.unlink(missing_ok=True)
        link.symlink_to(Path('releases') / lock['sha256'])
        link.replace(root / 'current')
        print('Assets ready (local cache)', flush=True)
    return release


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('pack')
    p.add_argument('--source', default='game')
    p.add_argument('--output', required=True)
    p.add_argument('--lock', default='assets.lock.json')
    for command in ('install', 'verify', 'run'):
        p = sub.add_parser(command)
        p.add_argument('--lock', default=os.environ.get('ASSETS_LOCK', 'assets.lock.json'))
        p.add_argument('--root', default=os.environ.get('ASSETS_ROOT', '.assets'))
        if command == 'install':
            p.add_argument('--archive')
            p.add_argument('--url')
        if command == 'run':
            p.add_argument('process', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command == 'pack':
        pack(args.source, args.output, args.lock)
    elif args.command == 'verify':
        lock = read_lock(args.lock)
        if not verify_tree(Path(args.root) / 'releases' / lock['sha256'], lock, full=True):
            raise ValueError('Installed assets failed full verification')
        print('All installed asset checksums passed')
    else:
        release = ensure(args.lock, args.root, url=getattr(args, 'url', None) or os.environ.get('ASSETS_URL'), archive=getattr(args, 'archive', None))
        if args.command == 'run':
            process = args.process
            if process and process[0] == '--':
                process = process[1:]
            if not process:
                raise ValueError('Missing server command')
            os.environ['ASSET_DIR'] = str(release)
            os.execvp(process[0], process)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, tarfile.TarError) as error:
        # HTTP exceptions may include provider URLs; never log credentials/response bodies.
        print(f'Asset setup failed: {type(error).__name__}: {error if isinstance(error, ValueError) else "I/O or network failure; check access, space and permissions"}', file=sys.stderr)
        sys.exit(1)
