"""Install a pinned, manifest-limited art archive into the existing Drive library.
Run inside the application container; OAuth credentials never leave that host.
"""
import hashlib
import json
import sys
import tarfile
from pathlib import PurePosixPath
from app import app
from drive_store import store, DriveMissing


def install(stream):
    seen=set()
    with tarfile.open(fileobj=stream,mode='r|gz') as archive:
        members=iter(archive)
        first=next(members)
        if first.name!='realm-assets.json' or not first.isfile() or first.size>60000:
            raise ValueError('Manifest must be the first regular file')
        manifest=json.load(archive.extractfile(first))
        if not isinstance(manifest,dict) or not 1<=len(manifest)<=40:
            raise ValueError('Invalid manifest')
        for key,item in manifest.items():
            path=PurePosixPath(item['path'])
            if not key.replace('-','').isalnum() or path.is_absolute() or '..' in path.parts or not str(path).startswith(('images/realm-v13/','videos/realm-v13/','images/realm-v14/')) or not 0<item['bytes']<=32*1024*1024 or item['mime'] not in ('image/png','video/mp4'):
                raise ValueError('Unapproved media entry')
        with app.app_context():
            source=store()
            for member in members:
                if member.name not in manifest or member.name in seen or not member.isfile():
                    raise ValueError('Unexpected archive entry')
                item=manifest[member.name]
                if member.size!=item['bytes']:
                    raise ValueError('Unexpected member size')
                body=archive.extractfile(member).read(item['bytes']+1)
                if hashlib.sha256(body).hexdigest()!=item['sha256']:
                    raise ValueError('Media checksum mismatch')
                try:
                    existing,_=source.read(item['path'])
                except DriveMissing:
                    existing=None
                if existing is not None and hashlib.sha256(existing).hexdigest()!=item['sha256']:
                    raise ValueError('Refusing to replace a conflicting immutable original')
                if existing is None:
                    source.write(item['path'],body,item['mime'])
                verified,_=source.read(item['path'])
                if hashlib.sha256(verified).hexdigest()!=item['sha256']:
                    raise ValueError('Drive readback did not match')
                seen.add(member.name)
                print('Verified on Drive:',member.name,flush=True)
    if seen!=set(manifest):
        raise ValueError('Incomplete archive')
    print('Drive originals verified:',len(seen),flush=True)

if __name__=='__main__':
    install(sys.stdin.buffer)
