"""Hybrid collection: permitted sources are collected, everything else stays available as an
official link with a precise reason. All network access is faked and all content is synthetic
test text, not USIU-Africa information. Passing tests say nothing about the live website."""

import json

import pytest

from services import chat_service as cs
from services.live_retrieval import OfficialPageCatalogue
from services.web_access import WebsiteAccess
from tests.conftest import ROBOTS_DENY_ALL, FakeTransport
from tests.test_knowledge_sources import (HTML_PAGE, LONG_TEXT, OFFICIAL, PDF_A, PERMISSIVE_ROBOTS, USIU_ROBOTS,
                                          FakeFetcher, fetcher_with, imported, pdf_seed, register, run_download,
                                          text_pdf)
from tools import knowledge_sources as ks

HTML = "text/html; charset=utf-8"


@pytest.fixture
def root(tmp_path):
    return ks.ensure_structure(tmp_path / "usiubot_knowledge")


def page_seed(path, title="Synthetic page", category="admissions", **extra):
    return {"title": title, "url": f"{OFFICIAL}/{path}", "content_type": "html", "category": category, **extra}


def source_of(inventory, path):
    return inventory.sources[ks.normalize_url(f"{OFFICIAL}/{path}")]


def html_with(body, head=""):
    return (f"<!DOCTYPE html><html><head><title>T</title>{head}</head><body><main>{body}</main></body></html>"
            ).encode()


SYNTHETIC_BODY = "<h1>Synthetic heading</h1><p>" + "Synthetic test content, not USIU-Africa information. " * 4 + "</p>"


class SequenceFetcher(FakeFetcher):
    """Like FakeFetcher, but a URL can map to a list of responses returned in turn."""

    def get(self, url):
        response = self.responses.get(url)
        if isinstance(response, list):
            self.requested.append(url)
            item = response.pop(0) if len(response) > 1 else response[0]
            if isinstance(item, Exception):
                raise item
            return item
        return super().get(url)


# --- Permitted collection -------------------------------------------------------------------
def test_permitted_html_page_is_collected_with_metadata(root):
    head = f'<link rel="canonical" href="{OFFICIAL}/how-to-apply/">'
    fetcher = fetcher_with(**{"how-to-apply/?utm=x": (200, HTML, html_with(SYNTHETIC_BODY, head))})
    source = source_of(run_download(root, [page_seed("how-to-apply/?utm=x")], fetcher), "how-to-apply/?utm=x")
    assert source.download_status == ks.DOWNLOADED and source.local_path
    assert source.canonical_url == f"{OFFICIAL}/how-to-apply/"
    assert source.content_hash and source.last_checked and source.retrieved_on == ks.today()
    assert source.failure_reason == "" and source.link_only is False
    assert source.review_status == "pending"  # collected is not approved

    inventory = ks.Inventory(root)
    ks.extract_all(inventory, root)
    inventory.save()
    source = source_of(ks.Inventory(root), "how-to-apply/?utm=x")
    assert source.extraction_status == ks.EXTRACTED and source.last_extracted
    assert "Synthetic heading" in (root / source.text_path).read_text(encoding="utf-8")


def test_permitted_pdf_is_downloaded_and_its_text_extracted(root):
    fetcher = fetcher_with(**{"guide.pdf": (200, "application/pdf", text_pdf(LONG_TEXT))})
    run_download(root, [pdf_seed("guide.pdf")], fetcher)
    inventory = ks.Inventory(root)
    ks.extract_all(inventory, root)
    source = source_of(inventory, "guide.pdf")
    assert source.download_status == ks.DOWNLOADED and source.extraction_status == ks.EXTRACTED
    assert source.content_hash == ks.normalized_text_hash((root / source.text_path).read_text(encoding="utf-8"))
    assert source.last_extracted and source.url == f"{OFFICIAL}/guide.pdf"


# --- Not collected: link only, with the precise reason ----------------------------------------
def test_robots_disallowed_sources_become_link_only(root):
    fetcher = fetcher_with(robots=USIU_ROBOTS, **{"how-to-apply/": (200, HTML, HTML_PAGE)})
    source = source_of(run_download(root, [page_seed("how-to-apply/")], fetcher), "how-to-apply/")
    assert source.download_status == ks.ROBOTS_DISALLOWED
    assert source.link_only is True and source.url == f"{OFFICIAL}/how-to-apply/"
    assert "robots.txt" in source.failure_reason and source.last_checked
    assert fetcher.requested == [f"{OFFICIAL}/robots.txt"]  # the page itself was never requested


