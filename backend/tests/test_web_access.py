"""Website access rules: trusted hosts, robots.txt, redirects, limits, cache.

All synthetic: a fake transport, or a local HTTP server on 127.0.0.1. No real website
is contacted.
"""

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import pytest

from config.config import validate_config
from services import web_access as wa
from services.web_access import FetchError, TTLCache, WebsiteAccess, check_trusted_hosts, is_trusted_url
from tests.conftest import ROBOTS_ALLOW_USIUBOT, ROBOTS_DENY_ALL, FakeTransport, html_page

TRUSTED = frozenset({"www.usiu.ac.ke"})
SITE = "https://www.usiu.ac.ke"
PAGE = SITE + "/how-to-apply/"
BODY = "<p>Applications are submitted through the online application system before the deadline.</p>" * 3


def settings(**extra):
    return {"TRUSTED_SOURCE_HOSTS": ["www.usiu.ac.ke"], "LIVE_USER_AGENT": "USIUBOT/1.0", **extra}


def access(routes, clock=None, **extra):
    transport = FakeTransport(routes)
    kwargs = {"clock": clock} if clock else {}
    return WebsiteAccess(settings(**extra), transport=transport, **kwargs), transport


def ok_page(title="How to Apply", body=BODY, **headers):
    return 200, {"Content-Type": "text/html; charset=utf-8", **headers}, html_page(title, body)


@pytest.mark.parametrize("url", [
    "https://www.usiu.ac.ke/how-to-apply/",
    "https://www.usiu.ac.ke/undergraduate-costs/?schl=sst",
    "https://WWW.USIU.AC.KE/about/",
    "https://www.usiu.ac.ke/academics/undergraduate-programs/",
])
def test_trusted_urls(url):
    assert is_trusted_url(url, TRUSTED)


@pytest.mark.parametrize("url", [
    "http://www.usiu.ac.ke/how-to-apply/",              # not https
    "https://usiu.ac.ke/how-to-apply/",                 # different host, not listed
    "https://cx.usiu.ac.ke/ics/",                       # student portal
    "https://erepo.usiu.ac.ke/handle/1",                # subdomain not trusted automatically
    "https://www.usiu.ac.ke.evil.example/",             # look-alike host
    "https://evil.example/?u=https://www.usiu.ac.ke/",
    "https://user:pw@www.usiu.ac.ke/",                  # credentials
    "https://www.usiu.ac.ke:8443/",                     # non-default port
    "https://www.usiu.ac.ke/wp-login.php",              # login page
    "https://www.usiu.ac.ke/student-portal/",           # portal path
    "https://www.usiu.ac.ke/?s=fees",                   # site search results
    "https://www.usiu.ac.ke/ics/",                      # portal path on the main host
    "https://www.usiu.ac.ke/wp-json/wp/v2/search",      # API, not a page
    "javascript:alert(1)",
    "",
    None,
])
def test_untrusted_urls(url):
    assert not is_trusted_url(url, TRUSTED)


def test_trusted_host_configuration_is_validated():
    assert check_trusted_hosts(["www.usiu.ac.ke"]) == []
    assert check_trusted_hosts(["*.usiu.ac.ke"])
    assert check_trusted_hosts(["cx.usiu.ac.ke"])
    assert check_trusted_hosts(["www.example.com"])
    base = {"SECRET_KEY": "x" * 40, "CLOUDINARY_DELIVERY_TYPE": "authenticated",
            "ALLOWED_SOURCE_DOMAINS": ["usiu.ac.ke"]}
    assert any("TRUSTED_SOURCE_HOSTS" in p for p in validate_config({**base, "TRUSTED_SOURCE_HOSTS": ["cx.usiu.ac.ke"]}))
    assert not any("TRUSTED_SOURCE_HOSTS" in p for p in validate_config({**base, "TRUSTED_SOURCE_HOSTS": ["www.usiu.ac.ke"]}))


def test_permitted_page_is_fetched_and_extracted():
    web, transport = access({SITE + "/robots.txt": (200, {}, ROBOTS_ALLOW_USIUBOT), PAGE: ok_page()})
    result = web.fetch_page(PAGE)
    assert result.ok
    assert result.page.title == "How to Apply"
    assert "online application system" in result.page.text
    assert "Menu Home" not in result.page.text and "Copyright" not in result.page.text
    assert result.page.final_url == PAGE


def test_robots_disallow_means_the_page_is_never_requested():
    web, transport = access({SITE + "/robots.txt": (200, {}, ROBOTS_DENY_ALL), PAGE: ok_page()})
    result = web.fetch_page(PAGE)
    assert result.status == wa.ROBOTS_DISALLOWED
    assert transport.fetched(SITE + "/robots.txt")
    assert not transport.fetched(PAGE)


