"""Approved-source registry: URL validation, approval workflow, local index and admin API."""

import datetime
import io

import pytest
from pypdf import PdfWriter
from reportlab.pdfgen import canvas

from config.database import db_instance
from services.sources import (
    LocalIndex,
    SourceError,
    is_stale,
    normalize_source_url,
    parse_source_date,
    tokenize,
)
from tests.conftest import TEST_SOURCES, add_source

ALLOWED = ("usiu.ac.ke",)
BASE = "/api/admin/sources"


# --- URL validation -----------------------------------------------------------------
@pytest.mark.parametrize("url,expected", [
    ("https://www.usiu.ac.ke/how-to-apply/", "https://www.usiu.ac.ke/how-to-apply/"),
    ("https://WWW.USIU.AC.KE/How-To-Apply/#section", "https://www.usiu.ac.ke/How-To-Apply/"),
    ("https://usiu.ac.ke", "https://usiu.ac.ke/"),
    ("https://cx.usiu.ac.ke/ICS/Registrar/?x=1", "https://cx.usiu.ac.ke/ICS/Registrar/?x=1"),
    ("  https://www.usiu.ac.ke:443/page  ", "https://www.usiu.ac.ke/page"),
])
def test_valid_official_urls_are_normalised(url, expected):
    assert normalize_source_url(url, ALLOWED) == expected


@pytest.mark.parametrize("url", [
    "",
    None,
    "http://www.usiu.ac.ke/how-to-apply/",          # not https
    "javascript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "ftp://www.usiu.ac.ke/file.pdf",
    "https://evil.example.com/usiu.ac.ke",
    "https://usiu.ac.ke.evil.com/apply",             # look-alike domain
    "https://notusiu.ac.ke/apply",                   # suffix without a dot boundary
    "https://admin:pw@www.usiu.ac.ke/",              # credentials
    "https://www.usiu.ac.ke@evil.com/",
    "https://www.usiu.ac.ke:8080/apply",             # non-standard port
    "https://www.usiu.ac.ke/a b",                    # whitespace
    "https://www.usiu.ac.ke/\x00",
    "https://www.usiu.ac.ke/" + "a" * 2100,
    "//www.usiu.ac.ke/apply",
    "https://[::1/",
])
def test_invalid_urls_are_rejected(url):
    with pytest.raises(SourceError):
        normalize_source_url(url, ALLOWED)


# --- Dates and staleness ---------------------------------------------------------------
@pytest.mark.parametrize("value", ["2025", "2025-09", "2025-09-30"])
def test_valid_source_dates(value):
    assert parse_source_date(value) == value


@pytest.mark.parametrize("value", ["2025/09", "30-09-2025", "2025-13", "2025-02-30", "September 2025", "2999"])
def test_invalid_source_dates(value):
    with pytest.raises(SourceError):
        parse_source_date(value)


def test_staleness_uses_source_date_then_retrieval_date():
    now = datetime.datetime(2026, 10, 19, tzinfo=datetime.timezone.utc)
    assert is_stale({"source_date": "2024"}, 365, now) is True
    assert is_stale({"source_date": "2025-12"}, 365, now) is False   # a month is judged by its last day
    recent = now - datetime.timedelta(days=30)
    old = now - datetime.timedelta(days=400)
    assert is_stale({"retrieved_at": recent}, 365, now) is False
    assert is_stale({"retrieved_at": old.replace(tzinfo=None)}, 365, now) is True  # naive Mongo datetimes
    assert is_stale({}, 365, now) is True


# --- Approval workflow ---------------------------------------------------------------------
def test_new_sources_start_as_draft_and_are_not_indexed(registry):
    source = add_source(registry, approve=False)
    assert source["status"] == "draft"
    assert db_instance.get_collection("source_chunks").count_documents({}) == 0
    assert registry.retrieve("applications submitted online") == []


def test_approving_indexes_and_archiving_removes(registry):
    source = add_source(registry)
    chunks = db_instance.get_collection("source_chunks")
    assert chunks.count_documents({"source_id": source["_id"]}) >= 1
    assert registry.retrieve("applications submitted online")[0]["source"]["_id"] == source["_id"]

    archived = registry.set_status(str(source["_id"]), "archived", note="superseded")
    assert archived["status"] == "archived"
    assert chunks.count_documents({"source_id": source["_id"]}) == 0
    assert registry.retrieve("applications submitted online") == []
    assert [h["status"] for h in archived["status_history"]] == ["draft", "approved", "archived"]
    assert archived["status_history"][-1]["note"] == "superseded"


