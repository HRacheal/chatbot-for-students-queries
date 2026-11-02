"""Permitted, in-memory access to official USIU-Africa web pages.

Rules enforced here for every request:

* Only https URLs on an exactly listed trusted host (``TRUSTED_SOURCE_HOSTS``, default
  ``www.usiu.ac.ke``). Subdomains are *not* trusted automatically, and portal or
  login hosts and paths are always refused, so student records are never reached.
* robots.txt is read for the configured user agent before any page is fetched. If
  robots.txt cannot be read, nothing is fetched. A disallowed page is never fetched.
* Redirects are followed manually and each hop is checked again (host and robots.txt).
* Only HTML is accepted, with a byte limit and short connect/read timeouts.
* Page text is kept only in a bounded in-memory cache with expiry. Nothing is
  written to disk. Page text is untrusted data.
"""

import datetime
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

from services.page_text import extract_html

logger = logging.getLogger(__name__)

# Hosts and paths that are never fetched, whatever the configuration says.
DENIED_HOSTS = frozenset({"cx.usiu.ac.ke", "portal.usiu.ac.ke", "elearning.usiu.ac.ke",
                          "blackboard.usiu.ac.ke", "mail.usiu.ac.ke", "erp.usiu.ac.ke"})
DENIED_PATH_WORDS = ("login", "signin", "sign-in", "logon", "wp-admin", "wp-login", "portal",
                     "my-account", "student-records", "cgi-bin")
DENIED_PATH_PREFIXES = ("/ics/", "/ics?", "/wp-json/")

# Result statuses
OK = "ok"
NOT_TRUSTED = "not_trusted"
ROBOTS_DISALLOWED = "robots_disallowed"
ROBOTS_UNAVAILABLE = "robots_unavailable"
TIMEOUT = "timeout"
UNREACHABLE = "unreachable"
HTTP_ERROR = "http_error"
NOT_HTML = "not_html"
TOO_LARGE = "too_large"
NO_TEXT = "no_text"
BAD_REDIRECT = "bad_redirect"


class FetchError(Exception):
    def __init__(self, status, detail=""):
        super().__init__(detail or status)
        self.status = status
        self.detail = detail


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


@dataclass
class Page:
    url: str            # URL that was requested
    final_url: str      # URL the text actually came from (after redirects)
    title: str
    text: str
    published: str      # date from the page's metadata, or ""
    fetched_at: datetime.datetime = field(default_factory=utcnow)
    etag: str = ""
    last_modified: str = ""


@dataclass
class FetchResult:
    status: str
    url: str
    page: Page = None
    detail: str = ""

    @property
    def ok(self):
        return self.status == OK


class TTLCache:
    """Thread-safe in-memory cache with per-entry expiry and entry/byte limits (LRU eviction)."""

    def __init__(self, max_entries=200, max_bytes=20 * 1024 * 1024, clock=time.monotonic):
        self.max_entries = max_entries
        self.max_bytes = max_bytes
        self.clock = clock
        self._data = OrderedDict()  # key -> (expires_at, size, value)
        self._bytes = 0
        self._lock = threading.Lock()

    def get(self, key, include_expired=False):
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires_at, _, value = item
            if expires_at <= self.clock():
                return value if include_expired else None
            self._data.move_to_end(key)
            return value

    def set(self, key, value, ttl, size=1):
        if size > self.max_bytes:
            return
        with self._lock:
            old = self._data.pop(key, None)
            if old:
                self._bytes -= old[1]
            self._data[key] = (self.clock() + ttl, size, value)
            self._bytes += size
            while self._data and (len(self._data) > self.max_entries or self._bytes > self.max_bytes):
                _, (_, old_size, _) = self._data.popitem(last=False)
                self._bytes -= old_size

    def __len__(self):
        return len(self._data)

    @property
    def size_bytes(self):
        return self._bytes

    def clear(self):
        with self._lock:
            self._data.clear()
            self._bytes = 0


def trusted_hosts_from(settings):
    return frozenset(h.strip().lower() for h in settings.get("TRUSTED_SOURCE_HOSTS", ("www.usiu.ac.ke",)) if h.strip())