def test_unreadable_robots_means_nothing_is_fetched():
    web, transport = access({SITE + "/robots.txt": FetchError(wa.TIMEOUT), PAGE: ok_page()})
    assert web.fetch_page(PAGE).status == wa.ROBOTS_UNAVAILABLE
    assert not transport.fetched(PAGE)


@pytest.mark.parametrize("status,expected", [(403, wa.ROBOTS_DISALLOWED), (401, wa.ROBOTS_DISALLOWED),
                                             (500, wa.ROBOTS_UNAVAILABLE), (404, wa.OK)])
def test_robots_http_status_handling(status, expected):
    web, transport = access({SITE + "/robots.txt": (status, {}, b""), PAGE: ok_page()})
    assert web.fetch_page(PAGE).status == expected
    assert transport.fetched(PAGE) == (expected == wa.OK)


def test_untrusted_url_is_refused_without_any_request():
    web, transport = access({})
    for url in ("https://cx.usiu.ac.ke/ics/", "https://www.example.com/", "http://www.usiu.ac.ke/"):
        assert web.fetch_page(url).status == wa.NOT_TRUSTED
    assert transport.requests == []


def test_redirect_to_another_host_is_refused():
    web, transport = access({
        SITE + "/robots.txt": (200, {}, ROBOTS_ALLOW_USIUBOT),
        PAGE: (302, {"Location": "https://cx.usiu.ac.ke/ics/"}, b""),
    })
    assert web.fetch_page(PAGE).status == wa.BAD_REDIRECT
    assert not transport.fetched("https://cx.usiu.ac.ke/ics/")


def test_redirect_within_trusted_host_is_followed_and_reported():
    new = SITE + "/admissions/how-to-apply/"
    web, _ = access({
        SITE + "/robots.txt": (200, {}, ROBOTS_ALLOW_USIUBOT),
        PAGE: (301, {"Location": "/admissions/how-to-apply/"}, b""),
        new: ok_page(),
    })
    result = web.fetch_page(PAGE)
    assert result.ok and result.page.final_url == new


def test_redirect_loop_stops():
    web, _ = access({SITE + "/robots.txt": (200, {}, ROBOTS_ALLOW_USIUBOT),
                     PAGE: (302, {"Location": PAGE}, b"")})
    assert web.fetch_page(PAGE).status == wa.BAD_REDIRECT


@pytest.mark.parametrize("route,expected", [
    (FetchError(wa.TIMEOUT), wa.TIMEOUT),
    (FetchError(wa.UNREACHABLE), wa.UNREACHABLE),
    ((500, {"Content-Type": "text/html"}, b"error"), wa.HTTP_ERROR),
    ((404, {"Content-Type": "text/html"}, b"missing"), wa.HTTP_ERROR),
    ((200, {"Content-Type": "application/pdf"}, b"%PDF-1.7"), wa.NOT_HTML),
    ((200, {"Content-Type": "text/html"}, b"<html><body><p>Hi</p></body></html>"), wa.NO_TEXT),
])
def test_fetch_failures_are_reported(route, expected):
    web, _ = access({SITE + "/robots.txt": (200, {}, ROBOTS_ALLOW_USIUBOT), PAGE: route})
    result = web.fetch_page(PAGE)
    assert result.status == expected and result.page is None


def test_oversized_page_is_rejected():
    web, _ = access({SITE + "/robots.txt": (200, {}, ROBOTS_ALLOW_USIUBOT), PAGE: ok_page(body="x" * 5000)},
                    LIVE_MAX_PAGE_BYTES=1000)
    assert web.fetch_page(PAGE).status == wa.TOO_LARGE


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_page_cache_hit_expiry_and_conditional_refresh():
    clock = Clock()
    web, transport = access({SITE + "/robots.txt": (200, {}, ROBOTS_ALLOW_USIUBOT),
                             PAGE: ok_page(ETag='"v1"')}, clock=clock, LIVE_PAGE_CACHE_SECONDS=100)
    assert web.fetch_page(PAGE).ok
    assert web.fetch_page(PAGE).ok
    assert sum(u == PAGE for u, _ in transport.requests) == 1          # second call served from cache

    clock.now += 101                                                     # expired
    transport.routes[PAGE] = (304, {}, b"")
    result = web.fetch_page(PAGE)
    assert result.ok and "online application system" in result.page.text
    assert transport.requests[-1] == (PAGE, {"If-None-Match": '"v1"'})


def test_failures_are_cached_briefly():
    clock = Clock()
    web, transport = access({SITE + "/robots.txt": (200, {}, ROBOTS_ALLOW_USIUBOT), PAGE: FetchError(wa.TIMEOUT)},
                            clock=clock, LIVE_FAILURE_CACHE_SECONDS=60)
    assert web.fetch_page(PAGE).status == wa.TIMEOUT
    assert web.fetch_page(PAGE).status == wa.TIMEOUT
    assert sum(u == PAGE for u, _ in transport.requests) == 1
    clock.now += 61
    transport.routes[PAGE] = ok_page()
    assert web.fetch_page(PAGE).ok