def test_older_inventory_statuses_are_migrated(root):
    inventory_file = root / ks.METADATA_DIR / ks.INVENTORY_FILE
    inventory_file.write_text(json.dumps({"sources": [{
        "title": "Old", "url": f"{OFFICIAL}/old/", "content_type": "html", "category": "admissions",
        "download_status": "blocked_by_robots_txt", "a_field_from_the_future": 1}]}), encoding="utf-8")
    assert source_of(ks.Inventory(root), "old/").download_status == ks.ROBOTS_DISALLOWED


@pytest.mark.parametrize("response, status", [
    ((403, HTML, b"forbidden"), ks.ACCESS_DENIED),
    ((401, HTML, b"sign in"), ks.LOGIN_REQUIRED),
    ((200, HTML, b"<html>x</html>", f"{OFFICIAL}/wp-login.php?redirect=x"), ks.LOGIN_REQUIRED),
    ((200, HTML, b"", "https://cx.usiu.ac.ke/ics/"), ks.LOGIN_REQUIRED),
    ((200, HTML, html_with(SYNTHETIC_BODY + '<input type="password" name="p">')), ks.LOGIN_REQUIRED),
    ((200, HTML, b"", "https://example.com/elsewhere"), ks.FAILED),
    ((404, HTML, b"not found"), ks.NOT_FOUND),
    ((410, HTML, b"gone"), ks.NOT_FOUND),
])
def test_access_denied_login_and_missing_pages_are_told_apart(root, response, status):
    fetcher = fetcher_with(**{"page/": response})
    source = source_of(run_download(root, [page_seed("page/")], fetcher), "page/")
    assert source.download_status == status
    assert source.failure_reason and source.local_path == ""
    assert fetcher.requested.count(f"{OFFICIAL}/page/") == 1  # not transient: never retried
    assert source.link_only is (status != ks.NOT_FOUND)


@pytest.mark.parametrize("failure, status", [
    (TimeoutError("timed out"), ks.TIMEOUT),
    (type("ReadTimeout", (Exception,), {})("slow"), ks.TIMEOUT),
    (ConnectionError("reset"), ks.UNREACHABLE),
    ((503, HTML, b"busy"), ks.SERVER_ERROR),
    ((429, HTML, b"slow down"), ks.SERVER_ERROR),
])
def test_transient_failures_are_retried_within_the_limit(root, failure, status):
    fetcher = SequenceFetcher({f"{OFFICIAL}/robots.txt": (200, "text/plain", PERMISSIVE_ROBOTS),
                               f"{OFFICIAL}/page/": [failure]})
    source = source_of(run_download(root, [page_seed("page/")], fetcher), "page/")
    assert source.download_status == status and source.link_only is True
    assert fetcher.requested.count(f"{OFFICIAL}/page/") == ks.MAX_ATTEMPTS
    assert f"after {ks.MAX_ATTEMPTS} attempts" in source.failure_reason


def test_transient_failure_followed_by_success_is_collected(root):
    fetcher = SequenceFetcher({f"{OFFICIAL}/robots.txt": (200, "text/plain", PERMISSIVE_ROBOTS),
                               f"{OFFICIAL}/page/": [(503, HTML, b"busy"), (200, HTML, html_with(SYNTHETIC_BODY))]})
    delays = []
    inventory = ks.Inventory(root)
    ks.import_seeds(inventory, [page_seed("page/")])
    ks.download_sources(inventory, fetcher, ks.RobotsPolicy(fetcher), root, retry_delay=7, sleep=delays.append)
    assert source_of(inventory, "page/").download_status == ks.DOWNLOADED
    assert delays == [7]


@pytest.mark.parametrize("seed, response, status", [
    (page_seed("empty/"), (200, HTML, b""), ks.EMPTY_CONTENT),
    (page_seed("empty/"), (200, HTML, html_with("<p> </p>")), ks.EMPTY_CONTENT),
    (pdf_seed("empty/"), (200, "application/pdf", b"  "), ks.EMPTY_CONTENT),
    (pdf_seed("empty/"), (200, "application/pdf", b"PK\x03\x04 a zip file"), ks.INVALID_FILE),
    (page_seed("empty/"), (200, "image/png", b"\x89PNG"), ks.INVALID_FILE),
    (pdf_seed("empty/"), ks.TooLarge("the file exceeds the size limit"), ks.INVALID_FILE),
])
def test_empty_and_invalid_files_are_not_stored(root, seed, response, status):
    fetcher = fetcher_with(**{"empty/": response})
    source = source_of(run_download(root, [seed], fetcher), "empty/")
    assert source.download_status == status and source.local_path == ""
    assert not list((root / seed["category"]).iterdir())


