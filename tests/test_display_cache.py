import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image

from test_auth import ApplicationTest
from display_cache import DisplayCache
from drive_store import DriveMissing, DriveUnavailable


def picture(colour="red"):
    output = io.BytesIO()
    Image.new("RGB", (900, 600), colour).save(output, "PNG")
    return output.getvalue()


class Origin:
    folder = "fixture-folder"

    def __init__(self):
        self.files = {}
        self.scans = 0
        self.downloads = 0
        self.failure = None

    def put(self, path, body, mime="image/png", version="1"):
        self.files[path] = (
            body,
            {
                "id": hashlib.sha256(path.encode()).hexdigest(),
                "mimeType": mime,
                "version": version,
                "size": str(len(body)),
                "sha256Checksum": hashlib.sha256(body).hexdigest(),
                "md5Checksum": hashlib.md5(body).hexdigest(),
                "appProperties": {
                    "gotPathHash": hashlib.sha256(path.encode()).hexdigest()
                },
            },
        )

    def call(self, method, path, **query):
        if self.failure:
            raise self.failure
        if path == "files":
            self.scans += 1
            return json.dumps(
                {"files": [value[1] for value in self.files.values()]}
            ).encode()
        self.downloads += 1
        for body, entry in self.files.values():
            if path == "files/" + entry["id"]:
                return body
        raise DriveMissing()

    def lookup(self, path):
        if path not in self.files:
            raise DriveMissing()
        return self.files[path][1]


class DisplayCacheTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.origin = Origin()
        self.path = "resource/images/card.png"
        self.origin.put(self.path, picture())
        self.now = 100.0
        self.cache = DisplayCache(
            self.origin, self.directory.name, ttl=10, clock=lambda: self.now
        )

    def test_warm_display_is_local_condensed_and_versioned(self):
        path, mime, key, state = self.cache.image(self.path, True)
        self.assertEqual((mime, state), ("image/webp", "miss"))
        with Image.open(path) as image:
            self.assertLessEqual(image.width, 480)
            self.assertLessEqual(image.height, 360)
        self.assertEqual(self.cache.image(self.path, True)[2:], (key, "hit"))
        self.assertEqual((self.origin.scans, self.origin.downloads), (1, 1))
        self.origin.put(self.path, picture("blue"), version="2")
        self.now += 11
        updated = self.cache.image(self.path, True)
        self.assertNotEqual(updated[2], key)
        with Image.open(updated[0]) as image:
            self.assertGreater(image.getpixel((0, 0))[2], 200)

    def test_known_cache_can_bridge_network_failure_but_never_permission_revocation(
        self,
    ):
        self.cache.image(self.path)
        self.now += 11
        self.origin.failure = DriveUnavailable("offline")
        self.assertEqual(self.cache.image(self.path)[3], "stale")
        self.now += 16
        denied = DriveUnavailable("revoked")
        denied.http_status = 403
        denied.reason = "insufficientPermissions"
        self.origin.failure = denied
        with self.assertRaises(DriveUnavailable):
            self.cache.image(self.path)

    def test_deleted_resources_and_unmapped_paths_do_not_serve_old_copies(self):
        self.cache.image(self.path)
        del self.origin.files[self.path]
        self.cache.invalidate(self.path)
        with self.assertRaises(DriveMissing):
            self.cache.image(self.path)
        with self.assertRaises(DriveMissing):
            self.cache.image("../app.db")

    def test_document_updates_are_immediate_and_callers_cannot_mutate_cached_values(
        self,
    ):
        path = "resource/topics.json"
        self.origin.put(path, b'{"name":"old"}', "application/json")
        value = self.cache.document(path)
        value["name"] = "changed"
        self.assertEqual(self.cache.document(path)["name"], "old")
        self.origin.put(path, b'{"name":"new"}', "application/json", "2")
        self.cache.invalidate(path)
        self.assertEqual(self.cache.document(path)["name"], "new")

    def test_source_checksum_mismatch_never_publishes_an_image(self):
        self.cache.refresh()
        body, entry = self.origin.files[self.path]
        self.origin.files[self.path] = (picture("blue"), entry)
        with self.assertRaises(DriveUnavailable):
            self.cache.image(self.path)
        self.assertFalse(list(Path(self.directory.name).rglob("*.blob")))

    def test_display_mapping_survives_restart_and_different_folders_are_isolated(self):
        first = self.cache.image(self.path)
        restarted = DisplayCache(
            self.origin, self.directory.name, ttl=10, clock=lambda: self.now
        )
        self.assertEqual(restarted.image(self.path)[2], first[2])
        self.assertEqual(self.origin.downloads, 1)
        other = Origin()
        other.folder = "another-folder"
        other.failure = DriveUnavailable("offline")
        isolated = DisplayCache(other, self.directory.name, clock=lambda: self.now)
        with self.assertRaises(DriveUnavailable):
            isolated.image(self.path)


class DisplayHTTPTests(ApplicationTest):
    def test_conditional_requests_serve_versioned_webp_from_the_server(self):
        origin = Origin()
        path = "resource/images/card.png"
        origin.put(path, picture())
        origin.view_cache = DisplayCache(
            origin, Path(self.directory.name) / "display-cache"
        )
        self.app.extensions["drive_store"] = origin
        first = self.client.get("/thumb/images/card.png")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.mimetype, "image/webp")
        self.assertEqual(first.headers["X-Resource-Cache"], "miss")
        second = self.client.get(
            "/thumb/images/card.png", headers={"If-None-Match": first.headers["ETag"]}
        )
        self.assertEqual(second.status_code, 304)
        self.assertEqual(origin.downloads, 1)
        self.assertIn("no-cache", first.headers["Cache-Control"])
        self.assertIn("private", first.headers["Cache-Control"])
        self.assertEqual(first.headers["CDN-Cache-Control"], "no-store")
        self.assertEqual(first.headers["Cloudflare-CDN-Cache-Control"], "no-store")

class CacheConcurrencyTests(unittest.TestCase):
    def test_simultaneous_cold_requests_download_the_original_only_once(self):
        from concurrent.futures import ThreadPoolExecutor
        with tempfile.TemporaryDirectory() as directory:
            origin=Origin();path='resource/images/concurrent.png';origin.put(path,picture())
            cache=DisplayCache(origin,directory)
            with ThreadPoolExecutor(max_workers=4) as pool:
                results=list(pool.map(lambda _:cache.image(path,True),range(8)))
            self.assertEqual(origin.downloads,1)
            self.assertEqual(len({r[2] for r in results}),1)

    def test_revocation_during_download_invalidates_persisted_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            origin=Origin();path='resource/images/a.png';origin.put(path,picture());cache=DisplayCache(origin,directory)
            cache.refresh();denied=DriveUnavailable('permission denied');denied.http_status=403;origin.failure=denied
            with self.assertRaises(DriveUnavailable):cache.image(path)
            self.assertFalse((cache.root/'index.json').exists())
            restarted=DisplayCache(origin,directory)
            with self.assertRaises(DriveUnavailable):restarted.image(path)
