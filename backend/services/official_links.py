"""Official fallback links managed by administrators.

The page catalogue (``config/official_pages.json``) is the starting list. Administrators
can add pages, correct titles, departments and keywords, mark a page as reviewed, or hide
it; those changes are stored in the ``official_links`` MongoDB collection and override
the file, so nothing is lost when the file is updated and no config file is written at
runtime. Links are metadata only: a link is never evidence for an answer.

``ManagedCatalogue`` has the same interface as ``OfficialPageCatalogue`` (``match``,
``entries``, ``reviewed_count``), so the chat, live-retrieval and guidance services use
it unchanged. It is rebuilt when an administrator saves a change and at most every
``ttl`` seconds otherwise (for other server processes).
"""

import datetime
import json
import logging
import threading
import time
from urllib.parse import urlsplit, urlunsplit

from services.live_retrieval import OfficialPageCatalogue
from services.sources import DEPARTMENTS

logger = logging.getLogger(__name__)

MAX_TITLE = 300
MAX_KEYWORDS = 30
MAX_KEYWORD = 60
MAX_NOTE = 500


class LinkError(ValueError):
    """Invalid link data. The message is safe to show to administrators."""


def link_key(url):
    parts = urlsplit(url.strip())
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, ""))


def _read_file(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        logger.warning("Official page catalogue not found: %s", path)
        return []
    except (OSError, ValueError) as e:
        logger.error("Official page catalogue could not be read (%s)", type(e).__name__)
        return []
    pages = data.get("pages", []) if isinstance(data, dict) else []
    return [p for p in pages if isinstance(p, dict) and isinstance(p.get("url"), str)]


class ManagedCatalogue:
    def __init__(self, db_getter, path, is_trusted, ttl=30):
        self._db = db_getter
        self.path = path
        self.is_trusted = is_trusted
        self.ttl = ttl
        self._file_pages = _read_file(path)
        self._lock = threading.Lock()
        self._built = None
        self._built_at = 0.0

    @property
    def collection(self):
        return self._db("official_links")

    # --- merged view -------------------------------------------------------------------
    def _overrides(self):
        try:
            return {d["key"]: d for d in self.collection.find({}, {"_id": 0})}
        except Exception as e:  # database unavailable: fall back to the file
            logger.error("Official link overrides could not be read (%s)", type(e).__name__)
            return {}

    def merged(self, include_hidden=False):
        """File pages with administrator changes applied; each entry says where it came from."""
        overrides = self._overrides()
        pages, seen = [], set()
        for page in self._file_pages:
            key = link_key(page["url"])
            if key in seen:
                continue
            seen.add(key)
            override = overrides.get(key)
            entry = {"url": page["url"], "title": page.get("title", ""), "department": page.get("department"),
                     "keywords": list(page.get("keywords", [])), "reviewed": page.get("reviewed") is True,
                     "hidden": False, "notes": list(page.get("notes", [])), "origin": "file"}
            if override:
                entry.update({k: override[k] for k in ("title", "department", "keywords", "reviewed", "hidden")
                              if k in override})
                entry.update(origin="file+admin", updated_at=override.get("updated_at"),
                             updated_by=override.get("updated_by"), admin_note=override.get("note", ""))
            pages.append(entry)
        for key, override in overrides.items():
            if key not in seen:
                pages.append({"url": override["url"], "title": override.get("title", ""),
                              "department": override.get("department"), "keywords": override.get("keywords", []),
                              "reviewed": override.get("reviewed") is True, "hidden": override.get("hidden") is True,
                              "notes": [], "origin": "admin", "updated_at": override.get("updated_at"),
                              "updated_by": override.get("updated_by"), "admin_note": override.get("note", "")})
        for entry in pages:
            entry["trusted"] = bool(self.is_trusted(entry["url"]))
        return pages if include_hidden else [p for p in pages if not p["hidden"]]

    def current(self):
        with self._lock:
            if self._built is None or time.monotonic() - self._built_at > self.ttl:
                self._built = OfficialPageCatalogue(self.merged(), self.is_trusted)
                self._built_at = time.monotonic()
            return self._built

    def invalidate(self):
        with self._lock:
            self._built = None

    # Same interface as OfficialPageCatalogue
    def match(self, *args, **kwargs):
        return self.current().match(*args, **kwargs)

    @property
    def entries(self):
        return self.current().entries

    @property
    def reviewed_count(self):
        return self.current().reviewed_count

    # --- administration ----------------------------------------------------------------
    def save(self, data, actor="admin"):
        """Add a page or change one (title, department, keywords, reviewed, hidden)."""
        if not isinstance(data, dict):
            raise LinkError("Expected a JSON object")
        url = data.get("url")
        if not isinstance(url, str) or not self.is_trusted(url.strip()):
            raise LinkError("The URL must be an https page on a trusted official USIU-Africa host "
                            "(no portal, login or search pages)")
        url = url.strip()
        key = link_key(url)
        existing = next((p for p in self.merged(include_hidden=True) if link_key(p["url"]) == key), None)
        title = data.get("title", existing["title"] if existing else None)
        if not isinstance(title, str) or not title.strip() or len(title.strip()) > MAX_TITLE:
            raise LinkError(f"Title is required (at most {MAX_TITLE} characters)")
        department = data.get("department", existing["department"] if existing else None)
        if department not in DEPARTMENTS:
            raise LinkError("Department must be one of: " + ", ".join(DEPARTMENTS))
        keywords = data.get("keywords", existing["keywords"] if existing else [])
        if isinstance(keywords, str):
            keywords = [k for k in (part.strip() for part in keywords.split(",")) if k]
        if not isinstance(keywords, list) or len(keywords) > MAX_KEYWORDS or \
                not all(isinstance(k, str) and 0 < len(k.strip()) <= MAX_KEYWORD for k in keywords):
            raise LinkError(f"Keywords must be at most {MAX_KEYWORDS} short words or phrases")
        flags = {}
        for flag in ("reviewed", "hidden"):
            value = data.get(flag, existing[flag] if existing else False)
            if not isinstance(value, bool):
                raise LinkError(f"'{flag}' must be true or false")
            flags[flag] = value
        note = data.get("note") or ""
        if not isinstance(note, str) or len(note) > MAX_NOTE:
            raise LinkError(f"Note must be text of at most {MAX_NOTE} characters")
        doc = {"key": key, "url": existing["url"] if existing else url, "title": " ".join(title.split()),
               "department": department, "keywords": [" ".join(k.split()) for k in keywords], **flags,
               "note": note.strip(), "updated_at": datetime.datetime.now(datetime.timezone.utc), "updated_by": actor}
        self.collection.update_one({"key": key}, {"$set": doc}, upsert=True)
        self.invalidate()
        logger.info("Official link %s by %s (reviewed=%s, hidden=%s)", "updated" if existing else "added",
                    actor, flags["reviewed"], flags["hidden"])
        return next(p for p in self.merged(include_hidden=True) if link_key(p["url"]) == key)