def test_source_without_text_cannot_be_approved(registry):
    source = add_source(registry, approve=False, text="")
    with pytest.raises(SourceError, match="needs text"):
        registry.set_status(str(source["_id"]), "approved")


def test_editing_text_of_an_approved_source_requires_reapproval(registry):
    source = add_source(registry)
    updated = registry.update(str(source["_id"]), {"text": "TEST FIXTURE. Completely new wording about bursaries."})
    assert updated["status"] == "draft"
    assert updated["approved_at"] is None
    assert registry.retrieve("bursaries") == []


def test_editing_only_metadata_keeps_approval(registry):
    source = add_source(registry)
    updated = registry.update(str(source["_id"]), {"title": "TEST FIXTURE: Renamed"})
    assert updated["status"] == "approved"
    assert registry.retrieve("applications submitted online")[0]["source"]["title"] == "TEST FIXTURE: Renamed"


def test_duplicate_urls_are_rejected(registry):
    add_source(registry, approve=False)
    with pytest.raises(SourceError, match="already exists"):
        add_source(registry, approve=False,
                   url=TEST_SOURCES[0]["url"].replace("www.usiu.ac.ke", "WWW.USIU.AC.KE") + "#top")


def test_retrieval_rechecks_approval_even_if_index_cache_is_stale(registry):
    source = add_source(registry)
    registry.retrieve("applications submitted online")  # warm the in-memory cache
    db_instance.get_collection("sources").update_one({"_id": source["_id"]}, {"$set": {"status": "archived"}})
    assert registry.retrieve("applications submitted online") == []


def test_source_on_a_domain_removed_from_the_allow_list_is_not_retrieved(registry):
    add_source(registry)
    registry.allowed_domains = ("example.org",)
    assert registry.retrieve("applications submitted online") == []


# --- Local index ------------------------------------------------------------------------------
class FakeCollection:
    def __init__(self, docs):
        self.docs = docs

    def find(self, *args, **kwargs):
        return list(self.docs)


def make_index(texts):
    docs = [{"_id": i, "source_id": f"s{i}", "chunk": 0, "text": t} for i, t in enumerate(texts)]
    return LocalIndex(lambda name: FakeCollection(docs))


def test_bm25_ranks_the_most_relevant_chunk_first():
    index = make_index([
        "The library opens at eight.",
        "Tuition fees are paid per unit each semester. Fees are due before registration.",
        "Clubs and sports are part of student life.",
    ])
    hits = index.search("When are tuition fees due?")
    assert hits[0][0]["source_id"] == "s1"


def test_low_coverage_matches_are_ignored():
    index = make_index(["Students request transcripts in writing.", "The cafeteria serves lunch."])
    assert index.search("hostel curfew rules for international transcripts", min_coverage=0.5) == []
    assert index.search("hostel curfew rules for international transcripts", min_coverage=0.0)


def test_words_common_to_all_university_text_do_not_count_as_a_match():
    index = make_index(["Students request transcripts in writing.", "The campus has a library."])
    assert index.search("gym for students on campus", min_coverage=0.0) == []


def test_each_part_of_a_two_part_question_can_match():
    index = make_index(["Registration opens online.", "Applications are submitted online through the portal."])
    hits = index.search("When does registration open and how are applications submitted?", min_coverage=0.5)
    assert {h[0]["source_id"] for h in hits} == {"s0", "s1"}


def test_empty_index_and_stopword_only_queries_return_nothing():
    assert make_index([]).search("fees") == []
    assert make_index(["Fees are due."]).search("what is the") == []


def test_tokenizer_matches_word_forms():
    assert set(tokenize("apply")) == set(tokenize("applications")) == set(tokenize("applicants"))
    assert set(tokenize("register")) == set(tokenize("registration"))


@pytest.mark.parametrize("text,is_transcript", [
    ("official transcript", True),
    ("transcripts", True),
    ("a copy of my academic record", True),
    ("exam results", False),
    ("KCSE results", False),
    ("results", False),
    ("result", False),
])
def test_only_specific_terms_map_to_the_transcript_concept(text, is_transcript):
    assert ("concepttranscript" in tokenize(text)) is is_transcript