def test_redirect_to_a_disallowed_page_is_not_kept(root):
    robots = b"User-agent: *\nDisallow: /private/\nAllow: /\n"
    fetcher = fetcher_with(robots=robots, **{"page/": (200, HTML, html_with(SYNTHETIC_BODY), f"{OFFICIAL}/private/x")})
    source = source_of(run_download(root, [page_seed("page/")], fetcher), "page/")
    assert source.download_status == ks.ROBOTS_DISALLOWED and source.local_path == ""


# --- Duplicates ----------------------------------------------------------------------------
def test_duplicate_content_and_canonical_urls_are_stored_once(root):
    same_text = html_with(SYNTHETIC_BODY)
    other_markup = html_with(SYNTHETIC_BODY.replace("<p>", "<p class='x'>"))
    canonical_copy = html_with("<p>A different synthetic print view of the same page, long enough to count.</p>",
                               f'<link rel="canonical" href="{OFFICIAL}/a/">')
    fetcher = fetcher_with(**{"a/": (200, HTML, same_text), "b/": (200, HTML, other_markup),
                              "a/print/": (200, HTML, canonical_copy)})
    inventory = run_download(root, [page_seed("a/"), page_seed("b/"), page_seed("a/print/"),
                                    page_seed("a/#section")], fetcher)
    assert len(inventory.sources) == 3  # "a/#section" is the same URL as "a/"
    assert source_of(inventory, "a/").download_status == ks.DOWNLOADED
    for path in ("b/", "a/print/"):
        duplicate = source_of(inventory, path)
        assert duplicate.download_status == ks.DUPLICATE and duplicate.local_path == ""
        assert f"{OFFICIAL}/a/" in duplicate.failure_reason and duplicate.link_only is False
    assert len(list((root / "admissions").iterdir())) == 1


# --- Domains and URLs ----------------------------------------------------------------------
@pytest.mark.parametrize("url", [
    "http://www.usiu.ac.ke/plain-http/",
    f"{OFFICIAL}/wp-login.php",
    f"{OFFICIAL}/?s=fees",
    "https://cx.usiu.ac.ke/ics/",
    "https://evil.example/usiu.ac.ke/",
])
def test_non_approved_urls_are_never_fetched(root, url):
    fetcher = fetcher_with()
    inventory = run_download(root, [{"title": "X", "url": url, "content_type": "html", "category": "admissions"}],
                             fetcher)
    (source,) = inventory.sources.values()
    assert source.download_status == ks.NOT_OFFICIAL
    assert fetcher.requested == [f"{OFFICIAL}/robots.txt"]
    assert source.link_only is False  # never offered as an official page either


# --- Existing content is protected -----------------------------------------------------------
def test_collected_sources_are_not_refetched_or_replaced_by_a_failure(root):
    run_download(root, [page_seed("page/")], fetcher_with(**{"page/": (200, HTML, html_with(SYNTHETIC_BODY))}))
    failing = fetcher_with(**{"page/": (500, HTML, b"")})
    source = source_of(run_download(root, [], failing), "page/")
    assert source.download_status == ks.DOWNLOADED and failing.requested == [f"{OFFICIAL}/robots.txt"]
    assert (root / source.local_path).read_bytes() == html_with(SYNTHETIC_BODY)


def test_approved_content_is_not_overwritten_by_empty_or_failed_extraction(root, tmp_path, registry):
    inventory = register(root, tmp_path, "guide.txt", LONG_TEXT.encode())
    ks.extract_all(inventory, root)
    _, inventory = imported(root, inventory, registry)
    (source,) = inventory.sources.values()
    registry.set_status(source.registry_id, "approved")

    (root / source.local_path).write_bytes(b"\xff\xfe not utf-8")  # the file is damaged later
    ks.extract_all(inventory, root, force=True)
    results, inventory = imported(root, inventory, registry)
    assert results == {ks.REG_SKIPPED: 1}
    approved = registry.get(source.registry_id)
    assert approved["status"] == "approved" and "register for courses online" in approved["text"]

    ks.archive_source(inventory, source.url, "superseded")
    results, _ = imported(root, inventory, registry)
    assert results == {ks.REG_SKIPPED: 1} and registry.get(source.registry_id)["text"] == approved["text"]


def test_link_only_and_unreviewed_content_never_reach_the_knowledge_base(root, registry):
    run_download(root, [page_seed("blocked/")], fetcher_with(robots=USIU_ROBOTS))
    inventory = ks.Inventory(root)
    assert ks.import_to_registry(inventory, root, registry) == {}
    assert registry.sources.count_documents({}) == 0 and registry.retrieve("synthetic") == []