def test_robots_cache_is_reused():
    web, transport = access({SITE + "/robots.txt": (200, {}, ROBOTS_ALLOW_USIUBOT),
                             PAGE: ok_page(), SITE + "/fees/": ok_page("Fees")})
    web.fetch_page(PAGE)
    web.fetch_page(SITE + "/fees/")
    assert sum(u.endswith("/robots.txt") for u, _ in transport.requests) == 1


def test_ttl_cache_limits_entries_and_bytes():
    cache = TTLCache(max_entries=2, max_bytes=100)
    cache.set("a", 1, 60, 10)
    cache.set("b", 2, 60, 10)
    cache.get("a")                      # a is now most recently used
    cache.set("c", 3, 60, 10)
    assert cache.get("b") is None and cache.get("a") == 1 and cache.get("c") == 3
    cache.set("big", 4, 60, 95)         # evicts until under the byte limit
    assert cache.size_bytes <= 100 and cache.get("big") == 4
    cache.set("huge", 5, 60, 500)       # larger than the whole cache: not stored
    assert cache.get("huge") is None


# --- real HTTP against a local server -------------------------------------------------------------
class _Handler(BaseHTTPRequestHandler):
    pages = {}

    def do_GET(self):  # noqa: N802
        route = self.pages.get(self.path)
        if route == "slow":
            threading.Event().wait(3)
            route = (200, {"Content-Type": "text/html"}, html_page("Slow", BODY))
        if route is None:
            route = (404, {"Content-Type": "text/html"}, b"<html>missing</html>")
        status, headers, body = route
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        # Record before replying: once the body is sent the client may check ``seen`` immediately.
        self.server.seen.append((self.path, self.headers.get("User-Agent")))
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class LocalSiteTransport(wa.RequestsTransport):
    """Real ``requests`` transport, with https://www.usiu.ac.ke rewritten to the local test server.

    The trust and robots rules still see the official URL; only the network address changes.
    """

    def __init__(self, user_agent, base):
        super().__init__(user_agent)
        self.base = base

    def get(self, url, **kwargs):
        parts = urlsplit(url)
        local = self.base + parts.path + ("?" + parts.query if parts.query else "")
        return super().get(local, **kwargs)


@pytest.fixture
def local_site():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.seen = []
    # The client deliberately gives up on the slow page; the server's write then fails harmlessly.
    server.handle_error = lambda request, address: None
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server, f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def test_local_http_end_to_end(local_site):
    server, base = local_site
    _Handler.pages = {
        "/robots.txt": (200, {"Content-Type": "text/plain"}, b"User-agent: USIUBOT\nDisallow: /private/\n"),
        "/how-to-apply/": (200, {"Content-Type": "text/html"}, html_page("How to Apply", BODY)),
        "/private/x/": (200, {"Content-Type": "text/html"}, html_page("Private", BODY)),
        "/moved/": (301, {"Location": "/how-to-apply/"}, b""),
        "/big/": (200, {"Content-Type": "text/html"}, html_page("Big", "y" * 50000)),
        "/slow/": "slow",
    }
    s = settings(LIVE_READ_TIMEOUT=1, LIVE_CONNECT_TIMEOUT=1, LIVE_MAX_PAGE_BYTES=20000)
    web = WebsiteAccess(s, transport=LocalSiteTransport("USIUBOT/1.0", base))

    result = web.fetch_page(SITE + "/how-to-apply/")
    assert result.ok and "online application system" in result.page.text
    assert ("/how-to-apply/", "USIUBOT/1.0") in server.seen

    assert web.fetch_page(SITE + "/private/x/").status == wa.ROBOTS_DISALLOWED
    assert not any(path == "/private/x/" for path, _ in server.seen)

    moved = web.fetch_page(SITE + "/moved/")
    assert moved.ok and moved.page.final_url == SITE + "/how-to-apply/"

    assert web.fetch_page(SITE + "/big/").status == wa.TOO_LARGE
    assert web.fetch_page(SITE + "/slow/").status == wa.TIMEOUT
    assert web.fetch_page(SITE + "/missing/").status == wa.HTTP_ERROR


def test_unreachable_site_is_reported(local_site):
    _, base = local_site
    # Nothing listens on port 9 locally, so the connection is refused.
    web = WebsiteAccess(settings(LIVE_CONNECT_TIMEOUT=1), transport=LocalSiteTransport("USIUBOT/1.0", "http://127.0.0.1:9"))
    assert web.fetch_page(PAGE).status == wa.ROBOTS_UNAVAILABLE