# --- Ranking: relevance and staleness ------------------------------------------------------------
def _ranked(registry, query):
    return [r["source"]["title"] for r in registry.retrieve(query, min_coverage=0.5)]


def _fixture(registry, slug, date, text):
    return add_source(registry, url=f"https://www.usiu.ac.ke/test-fixture/{slug}/", title=slug,
                      source_date=date, text="TEST FIXTURE. " + text)


@pytest.mark.parametrize("first_inserted", ["old", "new"])
def test_current_source_outranks_stale_source_of_equal_relevance(registry, first_inserted):
    versions = {"old": ("2020", "Library opening hours are eight to ten on weekdays."),
                "new": ("2026-06", "Library opening hours are eight to nine on weekdays.")}
    for name in (first_inserted, "new" if first_inserted == "old" else "old"):
        _fixture(registry, name, *versions[name])
    assert _ranked(registry, "What are the library opening hours?") == ["new", "old"]


def test_clearly_more_relevant_stale_source_still_ranks_first(registry):
    _fixture(registry, "old-detailed", "2020",
             "Library opening hours. The library opening hours are eight to ten on weekdays; library "
             "opening hours at weekends are nine to five.")
    _fixture(registry, "new-passing-mention", "2026-06",
             "Orientation week covers the student portal, clubs, chapel, sports, counselling, health "
             "services, the cafeteria menu, parking permits, the library and the opening hours of the gym.")
    results = registry.retrieve("What are the library opening hours?", min_coverage=0.5)
    assert [r["source"]["title"] for r in results] == ["old-detailed", "new-passing-mention"]
    assert results[0]["stale"] is True and results[1]["stale"] is False


def test_date_does_not_reorder_two_current_sources(registry):
    _fixture(registry, "older-but-relevant", "2026-01",
             "Library opening hours. The library opening hours are eight to ten on weekdays.")
    _fixture(registry, "newer-but-vague", "2026-09",
             "Orientation week covers the student portal, clubs, chapel, sports, counselling, health "
             "services, the cafeteria menu, parking permits, the library and the opening hours of the gym.")
    assert _ranked(registry, "What are the library opening hours?") == ["older-but-relevant", "newer-but-vague"]


def test_ranking_score_is_relevance_times_the_stale_penalty(registry):
    _fixture(registry, "old", "2020", "Library opening hours are eight to ten on weekdays.")
    _fixture(registry, "new", "2026-06", "Library opening hours are eight to nine on weekdays.")
    results = {r["source"]["title"]: r for r in registry.retrieve("library opening hours")}
    assert results["new"]["score"] == results["new"]["relevance"]
    assert results["old"]["score"] == pytest.approx(results["old"]["relevance"] * 0.85)
    registry.settings = {**registry.settings, "SOURCE_STALE_PENALTY": 1.0}
    assert all(r["score"] == r["relevance"] for r in registry.retrieve("library opening hours"))


# --- Admin API ------------------------------------------------------------------------------------
def payload(**overrides):
    return {**TEST_SOURCES[0], **overrides}


def _text_pdf(text):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(72, 720, text)
    pdf.save()
    return buffer.getvalue()


def test_admin_can_create_list_approve_and_archive(client, admin_headers):
    created = client.post(BASE, json=payload(), headers=admin_headers)
    assert created.status_code == 201
    source = created.get_json()["source"]
    assert source["status"] == "draft" and source["has_text"] is True
    assert source["url"] == TEST_SOURCES[0]["url"]
    assert source["department"] == "admissions" and source["source_date"] == "2026-01"
    assert source["retrieved_at"]
    assert "text" not in source

    listed = client.get(BASE + "?status=draft", headers=admin_headers).get_json()["sources"]
    assert [s["id"] for s in listed] == [source["id"]]
    assert client.get(BASE + "?status=approved", headers=admin_headers).get_json()["sources"] == []

    approved = client.post(f"{BASE}/{source['id']}/status", json={"status": "approved"}, headers=admin_headers)
    assert approved.status_code == 200
    assert approved.get_json()["source"]["status"] == "approved"
    assert approved.get_json()["source"]["approved_by"] == "admin"

    detail = client.get(f"{BASE}/{source['id']}", headers=admin_headers).get_json()["source"]
    assert detail["text"].startswith("TEST FIXTURE")
    assert [h["status"] for h in detail["status_history"]] == ["draft", "approved"]

    archived = client.post(f"{BASE}/{source['id']}/status", json={"status": "archived"}, headers=admin_headers)
    assert archived.get_json()["source"]["status"] == "archived"


