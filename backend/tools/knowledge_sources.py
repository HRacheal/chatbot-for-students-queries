"""Discover, download, extract and import official USIU-Africa knowledge sources.

Files and extracted text live in the local folder ``backend/resources/usiubot_knowledge``
(git-ignored except for metadata and reports). The tool never uploads to Cloudinary,
never writes to Pinecone and never approves anything: ``import-registry`` creates
*draft* sources in the source registry, which an administrator must review and
approve before the chatbot can use them.

Rules enforced in code:
* robots.txt is fetched first and obeyed for this tool's user agent. If it
  cannot be read, nothing is downloaded.
* Only https://www.usiu.ac.ke is fetched. Links to other USIU subdomains or
  other websites are recorded for manual review, never fetched.
* Requests are rate limited and size limited; PDFs must really be PDFs and
  web pages must really be HTML.
* Application and other forms are never downloaded or imported as knowledge.
* Duplicates (same URL, same canonical URL, same file content or same text) are never
  stored or imported twice.
* Failures are recorded with a precise status (robots_disallowed, access_denied,
  login_required, timeout, server_error, not_found, empty_content, invalid_file, ...);
  only transient failures (timeouts, server errors, connection errors) are retried, at
  most ``MAX_ATTEMPTS`` times per run. Nothing is invented.
* A source whose content is not collected keeps its official URL and is marked
  ``link_only``: ``sync-links`` adds it to the chatbot's official page catalogue
  (``config/official_pages.json``, unreviewed), so users are sent to the real page.
* Stored content is never replaced by a failed, empty or unreviewed retrieval.

Usage (from the backend folder):
    python -m tools.knowledge_sources init
    python -m tools.knowledge_sources import-seeds resources/usiubot_knowledge/metadata/search_discovery_seeds.json
    python -m tools.knowledge_sources download
    python -m tools.knowledge_sources register path/to/saved-page.html --category admissions \
        --url https://www.usiu.ac.ke/... --title "Official title" --retrieved 2026-10-21
    python -m tools.knowledge_sources extract
    python -m tools.knowledge_sources import-registry   # needs the backend .env (MongoDB)
    python -m tools.knowledge_sources sync-links        # official links -> config/official_pages.json
    python -m tools.knowledge_sources archive https://www.usiu.ac.ke/... --reason "superseded"
    python -m tools.knowledge_sources report
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import sys
import time
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

from services.page_text import PageTextParser, _iso_date, extract_html, extract_html_details  # noqa: F401
from services.web_access import DENIED_HOSTS, is_trusted_url

KNOWLEDGE_ROOT = Path(__file__).resolve().parent.parent / "resources" / "usiubot_knowledge"
CATEGORIES = (
    "admissions",
    "registrar",
    "marketing",
    "academic_programmes",
    "general_university",
    "pending_review",
)
METADATA_DIR = "metadata"
INVENTORY_FILE = "source_inventory.json"
REPORT_FILE = "SOURCE_REPORT.md"
IMPORT_REPORT_FILE = "IMPORT_REPORT.md"
ACCESS_CHECK_FILE = "access_check.txt"
# Inventory category -> source registry department (pending_review has none yet).
DEPARTMENT_FOR_CATEGORY = {c: c for c in CATEGORIES if c != "pending_review"}
CATALOGUE_FILE = Path(__file__).resolve().parent.parent / "config" / "official_pages.json"

OFFICIAL_HOST = "www.usiu.ac.ke"
OFFICIAL_SITE = f"https://{OFFICIAL_HOST}"
USER_AGENT = "USIUBOT-SourceDiscovery/0.1 (student project; manual review before use)"
MAX_PDF_BYTES = 50 * 1024 * 1024
MIN_SECONDS_BETWEEN_REQUESTS = 5.0
REQUEST_TIMEOUT = (10, 30)  # (connect, read) seconds
MAX_ATTEMPTS = 2  # per source and run; only transient failures are retried
RETRY_DELAY_SECONDS = 15.0
MAX_ERRORS_KEPT = 5
MIN_PAGE_TEXT_CHARS = 50  # less readable text than this = an empty page
STALE_DAYS = 365

# Collection statuses (``download_status``). Review status is kept separately.
DISCOVERED = "discovered"
DOWNLOADED = "downloaded"
DUPLICATE = "duplicate"
ROBOTS_DISALLOWED = "robots_disallowed"
BLOCKED_ROBOTS = ROBOTS_DISALLOWED  # older name
UNREACHABLE = "site_unreachable"
ACCESS_DENIED = "access_denied"
LOGIN_REQUIRED = "login_required"
TIMEOUT = "timeout"
SERVER_ERROR = "server_error"
NOT_FOUND = "not_found"
EMPTY_CONTENT = "empty_content"
INVALID_FILE = "invalid_file"
NOT_OFFICIAL = "not_fetched_other_domain"
FAILED = "failed"
NOT_APPLICABLE = "not_applicable_html"  # older inventories: HTML pages were not downloaded
SKIPPED_FORM = "skipped_form"
MANUAL = "registered_manually"
ARCHIVED = "archived"
LEGACY_STATUSES = {"blocked_by_robots_txt": ROBOTS_DISALLOWED}
RETRYABLE = (DISCOVERED, FAILED, ROBOTS_DISALLOWED, UNREACHABLE, NOT_APPLICABLE, SKIPPED_FORM, ACCESS_DENIED,
             LOGIN_REQUIRED, TIMEOUT, SERVER_ERROR, NOT_FOUND, EMPTY_CONTENT, INVALID_FILE)
TRANSIENT = (TIMEOUT, SERVER_ERROR, UNREACHABLE)
# Not offered as links: the page is gone, withdrawn, or its content exists under another URL.
NOT_LINKABLE = (NOT_FOUND, ARCHIVED, DUPLICATE)

# Extraction statuses
EXTRACTED = "extracted"
NO_TEXT = "no_text"  # e.g. a scanned PDF
EXTRACTION_FAILED = "extraction_failed"

# Review flags (an administrator must look at these before approving)
FLAG_UNDATED = "undated"
FLAG_OUTDATED = "possibly_outdated"
FLAG_DUPLICATE = "duplicate_content"
FLAG_FORM = "personal_data_form"
FLAG_EXTRACTION = "extraction_problem"
FLAG_INSTRUCTIONS = "suspicious_instructions"
FLAG_DATE_FROM_METADATA = "date_from_file_metadata"
# Flagged items that are never imported into the source registry.
NOT_IMPORTABLE_FLAGS = (FLAG_FORM, FLAG_DUPLICATE)

# Registry import results
REG_CREATED = "draft_created"
REG_UPDATED = "draft_updated"
REG_UNCHANGED = "unchanged"
REG_SKIPPED = "skipped"


def today():
    return datetime.date.today().isoformat()


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def normalize_url(url):
    """Canonical form used for duplicate detection (no fragment, lower-case host)."""
    parts = urlsplit(url.strip())
    path = parts.path or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def host_of(url):
    return urlsplit(url).netloc.lower()


def is_official_host(url):
    return urlsplit(url).scheme.lower() == "https" and host_of(url) == OFFICIAL_HOST


def is_collectable_url(url):
    """An https page on the official host that is not a portal, login or search URL."""
    return is_official_host(url) and is_trusted_url(url, frozenset({OFFICIAL_HOST}))


def is_usiu_domain(url):
    host = host_of(url)
    return host == "usiu.ac.ke" or host.endswith(".usiu.ac.ke")


def safe_filename(url, fallback="document.pdf", extension=".pdf"):
    """Original file name from the URL (or a web page's last path segment), reduced to safe characters."""
    path = urlsplit(url).path
    if extension != ".pdf":
        path = path.rstrip("/")  # "/how-to-apply/" -> "how-to-apply.html"
    name = unquote(os.path.basename(path)) or fallback
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._") or fallback
    if not name.lower().endswith(extension):
        name += extension
    return name[:150]


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


@dataclass
class Source:
    title: str
    url: str
    content_type: str  # "pdf", "html" or "unknown"
    category: str
    discovered_on: str = field(default_factory=today)
    discovered_via: str = ""
    found_on_page: str = ""
    download_status: str = DISCOVERED
    local_path: str = ""
    sha256: str = ""
    size_bytes: int = 0
    published_or_updated: str = "unknown"
    review_status: str = "pending"
    notes: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    # Added in Phase 3.1 (older inventories load with these defaults).
    retrieved_on: str = ""
    text_path: str = ""
    text_sha256: str = ""
    text_chars: int = 0
    extraction_status: str = ""
    date_hint: str = ""
    flags: list = field(default_factory=list)
    registry_status: str = ""
    registry_reason: str = ""
    registry_id: str = ""
    # Added for hybrid collection (older inventories load with these defaults).
    canonical_url: str = ""
    last_checked: str = ""  # UTC time of the latest collection attempt
    last_extracted: str = ""  # UTC time of the latest successful text extraction
    content_hash: str = ""  # sha256 of the normalised text
    failure_reason: str = ""  # why the content is not collected (empty when it is)
    link_only: bool = False  # no content stored; the official URL is still offered to users
    imported_on: str = ""  # UTC time a manually saved file was registered

    @property
    def key(self):
        return normalize_url(self.url)


def is_link_only(source):
    """Content not collected, but the official URL can still be given to users to read the page."""
    return (not source.local_path and is_collectable_url(source.url)
            and source.download_status not in NOT_LINKABLE and source.review_status != "exclude_recommended")


def record_failure(source, status, reason, keep_history=True):
    """Set a not-collected status and reason. Stored files and text are never touched."""
    source.download_status, source.failure_reason = status, reason
    entry = f"{today()}: {reason}"
    source.errors = (source.errors + [entry])[-MAX_ERRORS_KEPT:] if keep_history else [entry]


class Inventory:
    """The JSON source inventory in ``metadata/source_inventory.json``."""

    def __init__(self, root):
        self.root = Path(root)
        self.path = self.root / METADATA_DIR / INVENTORY_FILE
        self.sources = {}
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            known = {f.name for f in fields(Source)}
            for item in data.get("sources", []):
                source = Source(**{k: v for k, v in item.items() if k in known})
                source.download_status = LEGACY_STATUSES.get(source.download_status, source.download_status)
                self.sources[source.key] = source

    def add(self, source):
        """Add a source unless its URL is already known. Returns (source, added)."""
        if source.category not in CATEGORIES:
            raise ValueError(f"Unknown category: {source.category}")
        existing = self.sources.get(source.key)
        if existing:
            return existing, False
        self.sources[source.key] = source
        return source, True

    def find_by_hash(self, digest):
        return next((s for s in self.sources.values() if s.sha256 == digest), None)

    def find_by_content_hash(self, digest, exclude=None):
        return next((s for s in self.sources.values()
                     if digest and s.content_hash == digest and s is not exclude and s.local_path), None)

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for source in self.sources.values():
            source.link_only = is_link_only(source)
        payload = {
            "generated_on": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "note": "Inventory of candidate USIU-Africa sources. Nothing here is approved for "
                    "the chatbot until an administrator reviews it.",
            "sources": [asdict(s) for s in sorted(self.sources.values(), key=lambda s: (s.category, s.title))],
        }
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def ensure_structure(root=KNOWLEDGE_ROOT):
    """Create the category and metadata folders (never deletes anything)."""
    root = Path(root)
    for name in CATEGORIES + (METADATA_DIR,):
        (root / name).mkdir(parents=True, exist_ok=True)
    return root


# --- Network access ------------------------------------------------------------------
class TooLarge(Exception):
    pass


class HttpFetcher:
    """Polite HTTP client: fixed, honest user agent, rate limit, timeouts and size cap."""

    def __init__(self, min_interval=MIN_SECONDS_BETWEEN_REQUESTS, max_bytes=MAX_PDF_BYTES, timeout=REQUEST_TIMEOUT):
        import requests

        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.min_interval = min_interval
        self.max_bytes = max_bytes
        self.timeout = timeout
        self._last = 0.0

    def get(self, url):
        """Return (status_code, content_type, body_bytes, final_url).

        The body of a response that ended on another host is not read.
        """
        wait = self.min_interval - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.monotonic()
        with self.session.get(url, stream=True, timeout=self.timeout, allow_redirects=True) as response:
            content_type = response.headers.get("Content-Type", "")
            if not is_official_host(response.url):
                return response.status_code, content_type, b"", response.url
            declared = response.headers.get("Content-Length", "")
            if declared.isdigit() and int(declared) > self.max_bytes:
                raise TooLarge("the file exceeds the size limit")
            chunks, total = [], 0
            for chunk in response.iter_content(65536):
                total += len(chunk)
                if total > self.max_bytes:
                    raise TooLarge("the file exceeds the size limit")
                chunks.append(chunk)
            return response.status_code, content_type, b"".join(chunks), response.url


def unpack_response(result, url):
    """(status, content_type, body, final_url) from a fetcher result (3- or 4-tuple)."""
    status, content_type, body = result[:3]
    return status, content_type or "", body or b"", result[3] if len(result) > 3 else url


class RobotsPolicy:
    """robots.txt rules for the official site. Unreadable robots.txt = disallow all."""

    def __init__(self, fetcher, user_agent=USER_AGENT):
        self.user_agent = user_agent
        self.parser = RobotFileParser()
        self.readable = False
        self.unreachable = False  # the site itself could not be reached
        self.error = ""
        try:
            status, _, body = fetcher.get(f"{OFFICIAL_SITE}/robots.txt")[:3]
            if status == 200:
                self.parser.parse(body.decode("utf-8", errors="replace").splitlines())
                self.readable = True
            else:
                self.error = f"robots.txt returned HTTP {status}"
        except Exception as e:
            self.unreachable = True
            self.error = f"robots.txt could not be fetched ({type(e).__name__}); the site was not reachable"

    def allows(self, url):
        return self.readable and self.parser.can_fetch(self.user_agent, url)


# --- Operations ------------------------------------------------------------------------
def import_seeds(inventory, seeds, defaults=None):
    """Add discovered sources (dicts) to the inventory. Returns (added, duplicates)."""
    added = duplicates = 0
    for seed in seeds:
        seed = {**(defaults or {}), **seed}
        source = Source(
            title=seed["title"],
            url=seed["url"],
            content_type=seed.get("content_type", "unknown"),
            category=seed["category"],
            discovered_on=seed.get("discovered_on", today()),
            discovered_via=seed.get("discovered_via", ""),
            found_on_page=seed.get("found_on_page", ""),
            published_or_updated=seed.get("published_or_updated", "unknown"),
            review_status=seed.get("review_status", "pending"),
            notes=list(seed.get("notes", [])),
        )
        if not is_usiu_domain(source.url):
            source.notes.append("Not a USIU-Africa domain; recorded only.")
        _, was_added = inventory.add(source)
        added += was_added
        duplicates += not was_added
    return added, duplicates


FORM_TITLE_RE = re.compile(r"\bforms?\b", re.IGNORECASE)


def is_form(source):
    """Application, re-admission and other forms are for people to fill in, never chatbot knowledge."""
    return bool(FORM_TITLE_RE.search(source.title))


def looks_like_html(body):
    head = body[:2048].lstrip().lower()
    return head.startswith(b"<!doctype html") or b"<html" in head


LOGIN_PATH_WORDS = ("login", "signin", "sign-in", "logon", "wp-login", "/sso", "/cas/", "/auth/")
PASSWORD_FIELD_RE = re.compile(rb"<input[^>]+type\s*=\s*[\"']?password", re.IGNORECASE)


def is_login_url(url):
    parts = urlsplit(url)
    path = (parts.path + "?" + parts.query).lower()
    return host_of(url) in DENIED_HOSTS or any(word in path for word in LOGIN_PATH_WORDS)


def classify_exception(error):
    """(status, reason) for a request that raised. Timeouts and connection errors are transient."""
    name = type(error).__name__
    if isinstance(error, TooLarge):
        return INVALID_FILE, str(error)
    if isinstance(error, TimeoutError) or "Timeout" in name:
        return TIMEOUT, f"{name}: the request timed out"
    if isinstance(error, ConnectionError) or "Connection" in name:
        return UNREACHABLE, f"{name}: the site could not be reached"
    return FAILED, f"{name}: {error}"


def classify_response(source, status, content_type, body, final_url):
    """(status, reason) when a response is not usable content, else (None, "")."""
    if not is_official_host(final_url):
        if is_login_url(final_url):
            return LOGIN_REQUIRED, f"redirected to a sign-in page ({host_of(final_url)})"
        return FAILED, f"redirected away from the official site (to {host_of(final_url) or 'an invalid URL'})"
    if is_login_url(final_url):
        return LOGIN_REQUIRED, "redirected to a sign-in page"
    if status == 401:
        return LOGIN_REQUIRED, "HTTP 401 (sign-in required)"
    if status == 403:
        return ACCESS_DENIED, "HTTP 403 (access denied)"
    if status in (404, 410):
        return NOT_FOUND, f"HTTP {status} (missing or moved)"
    if status == 429 or status >= 500:
        return SERVER_ERROR, f"HTTP {status}"
    if status != 200:
        return FAILED, f"HTTP {status}"
    if not body.strip():
        return EMPTY_CONTENT, "the response was empty"
    if source.content_type == "pdf":
        if body.lstrip()[:5] != b"%PDF-":
            if looks_like_html(body) and PASSWORD_FIELD_RE.search(body):
                return LOGIN_REQUIRED, "a sign-in page was returned instead of the PDF"
            return INVALID_FILE, f"response is not a PDF ({content_type or 'no content type'})"
    else:
        if "html" not in content_type.lower() or not looks_like_html(body):
            return INVALID_FILE, f"response is not an HTML page ({content_type or 'no content type'})"
        if PASSWORD_FIELD_RE.search(body):
            return LOGIN_REQUIRED, "the page asks for a password"
    return None, ""


def fetch_with_retries(fetcher, source, max_attempts=MAX_ATTEMPTS, retry_delay=RETRY_DELAY_SECONDS,
                       sleep=time.sleep):
    """One source, retried only after a transient failure. Returns (status, reason, response, attempts)."""
    for attempt in range(1, max_attempts + 1):
        response = None
        try:
            response = unpack_response(fetcher.get(source.url), source.url)
            status, reason = classify_response(source, *response)
        except Exception as e:
            status, reason = classify_exception(e)
        if status not in TRANSIENT or attempt == max_attempts:
            return status, reason, response, attempt
        sleep(retry_delay * attempt)


def canonical_of(page_canonical, final_url):
    """The page's declared canonical URL if it is on the official site, else the final URL."""
    candidate = urljoin(final_url, page_canonical) if page_canonical else ""
    return normalize_url(candidate if candidate and is_official_host(candidate) else final_url)


def download_sources(inventory, fetcher, robots, root, max_attempts=MAX_ATTEMPTS,
                     retry_delay=RETRY_DELAY_SECONDS, sleep=time.sleep):
    """Try to collect every discovered PDF and web page that the rules allow.

    Sources that cannot be collected keep their URL and get a precise status and reason.
    Sources already collected are not fetched again, so their stored content is kept.
    """
    root = Path(root)
    results = {}
    for source in list(inventory.sources.values()):
        if source.download_status not in RETRYABLE:
            continue
        if source.content_type not in ("pdf", "html"):
            continue  # unknown type: left for manual review
        if is_form(source):
            source.download_status, source.errors = SKIPPED_FORM, []
            source.failure_reason = "a form: offered as a link, never used as knowledge"
            continue
        if not is_collectable_url(source.url):
            source.download_status = NOT_OFFICIAL
            source.failure_reason = "not a public page on the official site (other host, portal, login or search)"
            note = "Other domain or subdomain: review manually before use."
            if note not in source.notes:
                source.notes.append(note)
            continue
        source.last_checked = utc_now()
        if not robots.allows(source.url):
            # Re-checked on every run, so only the latest reason is kept.
            record_failure(source, UNREACHABLE if robots.unreachable else ROBOTS_DISALLOWED,
                           robots.error or "disallowed for this user agent by robots.txt", keep_history=False)
            continue
        status, reason, response, attempts = fetch_with_retries(fetcher, source, max_attempts, retry_delay, sleep)
        if status:
            record_failure(source, status, reason + (f" (after {attempts} attempts)" if attempts > 1 else ""))
            continue
        _, _, body, final_url = response
        if normalize_url(final_url) != source.key and not robots.allows(final_url):
            record_failure(source, ROBOTS_DISALLOWED, f"redirected to {final_url}, which robots.txt disallows",
                           keep_history=False)
            continue
        canonical, content_hash = normalize_url(final_url), ""
        if source.content_type == "html":
            details = extract_html_details(body)
            if len(details["text"]) < MIN_PAGE_TEXT_CHARS:
                record_failure(source, EMPTY_CONTENT, "the page has no readable text")
                continue
            canonical = canonical_of(details["canonical"], final_url)
            content_hash = normalized_text_hash(details["text"])
        source.canonical_url = canonical
        same_page = inventory.sources.get(canonical)
        if same_page is not None and same_page is not source and same_page.local_path:
            duplicate = same_page
        else:
            duplicate = inventory.find_by_content_hash(content_hash, exclude=source)
        if duplicate:
            source.download_status, source.failure_reason = DUPLICATE, f"same content as {duplicate.url}"
            note = f"Same content as {duplicate.url}"
            if note not in source.notes:
                source.notes.append(note)
            continue
        source.retrieved_on = today()
        if save_document(inventory, source, body, root) is not None:
            source.failure_reason, source.content_hash = "", content_hash
    for source in inventory.sources.values():
        results[source.download_status] = results.get(source.download_status, 0) + 1
    return results


def save_document(inventory, source, data, root, filename=None):
    """Store file bytes in the source's category folder, unless the content is a duplicate."""
    digest = sha256_bytes(data)
    duplicate = inventory.find_by_hash(digest)
    if duplicate and duplicate is not source:
        source.download_status = DUPLICATE
        source.failure_reason = f"same file as {duplicate.url}"
        source.notes.append(f"Same content as {duplicate.url}")
        return None

    folder = Path(root) / source.category
    folder.mkdir(parents=True, exist_ok=True)
    name = filename or safe_filename(source.url, extension=".html" if source.content_type == "html" else ".pdf",
                                     fallback="page.html" if source.content_type == "html" else "document.pdf")
    target = folder / name
    counter = 1
    while target.exists() and sha256_bytes(target.read_bytes()) != digest:
        target = folder / f"{Path(name).stem}_{counter}{Path(name).suffix}"
        counter += 1
    target.write_bytes(data)

    source.download_status = DOWNLOADED if source.download_status != MANUAL else MANUAL
    source.local_path = target.relative_to(root).as_posix()
    source.sha256 = digest
    source.size_bytes = len(data)
    # New content must be extracted (and reviewed) again.
    source.extraction_status = source.text_path = source.text_sha256 = source.content_hash = ""
    return target


MANUAL_FILE_TYPES = {".pdf": "pdf", ".html": "html", ".htm": "html", ".txt": "html"}


def register_local_file(inventory, root, file_path, category, url, title, published="unknown", note="",
                        retrieved=None):
    """Add a document or saved web page obtained manually (in a browser, or supplied by a USIU office).

    ``url`` is the official page the content came from (it becomes the citation link);
    ``retrieved`` is the date it was obtained (default: today). Saved pages are ``.html``
    files ("Save page as" in a browser) or ``.txt`` files with the page text.
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()
    if suffix not in MANUAL_FILE_TYPES:
        raise ValueError("Only .pdf, .html, .htm and .txt files can be registered")
    data = file_path.read_bytes()
    if suffix == ".pdf" and not data.lstrip()[:5] == b"%PDF-":
        raise ValueError("The file is not a PDF")
    if suffix in (".html", ".htm") and not looks_like_html(data):
        raise ValueError("The file is not an HTML page")
    if suffix == ".txt":
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("Text files must be UTF-8") from None
    if retrieved is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", retrieved):
        raise ValueError("The retrieval date must be YYYY-MM-DD")
    if urlsplit(url).scheme.lower() != "https" or not host_of(url):
        raise ValueError("The source URL must be the https address of the original page")
    probe = Source(title=title, url=url, content_type=MANUAL_FILE_TYPES[suffix], category=category)
    if is_form(probe):
        raise ValueError("Forms are not used as chatbot knowledge")
    source, added = inventory.add(Source(
        title=title, url=url, content_type=MANUAL_FILE_TYPES[suffix], category=category,
        discovered_via="registered manually", published_or_updated=published,
        download_status=MANUAL, notes=[note] if note else [],
    ))
    if not added and source.local_path:
        raise ValueError(f"This URL is already registered: {source.local_path}")
    source.download_status = MANUAL
    source.category = category
    source.content_type = MANUAL_FILE_TYPES[suffix]
    source.title = title
    if published != "unknown":
        source.published_or_updated = published
    source.retrieved_on = retrieved or today()
    source.imported_on = utc_now()
    source.errors, source.failure_reason = [], ""
    source.canonical_url = normalize_url(url)
    if suffix in (".html", ".htm"):
        declared = canonical_of(extract_html_details(data)["canonical"], url)
        note = f"The saved page declares the canonical URL {declared}; check the source URL."
        if declared != source.canonical_url and note not in source.notes:
            source.notes.append(note)
    return save_document(inventory, source, data, root, filename=safe_filename(file_path.name, extension=suffix))


# --- Text extraction ---------------------------------------------------------------------
def extract_pdf(data, max_pages=500):
    """Text of a PDF and the date in its file metadata (which may not be the publication date)."""
    import io

    from pypdf import PdfReader

    from utils.pdf_utils import extract_pdf_text

    text = extract_pdf_text(data, max_pages=max_pages)
    try:
        info = PdfReader(io.BytesIO(data)).metadata or {}
        date = _iso_date(str(info.get("/ModDate") or info.get("/CreationDate") or ""))
    except Exception:
        date = ""
    return text, date


# Words of form fields that ask for personal details.
FORM_FIELD_RE = re.compile(
    r"\b(surname|first name|middle name|other names|full names?|date of birth|place of birth|national id|"
    r"id\s*/\s*passport|passport (?:no|number)|marital status|next of kin|signature|kcse index|"
    r"index (?:no|number)|telephone no|mobile no|postal address|guardian'?s name|parent'?s name)\b",
    re.IGNORECASE,
)
BLANK_FIELD_RE = re.compile(r"_{5,}|\.{8,}|\[\s*\]")
# Text that tries to instruct an AI model. Source text is untrusted data.
INSTRUCTION_RE = re.compile(
    r"ignore (?:all |any |the )?(?:previous|prior|above|earlier) (?:instructions|prompts|rules)|"
    r"disregard (?:all |any |the )?(?:previous|prior|above|earlier)|you are now (?:a|an|in)\b|"
    r"system prompt|developer mode|jailbreak|do anything now|<\s*script",
    re.IGNORECASE,
)
MIN_TEXT_CHARS = 200


def text_flags(source, text, today_date=None):
    """Review flags that depend on a source's text and dates (not on other sources)."""
    today_date = today_date or datetime.date.today()
    flags = []
    if source.extraction_status != EXTRACTED or len(text) < MIN_TEXT_CHARS or \
            sum(c.isalpha() for c in text) < 0.5 * len(text.replace(" ", "").replace("\n", "")):
        flags.append(FLAG_EXTRACTION)
    if is_form(source) or (len({m.lower() for m in FORM_FIELD_RE.findall(text)}) >= 3
                           and len(BLANK_FIELD_RE.findall(text)) >= 3):
        flags.append(FLAG_FORM)
    if INSTRUCTION_RE.search(text):
        flags.append(FLAG_INSTRUCTIONS)
    date = source_date_of(source)
    if not date:
        flags.append(FLAG_UNDATED)
    title_years = [int(y) for y in re.findall(r"\b(20\d{2})\b", source.title)]
    if source.review_status == "likely_outdated" or \
            (date and (today_date - _date_end(date)).days > STALE_DAYS) or \
            (title_years and max(title_years) < today_date.year - 1):
        flags.append(FLAG_OUTDATED)
    if not date and source.date_hint:
        flags.append(FLAG_DATE_FROM_METADATA)
    return flags


def source_date_of(source):
    """The source's publication/update date as YYYY, YYYY-MM or YYYY-MM-DD, or ''."""
    value = (source.published_or_updated or "").strip()
    return value if re.fullmatch(r"\d{4}(-\d{2}(-\d{2})?)?", value) else ""


def _date_end(value):
    parts = [int(p) for p in value.split("-")]
    if len(parts) == 1:
        return datetime.date(parts[0], 12, 31)
    if len(parts) == 2:
        nxt = datetime.date(parts[0] + parts[1] // 12, parts[1] % 12 + 1, 1)
        return nxt - datetime.timedelta(days=1)
    return datetime.date(*parts)


def normalized_text_hash(text):
    return sha256_bytes(re.sub(r"\s+", " ", text).strip().lower().encode("utf-8"))


def extract_all(inventory, root, force=False):
    """Extract text from every stored file, save it next to the file and set review flags.

    Returns a count per extraction status. Duplicate text (the same page under two URLs)
    is flagged on the later source.
    """
    root = Path(root)
    results = {}
    texts = {}
    for source in sorted(inventory.sources.values(), key=lambda s: s.key):
        if not source.local_path:
            continue
        file_path = root / source.local_path
        text_file = file_path.with_name(file_path.name + ".extracted.txt")
        if not force and source.extraction_status and source.text_path and text_file.exists():
            texts[source.key] = text_file.read_text(encoding="utf-8")
        else:
            text, date_hint = "", ""
            try:
                data = file_path.read_bytes()
                if file_path.suffix.lower() == ".pdf":
                    text, date_hint = extract_pdf(data)
                elif file_path.suffix.lower() in (".html", ".htm"):
                    text, _page_title, date_hint = extract_html(data)
                    if date_hint and not source_date_of(source):
                        # A date in the page's own metadata ("last modified") is the page's date.
                        source.published_or_updated, date_hint = date_hint, ""
                        source.notes.append("Date taken from the page's metadata; confirm it on the page.")
                else:
                    text = data.decode("utf-8").strip()
                source.extraction_status = EXTRACTED if text.strip() else NO_TEXT
            except Exception as e:
                source.extraction_status = EXTRACTION_FAILED
                source.errors.append(f"{today()}: text extraction failed ({type(e).__name__})")
            text = text.strip()
            text_file.write_text(text, encoding="utf-8")
            source.text_path = text_file.relative_to(root).as_posix()
            source.text_sha256 = sha256_bytes(text.encode("utf-8")) if text else ""
            source.content_hash = normalized_text_hash(text) if text else ""
            source.text_chars = len(text)
            if source.extraction_status == EXTRACTED:
                source.last_extracted = utc_now()
            source.date_hint = date_hint
            texts[source.key] = text
        results[source.extraction_status] = results.get(source.extraction_status, 0) + 1

    seen = {}
    for key in sorted(texts):
        source, text = inventory.sources[key], texts[key]
        source.flags = text_flags(source, text)
        if text:
            digest = normalized_text_hash(text)
            if digest in seen:
                source.flags.append(FLAG_DUPLICATE)
                note = f"Same text as {seen[digest].url}"
                if note not in source.notes:
                    source.notes.append(note)
            else:
                seen[digest] = source
    return results


# --- Source registry import ----------------------------------------------------------------
def import_to_registry(inventory, root, registry, actor="knowledge-sources-tool"):
    """Create or update *draft* sources in the registry from extracted files. Never approves.

    Skipped (with the reason recorded): forms, duplicates, items without text, the
    ``pending_review`` category (a department must be chosen first) and sources whose
    approved or archived registry entry has different content (an administrator
    must decide). Returns a count per registry status.
    """
    from services.sources import SourceError, parse_source_date

    root = Path(root)
    results = {}

    def skip(source, reason):
        source.registry_status, source.registry_reason = REG_SKIPPED, reason

    for source in sorted(inventory.sources.values(), key=lambda s: s.key):
        if not source.local_path:
            continue
        source.registry_reason = ""
        blocking = [f for f in source.flags if f in NOT_IMPORTABLE_FLAGS]
        if source.download_status == ARCHIVED:
            skip(source, "archived")
        elif source.extraction_status != EXTRACTED or not source.text_path:
            skip(source, "no extracted text (run `extract`; scanned PDFs have no text)")
        elif blocking:
            skip(source, "not importable: " + ", ".join(blocking))
        elif source.category not in DEPARTMENT_FOR_CATEGORY:
            skip(source, "choose a department first (register it again with --category)")
        else:
            text = (root / source.text_path).read_text(encoding="utf-8")
            try:
                source_date = parse_source_date(source_date_of(source) or None)
            except SourceError:
                source_date = None
            flags = list(source.flags)
            notes = (f"Imported on {today()} by {actor} from {source.local_path}. "
                     f"Review flags: {', '.join(flags) or 'none'}. Draft: verify against the official page "
                     "before approving.")
            data = {
                "url": source.url, "title": source.title, "department": DEPARTMENT_FOR_CATEGORY[source.category],
                "content_type": "pdf" if source.content_type == "pdf" else "html", "source_date": source_date,
                "retrieved_at": source.retrieved_on or None, "notes": notes, "text": text,
            }
            metadata = {"file_sha256": source.sha256, "local_path": source.local_path,
                        "extraction_status": source.extraction_status, "date_hint": source.date_hint,
                        "imported_by": actor}
            try:
                existing = registry.find_by_url(source.url)
                if existing is None:
                    created = registry.create(data, actor=actor)
                    source.registry_status, source.registry_id = REG_CREATED, str(created["_id"])
                    registry.set_review_flags(source.registry_id, flags, metadata)
                elif existing.get("text_sha256") == sha256_bytes(text.strip().encode("utf-8")):
                    source.registry_status, source.registry_id = REG_UNCHANGED, str(existing["_id"])
                    registry.set_review_flags(source.registry_id, flags, metadata)
                elif existing["status"] == "draft":
                    registry.update(str(existing["_id"]), data, actor=actor)
                    source.registry_status, source.registry_id = REG_UPDATED, str(existing["_id"])
                    registry.set_review_flags(source.registry_id, flags, metadata)
                else:
                    source.registry_id = str(existing["_id"])
                    skip(source, f"the registry already has an {existing['status']} version with different "
                                 "content; an administrator must compare them")
            except SourceError as e:
                skip(source, f"rejected by the registry: {e}")
        results[source.registry_status] = results.get(source.registry_status, 0) + 1
    return results


# --- Official links for the chatbot -------------------------------------------------------
def is_catalogue_candidate(source):
    """Official pages users can be sent to: current, linkable, with a known department."""
    return (is_collectable_url(source.url) and source.download_status not in NOT_LINKABLE
            and source.review_status not in ("exclude_recommended", "likely_outdated")
            and source.category in DEPARTMENT_FOR_CATEGORY)


def sync_catalogue(inventory, catalogue_path=CATALOGUE_FILE):
    """Add official, linkable sources to the chatbot's page catalogue. Returns the URLs added.

    Adds only: existing entries (their title, department and ``reviewed`` flag) are never
    changed or removed. New entries are ``reviewed: false``, so they are only shown as
    unverified places to look and are never fetched live until an administrator reviews them.
    """
    path = Path(catalogue_path)
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"pages": []}
    known = {normalize_url(p["url"]) for p in data.get("pages", []) if isinstance(p.get("url"), str)}
    added = []
    for source in sorted(inventory.sources.values(), key=lambda s: (s.category, s.title.lower())):
        if source.key in known or not is_catalogue_candidate(source):
            continue
        status = "content collected" if source.local_path else f"link only: {source.download_status}"
        data.setdefault("pages", []).append({
            "url": source.url, "title": source.title, "department": DEPARTMENT_FOR_CATEGORY[source.category],
            "keywords": [], "reviewed": False,
            "notes": [f"Added {today()} from metadata/{INVENTORY_FILE} ({status})."],
        })
        known.add(source.key)
        added.append(source.url)
    if added:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return added


def archive_source(inventory, url, reason):
    """Withdraw a source (superseded, wrong or no longer published). It is not fetched, imported or linked."""
    source = inventory.sources.get(normalize_url(url))
    if source is None:
        raise ValueError("This URL is not in the inventory")
    source.download_status, source.failure_reason = ARCHIVED, reason or "archived"
    source.notes.append(f"{today()}: archived ({source.failure_reason})")
    return source


# --- Reporting -------------------------------------------------------------------------
def build_report(inventory, robots_note=""):
    sources = list(inventory.sources.values())
    by_cat = {c: [s for s in sources if s.category == c] for c in CATEGORIES}
    count = lambda items, **kw: sum(all(getattr(s, k) == v for k, v in kw.items()) for s in items)  # noqa: E731

    lines = [
        "# USIUBOT knowledge sources — discovery report",
        "",
        f"Generated: {today()}. Machine-readable inventory: `metadata/{INVENTORY_FILE}`.",
        "",
        "Nothing listed here is approved for the chatbot. Every source needs administrator review.",
        "",
    ]
    if robots_note:
        lines += ["## Access policy", "", robots_note, ""]
    lines += [
        "## Totals",
        "",
        f"- Sources discovered: {len(sources)}",
        f"- Web pages (HTML): {count(sources, content_type='html')}",
        f"- PDFs found: {count(sources, content_type='pdf')}",
        f"- PDFs downloaded: {count(sources, download_status=DOWNLOADED, content_type='pdf')}",
        f"- PDFs registered manually: {count(sources, download_status=MANUAL)}",
        f"- Web pages downloaded: {count(sources, download_status=DOWNLOADED, content_type='html')}",
        f"- Link only (content not collected; the official URL is offered): "
        f"{sum(is_link_only(s) for s in sources)}",
        f"- Blocked by robots.txt: {count(sources, download_status=BLOCKED_ROBOTS)}",
        f"- Site unreachable (robots.txt could not be checked): {count(sources, download_status=UNREACHABLE)}",
        f"- Access denied (HTTP 403): {count(sources, download_status=ACCESS_DENIED)}",
        f"- Sign-in required: {count(sources, download_status=LOGIN_REQUIRED)}",
        f"- Timed out: {count(sources, download_status=TIMEOUT)}",
        f"- Server errors: {count(sources, download_status=SERVER_ERROR)}",
        f"- Missing or moved (HTTP 404/410): {count(sources, download_status=NOT_FOUND)}",
        f"- Empty pages: {count(sources, download_status=EMPTY_CONTENT)}",
        f"- Invalid or unsupported files: {count(sources, download_status=INVALID_FILE)}",
        f"- Duplicates: {count(sources, download_status=DUPLICATE)}",
        f"- Archived: {count(sources, download_status=ARCHIVED)}",
        f"- Forms (never downloaded): {count(sources, download_status=SKIPPED_FORM)}",
        f"- Other domains/subdomains (not fetched): {count(sources, download_status=NOT_OFFICIAL)}",
        f"- Failed downloads (other errors): {count(sources, download_status=FAILED)}",
        f"- Needing manual review (all): {count(sources, review_status='pending') + count(sources, review_status='exclude_recommended') + count(sources, review_status='likely_outdated')}",
        "",
        "## By category",
        "",
        "| Category | Sources | HTML | PDF | Files stored |",
        "|---|---|---|---|---|",
    ]
    for cat, items in by_cat.items():
        stored = sum(1 for s in items if s.local_path)
        lines.append(f"| {cat} | {len(items)} | {count(items, content_type='html')} | "
                     f"{count(items, content_type='pdf')} | {stored} |")
    empty = [c for c, items in by_cat.items() if not any(s.local_path for s in items)]
    lines += ["", "Categories with no stored documents yet: " + (", ".join(empty) or "none"), ""]

    for cat, items in by_cat.items():
        if not items:
            continue
        lines += [f"## {cat}", "", "| Title | Type | Status | Review | Notes |", "|---|---|---|---|---|"]
        for s in sorted(items, key=lambda s: s.title.lower()):
            notes = "; ".join(s.notes + s.errors).replace("|", "/")
            lines.append(f"| [{s.title.replace('|', '/')}]({s.url}) | {s.content_type} | "
                         f"{s.download_status} | {s.review_status} | {notes} |")
        lines.append("")
    return "\n".join(lines)


def write_report(inventory, root, robots_note=""):
    path = Path(root) / METADATA_DIR / REPORT_FILE
    path.write_text(build_report(inventory, robots_note), encoding="utf-8")
    write_import_report(inventory, root, robots_note)
    return path


NOT_COLLECTED_REASONS = {
    UNREACHABLE: "the site could not be reached from this network, so robots.txt could not be checked",
    BLOCKED_ROBOTS: "robots.txt does not allow this tool to fetch it",
    ACCESS_DENIED: "the server refused access (HTTP 403)",
    LOGIN_REQUIRED: "the page requires signing in; never fetched with credentials",
    TIMEOUT: "the request timed out (retried within the limit)",
    SERVER_ERROR: "the server returned an error (retried within the limit)",
    NOT_FOUND: "the page is missing or has moved",
    EMPTY_CONTENT: "the page had no readable content",
    INVALID_FILE: "the response was not a valid PDF/HTML file or was too large",
    ARCHIVED: "archived by an administrator",
    NOT_OFFICIAL: "other domain or subdomain (not fetched; may need a login or separate permission)",
    SKIPPED_FORM: "a form: not used as chatbot knowledge",
    FAILED: "the download failed",
    DUPLICATE: "same content as another source",
    NOT_APPLICABLE: "web page not attempted yet (run `download`)",
    DISCOVERED: "not attempted yet, or unknown content type",
}


def _cell(value):
    return str(value).replace("|", "/").replace("\n", " ")


def build_import_report(inventory, robots_note=""):
    """Collection, extraction and registry import results. Contains metadata only, never document text."""
    sources = sorted(inventory.sources.values(), key=lambda s: (s.category, s.title.lower()))
    stored = [s for s in sources if s.local_path]
    not_collected = [s for s in sources if not s.local_path]
    tally = lambda items, attr: {k: sum(getattr(s, attr) == k for s in items)  # noqa: E731
                                 for k in sorted({getattr(s, attr) for s in items})}

    lines = [
        "# USIUBOT knowledge import report",
        "",
        f"Generated: {today()}. This report lists metadata only; document text is kept locally and is not in Git.",
        "",
        "**Nothing here is approved.** Imported items are *draft* sources: an administrator must check each "
        "one against the official page and approve it before the chatbot can use it.",
        "",
    ]
    if robots_note:
        lines += ["## Access check", "", robots_note, ""]
    lines += ["## Summary", "",
              f"- Sources in the inventory: {len(sources)}",
              f"- Files collected (downloaded or registered manually): {len(stored)}",
              f"- Not collected: {len(not_collected)}"]
    lines += [f"  - {k}: {v}" for k, v in tally(not_collected, "download_status").items()]
    lines += ["- Text extraction:"] + ([f"  - {k or 'not extracted yet'}: {v}"
                                        for k, v in tally(stored, "extraction_status").items()] or ["  - none"])
    lines += ["- Source registry:"] + ([f"  - {k or 'not imported yet'}: {v}"
                                        for k, v in tally(stored, "registry_status").items()] or ["  - none"])
    lines.append("")

    lines += ["## Collected files", ""]
    if stored:
        lines += ["| Title | Department | File | Retrieved | Last extracted | Date | Extraction | Flags | Registry |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for s in stored:
            registry = s.registry_status + (f" ({s.registry_reason})" if s.registry_reason else "")
            lines.append(f"| [{_cell(s.title)}]({s.url}) | {s.category} | {_cell(s.local_path)} | "
                         f"{s.retrieved_on or '?'} | {s.last_extracted or '-'} | {s.published_or_updated} | "
                         f"{s.extraction_status or 'not extracted'} ({s.text_chars} chars) | "
                         f"{', '.join(s.flags) or 'none'} | {_cell(registry) or 'not imported'} |")
    else:
        lines.append("None. No page or document has been downloaded or registered yet.")
    lines.append("")

    lines += ["## Not collected: inaccessible, restricted, other domains and skipped", "",
              "Nothing in this section was downloaded; its content is not available to the chatbot. "
              "Link-only sources are still offered to users as official pages to read "
              "(after `sync-links`).", "",
              "| Title | Category | Type | Status | Link only | Last checked | Reason |",
              "|---|---|---|---|---|---|---|"]
    for s in not_collected:
        reason = NOT_COLLECTED_REASONS.get(s.download_status, s.download_status)
        detail = s.failure_reason or "; ".join(s.errors[-1:])
        lines.append(f"| [{_cell(s.title)}]({s.url}) | {s.category} | {s.content_type} | {s.download_status} | "
                     f"{'yes' if is_link_only(s) else 'no'} | {s.last_checked or '-'} | "
                     f"{_cell(reason + (f' ({detail})' if detail else ''))} |")
    lines.append("")

    review = [s for s in stored if s.registry_status in (REG_CREATED, REG_UPDATED, REG_UNCHANGED)]
    lines += ["## Requires review before approval", ""]
    if review:
        lines += ["Each draft must be compared with the official page (text complete and current, date correct, "
                  "no personal data) before it is approved in the admin Sources screen.", "",
                  "| Title | Department | Flags to check |", "|---|---|---|"]
        lines += [f"| [{_cell(s.title)}]({s.url}) | {s.category} | {', '.join(s.flags) or 'none'} |"
                  for s in review]
    else:
        lines.append("No draft sources have been imported yet.")
    held = [s for s in stored if s.registry_status == REG_SKIPPED]
    if held:
        lines += ["", "Collected but not imported:", ""]
        lines += [f"- [{_cell(s.title)}]({s.url}): {_cell(s.registry_reason)}" for s in held]
    lines.append("")
    return "\n".join(lines)


def write_import_report(inventory, root, robots_note=""):
    path = Path(root) / METADATA_DIR / IMPORT_REPORT_FILE
    path.write_text(build_import_report(inventory, robots_note), encoding="utf-8")
    return path


def _registry_from_app():
    """The application's own source registry (same MongoDB, settings and validation)."""
    from app import create_app

    return create_app().extensions["source_registry"]


# --- Command line ------------------------------------------------------------------------
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", default=str(KNOWLEDGE_ROOT))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    seeds = sub.add_parser("import-seeds")
    seeds.add_argument("seed_file")
    sub.add_parser("download")
    reg = sub.add_parser("register")
    reg.add_argument("file", help=".pdf, a saved web page (.html/.htm) or the page text (.txt, UTF-8)")
    reg.add_argument("--category", required=True, choices=CATEGORIES)
    reg.add_argument("--url", required=True, help="Official URL the content came from (used for citations)")
    reg.add_argument("--title", required=True)
    reg.add_argument("--published", default="unknown", help="Date on the page/document: YYYY, YYYY-MM or YYYY-MM-DD")
    reg.add_argument("--retrieved", default=None, help="Date it was obtained, YYYY-MM-DD (default: today)")
    reg.add_argument("--note", default="", help="Who obtained it and how, e.g. 'browser download by ...'")
    extract = sub.add_parser("extract")
    extract.add_argument("--force", action="store_true", help="Extract again even if text exists")
    sub.add_parser("import-registry")
    links = sub.add_parser("sync-links", help="add official, linkable sources to the chatbot's page catalogue")
    links.add_argument("--catalogue", default=str(CATALOGUE_FILE))
    archive = sub.add_parser("archive", help="withdraw a source (never fetched, imported or linked again)")
    archive.add_argument("url")
    archive.add_argument("--reason", required=True)
    sub.add_parser("report")
    args = parser.parse_args(argv)

    root = ensure_structure(args.root)
    inventory = Inventory(root)
    robots_note = ""

    if args.command == "import-seeds":
        data = json.loads(Path(args.seed_file).read_text(encoding="utf-8"))
        added, dupes = import_seeds(inventory, data["sources"], data.get("defaults"))
        print(f"Imported {added} sources ({dupes} duplicates skipped)")
    elif args.command == "download":
        fetcher = HttpFetcher()
        robots = RobotsPolicy(fetcher)
        if not robots.readable:
            robots_note = (f"{today()}: {robots.error}. No page or PDF was downloaded. "
                           + _previous_policy_note(root))
        elif not robots.allows(f"{OFFICIAL_SITE}/"):
            robots_note = (f"{OFFICIAL_SITE}/robots.txt (checked {today()}) disallows all user agents "
                           "except named search engines, so this tool did not download any page or PDF.")
        print(download_sources(inventory, fetcher, robots, root))
        if robots_note:
            print(robots_note)
        # Kept so that later commands (extract, report, ...) show the latest access check.
        (root / METADATA_DIR / ACCESS_CHECK_FILE).write_text(
            robots_note or f"{today()}: robots.txt allowed this tool; see the statuses below.", encoding="utf-8")
    elif args.command == "register":
        target = register_local_file(inventory, root, args.file, args.category, args.url,
                                     args.title, args.published, args.note, args.retrieved)
        print(f"Stored: {target}" if target else "Duplicate content; not stored again")
    elif args.command == "extract":
        print(extract_all(inventory, root, force=args.force))
    elif args.command == "import-registry":
        try:
            registry = _registry_from_app()
        except Exception as e:
            print(f"Cannot open the source registry ({type(e).__name__}: {e}). Check the backend .env "
                  "(MONGO_URI, SECRET_KEY, ...). Nothing was imported.", file=sys.stderr)
            return 2
        print(import_to_registry(inventory, root, registry))
    elif args.command == "sync-links":
        added = sync_catalogue(inventory, args.catalogue)
        print(f"Added {len(added)} official links to {args.catalogue} (unreviewed)")
    elif args.command == "archive":
        archive_source(inventory, args.url, args.reason)

    inventory.save()
    report = write_report(inventory, root, robots_note or _previous_policy_note(root))
    print(f"Inventory: {inventory.path}\nReport: {report}")
    return 0


def _previous_policy_note(root):
    """The latest access check written by ``download``, else the original access policy note."""
    for name in (ACCESS_CHECK_FILE, "access_policy.txt"):
        note_file = Path(root) / METADATA_DIR / name
        if note_file.exists():
            return note_file.read_text(encoding="utf-8").strip()
    return ""


if __name__ == "__main__":
    sys.exit(main())