# --- Manual capture --------------------------------------------------------------------------
def test_manual_capture_keeps_the_original_url_and_timestamps(root, tmp_path):
    saved = html_with(SYNTHETIC_BODY, f'<link rel="canonical" href="{OFFICIAL}/real-page/">')
    inventory = register(root, tmp_path, "saved.html", saved, url=f"{OFFICIAL}/some-other-page/")
    (source,) = inventory.sources.values()
    assert source.download_status == ks.MANUAL and source.url == f"{OFFICIAL}/some-other-page/"
    assert source.retrieved_on == ks.today() and source.imported_on
    assert any(f"{OFFICIAL}/real-page/" in note for note in source.notes)  # flagged for the reviewer


def test_manual_capture_requires_an_https_source_url(root, tmp_path):
    (tmp_path / "a.txt").write_text(LONG_TEXT, encoding="utf-8")
    with pytest.raises(ValueError, match="https"):
        ks.register_local_file(ks.Inventory(root), root, tmp_path / "a.txt", "registrar", "www.usiu.ac.ke/a", "A")


# --- Official link catalogue -------------------------------------------------------------------
def test_sync_adds_linkable_official_sources_without_touching_reviewed_entries(root, tmp_path):
    catalogue = tmp_path / "official_pages.json"
    reviewed = {"url": f"{OFFICIAL}/blocked/", "title": "Reviewed title", "department": "admissions",
                "keywords": ["k"], "reviewed": True, "notes": []}
    catalogue.write_text(json.dumps({"about": "test", "pages": [reviewed]}), encoding="utf-8")
    seeds = [page_seed("blocked/", title="Inventory title"), page_seed("new/", title="New page"),
             pdf_seed("fees-2026.pdf", category="admissions", title="Fees 2026"),
             {**pdf_seed("fees-2018.pdf", category="admissions", title="Fees 2018"),
              "review_status": "likely_outdated"},
             page_seed("unsorted/", category="pending_review"),
             {"title": "Elsewhere", "url": "https://example.com/x/", "content_type": "html", "category": "marketing"}]
    inventory = run_download(root, seeds, fetcher_with(robots=USIU_ROBOTS))
    ks.archive_source(inventory, f"{OFFICIAL}/new/", "withdrawn")
    ks.import_seeds(inventory, [page_seed("current/", title="Current page")])

    added = ks.sync_catalogue(inventory, catalogue)
    assert added == [f"{OFFICIAL}/current/", f"{OFFICIAL}/fees-2026.pdf"]
    pages = json.loads(catalogue.read_text(encoding="utf-8"))["pages"]
    assert pages[0] == reviewed  # existing entries are never changed
    assert all(p["reviewed"] is False for p in pages[1:])
    assert ks.sync_catalogue(inventory, catalogue) == []  # idempotent

    web = WebsiteAccess({"TRUSTED_SOURCE_HOSTS": ["www.usiu.ac.ke"]}, transport=FakeTransport({}))
    loaded = OfficialPageCatalogue.load(str(catalogue), web.is_trusted)
    assert [e["url"] for e in loaded.entries] == [p["url"] for p in pages]


# --- Chatbot link-only replies -------------------------------------------------------------------
def test_link_only_reply_names_the_official_page_and_links_only_to_it(make_app, tmp_path, monkeypatch):
    url = f"{OFFICIAL}/admission-requirements/"
    catalogue = tmp_path / "official_pages.json"
    catalogue.write_text(json.dumps({"pages": [
        {"url": url, "title": "Admission Requirements", "department": "admissions",
         "keywords": ["requirements", "admission"], "reviewed": False}]}), encoding="utf-8")
    transport = FakeTransport({f"{OFFICIAL}/robots.txt": (200, {}, ROBOTS_DENY_ALL)})
    app = make_app(LIVE_RETRIEVAL_ENABLED=True, OFFICIAL_PAGES_FILE=str(catalogue),
                   website_access=WebsiteAccess({"TRUSTED_SOURCE_HOSTS": ["www.usiu.ac.ke"]}, transport=transport))
    body = app.test_client().post("/api/query", json={"question": "What are the admission requirements?"}).get_json()
    assert body["status"] == "unanswered" and body["verified"] is False and body["citations"] == []
    assert "“Admission Requirements”" in body["answer"] and "couldn't verify" in body["answer"]
    assert "http" not in body["answer"]  # the link is sent separately, never invented in the text
    assert [p["url"] for p in body["places_to_look"]] == [url]
    assert body["places_to_look"][0]["verified"] is False


@pytest.mark.parametrize("title", ["[Click](https://evil.example/)", "Fees <script>x</script>",
                                   "Visit www.evil.example now", "javascript:alert(1)"])
def test_link_only_message_shows_the_title_as_plain_text(title):
    message = cs.link_only_message(title)
    for unsafe in ("](", "<", "evil.example", "javascript:", "https://"):
        assert unsafe not in message
