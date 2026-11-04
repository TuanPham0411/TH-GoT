"""One-time archive-to-Drive migration; no archive or image is written to disk."""
import hashlib
import json
from pathlib import Path
import tarfile
from urllib.request import Request, urlopen
from urllib.parse import quote

from drive_store import DriveMissing, DriveUnavailable, MAX_IMAGE, valid_path

ARCHIVE_ID = '1JsQk7-4mWJlmCJDd5TdDy9mnUnEm41U5'
MARKER = 'resource/drive-ready.json'


def source(store, archive_id):
    # Fixed Google API destination; credentials never travel to a supplied URL.
    req = Request('https://www.googleapis.com/drive/v3/files/' + quote(archive_id, safe='') + '?alt=media&supportsAllDrives=true',
                  headers={'Authorization': 'Bearer ' + store.token_provider()})
    return urlopen(req, timeout=120)


def migrate(store, resource_root, lock_path, progress=lambda **_: None, opener=source):
    lock = json.loads(Path(lock_path).read_text())
    inventory = lock['files']
    try:
        marker = store.document(MARKER)
        if (marker.get('schema') != 1 or marker.get('archive_sha256') != lock['sha256']
                or marker.get('initial_images') != len(inventory)):
            raise DriveUnavailable('Invalid Drive migration marker; inspect the existing Drive data')
        progress(stage='complete', message='Drive đã được khởi tạo; không ghi đè tài nguyên đã sửa')
        return
    except DriveMissing:
        pass
    # Verify the whole pinned archive before uploading anything; keep only a chunk in RAM.
    progress(stage='verify-archive', done=0, total=lock['bytes'])
    count, checksum = 0, hashlib.sha256()
    with opener(store, ARCHIVE_ID) as stream:
        while block := stream.read(1024 * 1024):
            count += len(block)
            if count > lock['bytes']:
                raise ValueError('Archive exceeds pinned size')
            checksum.update(block)
            progress(stage='verify-archive', done=count, total=lock['bytes'])
    if count != lock['bytes'] or checksum.hexdigest() != lock['sha256']:
        raise ValueError('Archive size/SHA-256 mismatch; nothing was uploaded')
    seen = set()
    # Stream a second pass, verify each member and upload one image at a time.
    with opener(store, ARCHIVE_ID) as stream, tarfile.open(fileobj=stream, mode='r|gz') as archive:
        for entry in archive:
            expected = inventory.get(entry.name)
            if (not entry.isfile() or not valid_path(entry.name) or expected is None
                    or entry.name in seen or entry.size != expected['bytes'] or entry.size > MAX_IMAGE):
                raise ValueError('Unsafe or unexpected archive member')
            with archive.extractfile(entry) as image:
                body = image.read(MAX_IMAGE + 1)
            if len(body) != expected['bytes'] or hashlib.sha256(body).hexdigest() != expected['sha256']:
                raise ValueError('Image checksum mismatch')
            try:
                existing, _ = store.read(entry.name)
            except DriveMissing:
                existing = None
            if existing is not None and hashlib.sha256(existing).hexdigest() != expected['sha256']:
                raise ValueError('A Drive image was edited; migration will not overwrite it')
            if existing is None:
                suffix = Path(entry.name).suffix.lower()
                mime = {'.png': 'image/png', '.webp': 'image/webp', '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml'}.get(suffix)
                if not mime:
                    raise ValueError('Unexpected image type')
                store.write(entry.name, body, mime)
            seen.add(entry.name)
            progress(stage='upload-images', done=len(seen), total=len(inventory))
    if seen != set(inventory):
        raise ValueError('Archive is missing images')
    for path in sorted(Path(resource_root).glob('*.json')):
        name = 'resource/' + path.name
        try:
            store.lookup(name)
        except DriveMissing:
            store.write_document(name, json.loads(path.read_text()))
    store.write_document(MARKER, {'schema': 1, 'initial_images': len(seen), 'archive_sha256': lock['sha256']})
    progress(stage='complete', done=len(seen), total=len(inventory))