def check_trusted_hosts(hosts):
    """Configuration problems with a trusted-host list (used by ``validate_config``)."""
    problems = []
    for host in hosts:
        if "*" in host or "/" in host or ":" in host or " " in host:
            problems.append(f"TRUSTED_SOURCE_HOSTS entry '{host}' must be an exact host name.")
        elif host.lower() in DENIED_HOSTS:
            problems.append(f"TRUSTED_SOURCE_HOSTS must not include the portal host '{host}'.")
        elif not host.lower().endswith(".usiu.ac.ke") and host.lower() != "usiu.ac.ke":
            problems.append(f"TRUSTED_SOURCE_HOSTS entry '{host}' is not an official usiu.ac.ke host.")
    return problems


def is_trusted_url(url, trusted_hosts):
    """https, exact trusted host, default port, no credentials, no portal/login path."""
    if not isinstance(url, str) or len(url) > 2048:
        return False
    try:
        parts = urlsplit(url.strip())
        port = parts.port
    except ValueError:
        return False
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or port not in (None, 443) or parts.username or parts.password:
        return False
    if host in DENIED_HOSTS or host not in trusted_hosts:
        return False
    path = (parts.path or "/").lower() + ("?" + parts.query.lower() if parts.query else "")
    if any(word in path for word in DENIED_PATH_WORDS) or (path + "/").startswith(DENIED_PATH_PREFIXES):
        return False
    # Site search result pages are not content pages (and are disallowed for robots anyway).
    if parts.query and any(q.split("=")[0] in ("s", "q", "search") for q in parts.query.split("&")):
        return False
    return True


class RequestsTransport:
    """Thin wrapper over ``requests`` so tests can substitute a fake transport."""

    def __init__(self, user_agent):
        import requests

        self._requests = requests
        self.session = requests.Session()
        self.session.headers["User-Agent"] = user_agent
        self.session.headers["Accept"] = "text/html,application/xhtml+xml;q=0.9,text/plain;q=0.5"

    def get(self, url, headers=None, timeout=(5, 10), max_bytes=2_000_000):
        """Return ``(status, headers_dict, body_bytes)``. Raises FetchError on network problems."""
        requests = self._requests
        try:
            with self.session.get(url, headers=headers or {}, timeout=timeout,
                                  allow_redirects=False, stream=True) as response:
                body, total = [], 0
                for chunk in response.iter_content(65536):
                    total += len(chunk)
                    if total > max_bytes:
                        raise FetchError(TOO_LARGE, "response exceeds the size limit")
                    body.append(chunk)
                return response.status_code, {k.lower(): v for k, v in response.headers.items()}, b"".join(body)
        except requests.exceptions.Timeout as e:
            raise FetchError(TIMEOUT, type(e).__name__) from e
        except requests.exceptions.RequestException as e:
            raise FetchError(UNREACHABLE, type(e).__name__) from e


