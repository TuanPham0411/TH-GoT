"""Package locally supplied originals for the manifest-limited Drive importer."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile


def pack(local_map, output):
    manifest_path = Path(__file__).resolve().parents[1] / 'game/realm-assets.json'
    manifest = json.loads(manifest_path.read_text())
    local = json.loads(Path(local_map).read_text())
    files = {}
    for key, item in manifest.items():
        path = Path(local[key])
        body = path.read_bytes()
        if len(body) != item['bytes'] or hashlib.sha256(body).hexdigest() != item['sha256']:
            raise ValueError('Local original does not match manifest: ' + key)
        files[key] = path
    with tarfile.open(output, 'w:gz') as archive:
        body = manifest_path.read_bytes()
        info = tarfile.TarInfo('realm-assets.json')
        info.size = len(body)
        archive.addfile(info, io.BytesIO(body))
        for key, path in files.items():
            archive.add(path, arcname=key)
    digest = hashlib.sha256(Path(output).read_bytes()).hexdigest()
    Path(str(output) + '.sha256').write_text(digest + '\n')
    print('Packaged', len(files), 'verified originals;', digest)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('local_map')
    parser.add_argument('output')
    args = parser.parse_args()
    pack(args.local_map, args.output)