@pytest.mark.parametrize("bad,message", [
    ({"url": "http://www.usiu.ac.ke/x"}, "https"),
    ({"url": "https://evil.example.com/x"}, "approved USIU-Africa domain"),
    ({"url": "javascript:alert(1)"}, "https"),
    ({"title": ""}, "Title"),
    ({"department": "bursary"}, "Department"),
    ({"content_type": "docx"}, "Content type"),
    ({"source_date": "last year"}, "Source date"),
    ({"retrieved_at": "2999-01-01"}, "future"),
    ({"text": "x" * 200_001}, "Text"),
])
def test_invalid_source_data_is_rejected(client, admin_headers, bad, message):
    response = client.post(BASE, json=payload(**bad), headers=admin_headers)
    assert response.status_code == 400
    assert message in response.get_json()["error"]
    assert db_instance.get_collection("sources").count_documents({}) == 0


def test_invalid_status_and_unknown_ids(client, admin_headers):
    source_id = client.post(BASE, json=payload(), headers=admin_headers).get_json()["source"]["id"]
    assert client.post(f"{BASE}/{source_id}/status", json={"status": "published"},
                       headers=admin_headers).status_code == 400
    assert client.get(f"{BASE}/not-an-id", headers=admin_headers).status_code == 404
    assert client.get(f"{BASE}/650000000000000000000000", headers=admin_headers).status_code == 404
    assert client.put(f"{BASE}/650000000000000000000000", json={"title": "x"},
                      headers=admin_headers).status_code == 404
    assert client.post(f"{BASE}/650000000000000000000000/status", json={"status": "approved"},
                       headers=admin_headers).status_code == 404
    assert client.get(BASE + "?department=bursary", headers=admin_headers).status_code == 400


def test_duplicate_url_returns_400(client, admin_headers):
    client.post(BASE, json=payload(), headers=admin_headers)
    response = client.post(BASE, json=payload(title="Another"), headers=admin_headers)
    assert response.status_code == 400
    assert "already exists" in response.get_json()["error"]


def test_pdf_upload_extracts_text_without_cloud_storage(client, admin_headers, storage):
    data = {k: v for k, v in payload(url="https://www.usiu.ac.ke/test-fixture/guide.pdf").items() if k != "text"}
    data["file"] = (io.BytesIO(_text_pdf("TEST FIXTURE scholarship guide")), "guide.pdf")
    response = client.post(BASE, data=data, headers=admin_headers, content_type="multipart/form-data")
    assert response.status_code == 201
    source = response.get_json()["source"]
    assert source["content_type"] == "pdf" and source["has_text"] is True
    assert storage.uploaded == []  # nothing is sent to Cloudinary


@pytest.mark.parametrize("filename,content,message", [
    ("guide.txt", b"%PDF-1.4", "Only PDF"),
    ("guide.pdf", b"not a pdf", "not a valid PDF"),
])
def test_bad_pdf_uploads_are_rejected(client, admin_headers, filename, content, message):
    data = {k: v for k, v in payload().items() if k != "text"}
    data["file"] = (io.BytesIO(content), filename)
    response = client.post(BASE, data=data, headers=admin_headers, content_type="multipart/form-data")
    assert response.status_code == 400
    assert message in response.get_json()["error"]


def test_pdf_without_extractable_text_is_rejected(client, admin_headers):
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buffer = io.BytesIO()
    writer.write(buffer)
    data = {k: v for k, v in payload().items() if k != "text"}
    data["file"] = (io.BytesIO(buffer.getvalue()), "scan.pdf")
    response = client.post(BASE, data=data, headers=admin_headers, content_type="multipart/form-data")
    assert response.status_code == 400
    assert "no extractable text" in response.get_json()["error"]


