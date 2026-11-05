"""Versioned, bounded display copies. Google Drive remains the source of truth."""

import copy
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import time
from urllib.parse import quote

from PIL import Image, ImageOps
from drive_store import DriveMissing, DriveUnavailable, MAX_IMAGE, valid_path


class DisplayCache:
    def __init__(
        self, source, root, max_bytes=256 * 1024 * 1024, ttl=60, clock=time.time
    ):
        self.source = source
        self.root = Path(root) / hashlib.sha256(source.folder.encode()).hexdigest()[:20]
        self.max_bytes = max(1024 * 1024, int(max_bytes))
        self.ttl = max(1, int(ttl))
        self.clock = clock
        self._index = {}
        self._checked = 0
        self._retry = 0
        self._invalid = set()
        self._lock = threading.RLock()
        self._render = threading.Lock()
        self._documents = {}
        self.hits = 0
        self.misses = 0
        self._writes = 0
        self._bytes = 0
        if self.root.exists():
            self._bytes = sum(p.stat().st_size for p in self.root.glob("*.blob"))
            try:
                saved = json.loads((self.root / "index.json").read_text())
                if (
                    saved["folder"] == source.folder
                    and self.clock() - saved["checked"] < 3600
                ):
                    self._index = saved["entries"]
                    self._checked = saved["checked"]
            except (OSError, ValueError, KeyError, TypeError):
                pass

    def _atomic(self, path, body):
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, name = tempfile.mkstemp(dir=self.root, prefix=".writing-")
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(body)
                stream.flush()
            os.replace(name, path)
        finally:
            try:
                os.unlink(name)
            except FileNotFoundError:
                pass

    def invalidate(self, path):
        with self._lock:
            self._invalid.add(path)

    def refresh(self, force=False):
        with self._lock:
            now = self.clock()
            if not force and self._checked and now - self._checked < self.ttl:
                return False
            if not force and now < self._retry:
                if self._index and now - self._checked < 3600:
                    return True
                raise DriveUnavailable("Thư viện đang mất kết nối; hãy thử lại sau")
            try:
                entries = {}
                page = ""
                query = (
                    "trashed=false and ('"
                    + self.source.folder
                    + "' in parents or appProperties has { key='gotRoot' and value='"
                    + self.source.folder
                    + "' })"
                )
                while True:
                    data = json.loads(
                        self.source.call(
                            "GET",
                            "files",
                            q=query,
                            pageSize=1000,
                            pageToken=page,
                            request_timeout=12,
                            fields="nextPageToken,files(id,mimeType,version,size,md5Checksum,sha256Checksum,appProperties)",
                        )
                    )
                    for entry in data.get("files", []):
                        fingerprint = entry.get("appProperties", {}).get("gotPathHash")
                        if not fingerprint:
                            continue
                        if fingerprint in entries:
                            error = DriveUnavailable("Duplicate Drive resource path")
                            error.code = "duplicate-resource"
                            raise error
                        entries[fingerprint] = entry
                    page = data.get("nextPageToken")
                    if not page:
                        break
                self._index = entries
                self._checked = now
                self._retry = 0
                self._invalid.clear()
                self._atomic(
                    self.root / "index.json",
                    json.dumps(
                        {
                            "folder": self.source.folder,
                            "checked": now,
                            "entries": entries,
                        }
                    ).encode(),
                )
                return False
            except DriveUnavailable as error:
                quota = getattr(error, "reason", "") in (
                    "rateLimitExceeded",
                    "userRateLimitExceeded",
                    "dailyLimitExceeded",
                )
                denied = (
                    getattr(error, "http_status", None) in (401, 403, 404) and not quota
                )
                if denied or getattr(error, "code", None) == "duplicate-resource":
                    self._index = {}
                    self._checked = 0
                    self._retry = now + 15
                    (self.root / "index.json").unlink(missing_ok=True)
                    raise
                self._retry = now + 15
                if self._index and now - self._checked < 3600:
                    return True
                raise

    def lookup(self, path):
        if not valid_path(path):
            raise DriveMissing()
        stale = self.refresh()
        fingerprint = hashlib.sha256(path.encode()).hexdigest()
        with self._lock:
            if path in self._invalid:
                try:
                    self._index[fingerprint] = self.source.lookup(path)
                except DriveMissing:
                    self._index.pop(fingerprint, None)
                    self._invalid.discard(path)
                    raise
                self._invalid.discard(path)
                stale = False
            entry = self._index.get(fingerprint)
            if not entry:
                raise DriveMissing()
            return entry, stale

    def _body(self, entry):
        try:
            body = self.source.call(
                "GET", "files/" + quote(entry["id"], safe=""), alt="media"
            )
        except DriveMissing:
            self._checked = 0
            raise
        except DriveUnavailable as error:
            if getattr(error, "http_status", None) in (401, 403) and getattr(
                error, "reason", ""
            ) not in (
                "rateLimitExceeded",
                "userRateLimitExceeded",
                "dailyLimitExceeded",
            ):
                with self._lock:
                    self._index = {}
                    self._checked = 0
                    (self.root / "index.json").unlink(missing_ok=True)
            raise
        digest = entry.get("sha256Checksum") or entry.get("md5Checksum")
        if digest:
            actual = (
                hashlib.sha256(body).hexdigest()
                if entry.get("sha256Checksum")
                else hashlib.md5(body).hexdigest()
            )
            if actual != digest:
                self._checked = 0
                raise DriveUnavailable(
                    "Drive resource changed while downloading; retry to get the new version"
                )
        return body

    def document(self, path):
        entry, stale = self.lookup(path)
        key = (entry["id"], str(entry.get("version", "")), entry.get("md5Checksum", ""))
        with self._lock:
            if key in self._documents:
                return copy.deepcopy(self._documents[key])
        if stale:
            raise DriveUnavailable("Tài liệu chưa có bản hiển thị; cần kết nối Drive")
        try:
            value = json.loads(self._body(entry))
            if not isinstance(value, dict):
                raise ValueError()
        except (ValueError, UnicodeError):
            raise DriveUnavailable("Invalid Drive resource document") from None
        with self._lock:
            if len(self._documents) >= 64:
                self._documents.pop(next(iter(self._documents)))
            self._documents[key] = value
        return copy.deepcopy(value)

    def _prune(self):
        files = []
        for path in self.root.glob("*.blob"):
            try:
                info = path.stat()
                files.append((info.st_mtime, path, info.st_size))
            except FileNotFoundError:
                pass
        total = sum(size for _, _, size in files)
        for _, path, size in sorted(files):
            if total <= self.max_bytes:
                break
            try:
                path.unlink()
                total -= size
            except FileNotFoundError:
                pass
            path.with_suffix(".json").unlink(missing_ok=True)
        self._bytes = total

    def image(self, path, thumbnail=False):
        entry, stale = self.lookup(path)
        if not entry.get("mimeType", "").startswith("image/"):
            raise DriveMissing()
        identity = json.dumps(
            [
                self.source.folder,
                path,
                entry["id"],
                entry.get("version"),
                entry.get("md5Checksum"),
                entry.get("sha256Checksum"),
                "thumb-480" if thumbnail else "display-1280",
                "renderer-1",
            ]
        )
        key = hashlib.sha256(identity.encode()).hexdigest()
        output = self.root / (key + ".blob")
        metadata = output.with_suffix(".json")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with open(self.root / (key + ".lock"), "a") as lease:
            fcntl.flock(lease, fcntl.LOCK_EX)
            try:
                info = json.loads(metadata.read_text())
                if info["mime"] not in (
                    "image/webp",
                    "image/jpeg",
                    "image/png",
                    "image/gif",
                    "image/svg+xml",
                ):
                    raise ValueError()
                if output.is_symlink() or not output.is_file():
                    raise ValueError()
                if output.stat().st_size != info.get("bytes"):
                    raise ValueError()
                self.hits += 1
                if self.clock() - output.stat().st_mtime > 60:
                    os.utime(output, None)
                return output, info["mime"], key, "stale" if stale else "hit"
            except (OSError, ValueError, KeyError):
                pass
            if stale:
                raise DriveUnavailable("Ảnh này chưa được tải; cần kết nối Drive")
            with self._render:
                body = self._body(entry)
                mime = entry.get("mimeType", "image/webp")
                if len(body) > MAX_IMAGE:
                    raise DriveUnavailable("Image exceeds display memory limit")
                if mime != "image/svg+xml":
                    try:
                        with Image.open(io.BytesIO(body)) as original:
                            if original.width * original.height > 16_000_000:
                                raise ValueError("Image dimensions exceed limit")
                            if thumbnail or not getattr(original, "is_animated", False):
                                image = ImageOps.exif_transpose(original)
                                image.thumbnail(
                                    (480, 360) if thumbnail else (1280, 1280),
                                    Image.Resampling.LANCZOS,
                                )
                                if image.mode not in ("RGB", "RGBA"):
                                    image = image.convert(
                                        "RGBA"
                                        if "transparency" in image.info
                                        else "RGB"
                                    )
                                result = io.BytesIO()
                                image.save(
                                    result,
                                    "WEBP",
                                    quality=78 if thumbnail else 84,
                                    method=4,
                                )
                                body = result.getvalue()
                                mime = "image/webp"
                    except (OSError, ValueError, Image.DecompressionBombError):
                        raise DriveUnavailable(
                            "Invalid or oversized Drive image"
                        ) from None
                previous_size = output.stat().st_size if output.exists() else 0
                self._atomic(output, body)
                self._atomic(
                    metadata,
                    json.dumps(
                        {
                            "mime": mime,
                            "sourceVersion": entry.get("version"),
                            "bytes": len(body),
                        }
                    ).encode(),
                )
                self._bytes += len(body) - previous_size
                self._writes += 1
                self.misses += 1
                if self._bytes > self.max_bytes or self._writes % 32 == 0:
                    self._prune()
                if not output.exists():
                    raise DriveUnavailable("Image exceeds configured cache budget")
                return output, mime, key, "miss"

    def status(self):
        with self._lock:
            return {
                "enabled": True,
                "source": "google-drive",
                "hits": self.hits,
                "misses": self.misses,
                "maxBytes": self.max_bytes,
                "bytes": self._bytes,
                "indexedResources": len(self._index),
                "checkIntervalSeconds": self.ttl,
            }