class WebsiteAccess:
    """Fetch permitted pages from trusted official hosts, with caching and robots.txt checks."""

    MAX_REDIRECTS = 3

    def __init__(self, settings, transport=None, clock=time.monotonic):
        self.settings = settings
        self.user_agent = settings.get("LIVE_USER_AGENT", "USIUBOT/1.0")
        self.robots_agent = self.user_agent.split("/")[0]
        self.trusted_hosts = trusted_hosts_from(settings)
        self.timeout = (settings.get("LIVE_CONNECT_TIMEOUT", 5), settings.get("LIVE_READ_TIMEOUT", 10))
        self.max_bytes = settings.get("LIVE_MAX_PAGE_BYTES", 2_000_000)
        self.page_ttl = settings.get("LIVE_PAGE_CACHE_SECONDS", 86400)
        self.robots_ttl = settings.get("LIVE_ROBOTS_CACHE_SECONDS", 86400)
        self.failure_ttl = settings.get("LIVE_FAILURE_CACHE_SECONDS", 900)
        self._transport = transport
        self.clock = clock
        self.pages = TTLCache(settings.get("LIVE_CACHE_MAX_PAGES", 200),
                              settings.get("LIVE_CACHE_MAX_MB", 20) * 1024 * 1024, clock)
        self.failures = TTLCache(1000, 10 * 1024 * 1024, clock)
        self.robots = TTLCache(50, 5 * 1024 * 1024, clock)

    @property
    def transport(self):
        if self._transport is None:
            self._transport = RequestsTransport(self.user_agent)
        return self._transport

    def is_trusted(self, url):
        return is_trusted_url(url, self.trusted_hosts)

    # --- robots.txt -----------------------------------------------------------------
    def robots_status(self, url):
        """Return ``(allowed, status)`` for ``url`` under the host's robots.txt."""
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        entry = self.robots.get(origin)
        if entry is None:
            entry = self._load_robots(origin)
        kind, parser = entry
        if kind == "unavailable":
            return False, ROBOTS_UNAVAILABLE
        if kind == "allow_all":
            return True, OK
        if kind == "deny_all":
            return False, ROBOTS_DISALLOWED
        allowed = parser.can_fetch(self.robots_agent, url) and parser.can_fetch(self.user_agent, url)
        return allowed, OK if allowed else ROBOTS_DISALLOWED

    def _load_robots(self, origin):
        try:
            status, _, body = self.transport.get(origin + "/robots.txt", timeout=self.timeout,
                                                 max_bytes=500_000)
        except FetchError as e:
            logger.info("robots.txt for %s unavailable (%s)", origin, e.status)
            entry = ("unavailable", None)
            self.robots.set(origin, entry, self.failure_ttl, 1)
            return entry
        if status == 200:
            parser = RobotFileParser()
            parser.parse(body.decode("utf-8", errors="replace").splitlines())
            entry = ("rules", parser)
        elif status in (401, 403):
            entry = ("deny_all", None)       # access-controlled robots.txt: treat as "keep out"
        elif 400 <= status < 500:
            entry = ("allow_all", None)      # no robots.txt (RFC 9309)
        else:
            entry = ("unavailable", None)    # server error: do not crawl
        ttl = self.failure_ttl if entry[0] == "unavailable" else self.robots_ttl
        self.robots.set(origin, entry, ttl, len(body) + 1)
        return entry

    # --- pages ------------------------------------------------------------------------
    def fetch_page(self, url):
        """Fetch one page. Never raises; returns a ``FetchResult``."""
        if not self.is_trusted(url):
            return FetchResult(NOT_TRUSTED, url)
        cached = self.pages.get(url)
        if cached is not None:
            return FetchResult(OK, url, cached)
        failure = self.failures.get(url)
        if failure is not None:
            return failure
        stale = self.pages.get(url, include_expired=True)
        try:
            page = self._fetch(url, stale)
        except FetchError as e:
            result = FetchResult(e.status, url, detail=e.detail)
            if e.status not in (NOT_TRUSTED, ROBOTS_DISALLOWED):
                self.failures.set(url, result, self.failure_ttl, 1)
            logger.info("Page not retrieved (%s): %s", e.status, url)
            return result
        self.pages.set(url, page, self.page_ttl, len(page.text.encode("utf-8")) + 512)
        return FetchResult(OK, url, page)

    def _fetch(self, url, stale=None):
        current = url
        for _ in range(self.MAX_REDIRECTS + 1):
            if not self.is_trusted(current):
                raise FetchError(BAD_REDIRECT if current != url else NOT_TRUSTED, "redirect left the trusted hosts")
            allowed, status = self.robots_status(current)
            if not allowed:
                raise FetchError(status)
            headers = {}
            if stale is not None and current == url:
                if stale.etag:
                    headers["If-None-Match"] = stale.etag
                if stale.last_modified:
                    headers["If-Modified-Since"] = stale.last_modified
            code, response_headers, body = self.transport.get(current, headers=headers, timeout=self.timeout,
                                                              max_bytes=self.max_bytes)
            if code in (301, 302, 303, 307, 308):
                location = response_headers.get("location")
                if not location:
                    raise FetchError(HTTP_ERROR, f"HTTP {code} without location")
                current = urljoin(current, location)
                continue
            if code == 304 and stale is not None:
                return Page(url, stale.final_url, stale.title, stale.text, stale.published, utcnow(),
                            stale.etag, stale.last_modified)
            if code != 200:
                raise FetchError(HTTP_ERROR, f"HTTP {code}")
            content_type = response_headers.get("content-type", "").split(";")[0].strip().lower()
            if content_type not in ("text/html", "application/xhtml+xml"):
                raise FetchError(NOT_HTML, content_type or "no content type")
            text, title, published = extract_html(body)
            if len(text.strip()) < 50:
                raise FetchError(NO_TEXT, "page has no readable text")
            return Page(url, current, title, text, published, utcnow(),
                        response_headers.get("etag", ""), response_headers.get("last-modified", ""))
        raise FetchError(BAD_REDIRECT, "too many redirects")

    def cache_info(self):
        return {"pages": len(self.pages), "bytes": self.pages.size_bytes, "failures": len(self.failures)}