def test_update_via_api_sends_changed_content_back_to_draft(client, admin_headers):
    source_id = client.post(BASE, json=payload(), headers=admin_headers).get_json()["source"]["id"]
    client.post(f"{BASE}/{source_id}/status", json={"status": "approved"}, headers=admin_headers)
    response = client.put(f"{BASE}/{source_id}", json={"text": "TEST FIXTURE. New text."}, headers=admin_headers)
    assert response.status_code == 200
    assert response.get_json()["source"]["status"] == "draft"


def test_non_json_body_is_rejected(client, admin_headers):
    response = client.post(BASE, data="url=x", headers=admin_headers, content_type="text/plain")
    assert response.status_code == 400


# --- Multi-part questions and spelling variants ----------------------------------------------------
def test_british_and_american_spellings_match():
    assert tokenize("Which programmes do you offer?") == tokenize("Which programs do you offer?")
    assert tokenize("programme") == tokenize("Program")
    assert tokenize("the student centre") == tokenize("the student center")


def test_questions_split_at_sentences_and_commas_but_not_inside_numbers():
    from services.sources import PART_SPLIT_RE

    assert len(PART_SPLIT_RE.split("I'm a prospective student. Which programmes do you offer, the requirements?")) == 4
    assert PART_SPLIT_RE.split("The fee is KES 3,500 for undergraduates") == ["The fee is KES 3,500 for undergraduates"]
    assert PART_SPLIT_RE.split("See e.g.the brochure") == ["See e.g.the brochure"]


def _topic_sources(registry):
    _fixture(registry, "requirements-undergraduate", "2026-06",
             "Admission requirements for undergraduate applicants: the admission requirements are KCSE C+ "
             "or an equivalent. Admission requirements are checked by the admissions office.")
    _fixture(registry, "requirements-graduate", "2026-06",
             "Admission requirements for graduate applicants: admission requirements include a bachelor's "
             "degree. Admission requirements differ by school.")
    _fixture(registry, "requirements-international", "2026-06",
             "Admission requirements: international admission requirements. Admission requirements, "
             "admission requirements and English admission requirements.")
    _fixture(registry, "programme-list", "2026-06",
             "Undergraduate Programs: Bachelor of Science in Accounting, Bachelor of Arts in Journalism, "
             "Bachelor of Pharmacy.")


def test_every_part_of_a_multi_part_question_gets_a_source(registry):
    _topic_sources(registry)
    question = "Which undergraduate programmes do you offer, and what are the admission requirements?"
    titles = [r["source"]["title"] for r in registry.retrieve(question, k=2, min_coverage=0.5)]
    assert "programme-list" in titles  # not crowded out by the two strong requirement sources
    assert any(t.startswith("requirements-") for t in titles)
    assert len(titles) == 2


def test_part_coverage_keeps_the_best_source_of_a_weaker_part():
    from services.sources import SourceRegistry

    ranked = [{"name": "A", "_parts": {0: 5.0, 2: 4.0}}, {"name": "B", "_parts": {2: 3.9}},
              {"name": "C", "_parts": {2: 3.8}}, {"name": "P", "_parts": {1: 1.0}}]
    assert [e["name"] for e in SourceRegistry._cover_question_parts(ranked, 2)] == ["A", "P"]
    assert [e["name"] for e in SourceRegistry._cover_question_parts(ranked, 3)] == ["A", "B", "P"]
    # More parts than places: the strongest parts win, and ranking order is kept.
    assert [e["name"] for e in SourceRegistry._cover_question_parts(ranked, 1)] == ["A"]
    # Single-part question (only the whole question, part 0): plain top k.
    single = [{"name": n, "_parts": {0: s}} for n, s in (("A", 3.0), ("B", 2.0), ("C", 1.0))]
    assert [e["name"] for e in SourceRegistry._cover_question_parts(single, 2)] == ["A", "B"]


def test_single_part_question_ranking_is_unchanged(registry):
    _topic_sources(registry)
    titles = [r["source"]["title"] for r in registry.retrieve("What are the admission requirements",
                                                             k=2, min_coverage=0.5)]
    assert "programme-list" not in titles and all(t.startswith("requirements-") for t in titles)


def test_retrieve_results_do_not_expose_internal_part_scores(registry):
    _topic_sources(registry)
    results = registry.retrieve("Which programmes do you offer, and the admission requirements?", min_coverage=0.5)
    assert results and all("_parts" not in r for r in results)
