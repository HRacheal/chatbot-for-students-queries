"""Direct-link fallbacks, official link management, source review and index rebuilding.

The link-matching tests use the repository's real page catalogue (``config/official_pages.json``:
titles, URLs and keywords only). No network request is made and no page content is involved,
so these tests show which official page USIUBOT would suggest, not that the page is current.
"""

import json

import pytest

from services import chat_service as cs
from tests.conftest import TEST_SOURCES, add_source

SITE = "https://www.usiu.ac.ke"


def ask(client, question, headers=None):
    response = client.post("/api/query", json={"question": question}, headers=headers or {})
    assert response.status_code == 200
    return response.get_json()


# --- Specific official pages for realistic questions (real catalogue) --------------------------------------
@pytest.mark.parametrize("question, expected_path", [
    ("What are the admission requirements for undergraduate programmes?", "/admission-requirements/"),
    ("What are the masters admission requirements?", "/116/masters-admissions-requirements/"),
    ("How do I apply to USIU-Africa?", "/how-to-apply/"),
    ("How much is tuition?", "/tuition-fees/"),
    ("What are the fees for nursing?", "/resource/bsc-nursing-fee-schedule/"),
    ("Can I get financial aid?", "/financial-aid/"),
    ("What undergraduate degrees are offered?", "/academics/undergraduate-programs/"),
    ("What are the requirements for the BSc in Applied Computer Technology?",
     "/programs/bachelor-of-science-in-applied-computer-technology/"),
    ("Where is the academic calendar?", "/academic-catalog-academic-calendar-fee-schedule/"),
    ("How do I register for courses?", "/749/registration-policies-procedures/"),
    ("How do I request my transcript?", "/request-transcript/"),
    ("Where can I find the student handbook?", "/assets/file/266ac45d-student-handbook.pdf"),
    ("Where can I get the application form?", "/849/application-forms/"),
    ("Where is the library?", "/academics/library-and-e-resources/"),
    ("How can I contact the university?", "/about-us/contact-us/"),
    ("Where is the campus located?", "/76/where-find-us-contact/"),
    ("Requirements for international students", "/international-applicants/"),
])
def test_the_most_specific_official_page_is_suggested(app, question, expected_path):
    places = app.extensions["chat_service"].places_to_look(question)
    assert places, question
    assert places[0]["url"] == SITE + expected_path
    assert places[0]["verified"] is False and places[0]["reason"]


@pytest.mark.parametrize("question", ["How can I contact the university?", "Tell me about USIU-Africa",
                                      "What is the USIU-Africa website?"])
def test_the_home_page_is_never_suggested(app, question):
    assert all(p["url"] != SITE + "/" for p in app.extensions["chat_service"].places_to_look(question))


def test_unsupported_question_gets_the_specific_link_not_an_invented_answer(client):
    body = ask(client, "How do I request my transcript?")
    assert body["status"] == "unanswered" and body["verified"] is False and body["citations"] == []
    assert body["places_to_look"][0]["url"] == SITE + "/request-transcript/"
    assert "“Request Transcript”" in body["answer"]
    assert "transcript" in body["places_to_look"][0]["reason"].lower()


def test_no_suitable_link_gets_an_honest_reply(client):
    body = ask(client, "When is the graduation ceremony?")  # no graduation page in the catalogue
    assert body["status"] == "unanswered" and body["places_to_look"] == []
    assert body["answer"] == cs.UNANSWERED_MESSAGE + cs.FOLLOW_UP_STAFF and "don't know a specific official page" in body["answer"]


def test_unrelated_questions_get_no_university_information(client):
    body = ask(client, "What is the capital of France?")
    assert body["status"] == "out_of_scope" and body["citations"] == [] and "places_to_look" not in body


def test_staff_reply_email_is_promised_only_when_it_can_be_sent(client, app, user_headers):
    assert ask(client, "How do I request my transcript?", user_headers)["staff_reply_by_email"] is False
    app.extensions["chat_service"].staff_reply_email_available = lambda: True
    assert ask(client, "How do I request my transcript?", user_headers)["staff_reply_by_email"] is True
    assert ask(client, "How do I request my transcript?")["staff_reply_by_email"] is False  # anonymous


# --- Official link management ---------------------------------------------------------------
LINKS = "/api/admin/official-links"


def test_admin_can_add_review_and_hide_official_links(client, admin_headers):
    listing = client.get(LINKS, headers=admin_headers).get_json()
    assert listing["counts"]["total"] == len(listing["links"]) > 50
    assert all(link["trusted"] for link in listing["links"])

    new = {"url": SITE + "/test-fixture/graduation/", "title": "TEST FIXTURE Graduation", "department": "registrar",
           "keywords": ["graduation", "ceremony"], "reviewed": True}
    saved = client.post(LINKS, json=new, headers=admin_headers)
    assert saved.status_code == 200 and saved.get_json()["link"]["origin"] == "admin"
    body = ask(client, "When is the graduation ceremony?")
    assert body["places_to_look"][0]["url"] == new["url"]

    hidden = client.post(LINKS, json={"url": new["url"], "hidden": True}, headers=admin_headers).get_json()["link"]
    assert hidden["hidden"] is True and hidden["title"] == new["title"]  # other fields kept
    assert ask(client, "When is the graduation ceremony?")["places_to_look"] == []

    edited = client.post(LINKS, json={"url": SITE + "/request-transcript/", "title": "Request a Transcript",
                                      "reviewed": True}, headers=admin_headers).get_json()["link"]
    assert edited["origin"] == "file+admin" and edited["reviewed"] is True
    assert ask(client, "How do I request my transcript?")["places_to_look"][0]["title"] == "Request a Transcript"


@pytest.mark.parametrize("data", [
    {"url": "https://evil.example/fees", "title": "Fees", "department": "admissions"},
    {"url": "http://www.usiu.ac.ke/fees/", "title": "Fees", "department": "admissions"},
    {"url": "https://cx.usiu.ac.ke/ics/", "title": "Portal", "department": "registrar"},
    {"url": "https://www.usiu.ac.ke/wp-login.php", "title": "Login", "department": "registrar"},
    {"url": "javascript:alert(1)", "title": "x", "department": "admissions"},
    {"url": SITE + "/new/", "title": "", "department": "admissions"},
    {"url": SITE + "/new/", "title": "New", "department": "bursary"},
    {"url": SITE + "/new/", "title": "New", "department": "admissions", "reviewed": "yes"},
    {"url": SITE + "/new/", "title": "New", "department": "admissions", "keywords": ["x" * 61]},
])
def test_invalid_or_untrusted_links_are_rejected(client, admin_headers, data):
    assert client.post(LINKS, json=data, headers=admin_headers).status_code == 400


def test_link_preview_shows_what_users_would_be_offered(client, admin_headers):
    body = client.get(LINKS + "/preview?q=How do I request my transcript?", headers=admin_headers).get_json()
    assert body["places_to_look"][0]["url"] == SITE + "/request-transcript/"
    assert client.get(LINKS + "/preview", headers=admin_headers).status_code == 400


def test_link_changes_are_stored_in_the_database_not_the_config_file(app, client, admin_headers):
    path = app.extensions["official_links"].path
    before = open(path, encoding="utf-8").read()
    client.post(LINKS, json={"url": SITE + "/request-transcript/", "hidden": True}, headers=admin_headers)
    assert open(path, encoding="utf-8").read() == before
    assert app.extensions["official_links"].collection.count_documents({}) == 1


# --- Source review: approve, reject, archive; duplicates; index rebuild -------------------------------
def test_rejected_and_archived_sources_are_never_retrieved(registry):
    source = add_source(registry)
    assert registry.retrieve("applications submitted online")
    registry.set_status(str(source["_id"]), "rejected", note="Not an official page")
    assert registry.retrieve("applications submitted online") == []
    assert registry.get(str(source["_id"]))["status_history"][-1]["note"] == "Not an official page"
    registry.set_status(str(source["_id"]), "approved")
    registry.set_status(str(source["_id"]), "archived")
    assert registry.retrieve("applications submitted online") == []


def test_admin_can_reject_a_source_over_the_api(client, registry, admin_headers):
    source = add_source(registry, approve=False)
    response = client.post(f"/api/admin/sources/{source['_id']}/status", json={"status": "rejected"},
                           headers=admin_headers)
    assert response.status_code == 200 and response.get_json()["source"]["status"] == "rejected"
    assert client.get("/api/admin/sources?status=rejected", headers=admin_headers).get_json()["sources"]


def test_a_source_with_the_same_text_as_another_is_flagged(registry):
    add_source(registry)
    copy = add_source(registry, approve=False, url="https://www.usiu.ac.ke/test-fixture/copy/")
    assert copy["review_flags"] == ["duplicate_content"]


def test_rebuilding_the_index_keeps_sources_and_approvals(client, registry, admin_headers):
    approved = [add_source(registry, **s) for s in TEST_SOURCES]
    draft = add_source(registry, approve=False, url="https://www.usiu.ac.ke/test-fixture/draft/",
                       text="TEST FIXTURE draft text about a synthetic hostel.")
    registry.chunks.delete_many({"source_id": approved[0]["_id"]})           # index damaged
    registry.chunks.insert_one({"source_id": draft["_id"], "chunk": 0, "text": "stray"})  # stale chunk
    before = list(registry.sources.find({}, {"status": 1, "approved_at": 1, "text_sha256": 1}))

    response = client.post("/api/admin/sources/rebuild-index", headers=admin_headers)
    assert response.status_code == 200
    body = response.get_json()
    assert body["report"]["approved_sources"] == len(TEST_SOURCES) and body["report"]["failed"] == []
    assert body["report"]["removed_chunks"] == 1 and body["counts"]["approved"] == len(TEST_SOURCES)
    assert list(registry.sources.find({}, {"status": 1, "approved_at": 1, "text_sha256": 1})) == before
    assert registry.chunks.count_documents({"source_id": draft["_id"]}) == 0
    assert registry.retrieve("applications submitted online")[0]["source"]["url"] == TEST_SOURCES[0]["url"]


# --- Secrets ------------------------------------------------------------------------------
def test_admin_and_public_responses_never_contain_secrets(make_app):
    app = make_app(GROQ_API_KEY="gsk-test-secret-value", MAIL_PASSWORD="mail-test-secret")
    client = app.test_client()
    token = client.post("/api/admin/login", json={"email": "admin@example.test",
                                                   "password": "correct-horse-battery-staple"}).get_json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    bodies = [client.get(url, headers=headers).get_data(as_text=True) for url in (
        "/api/admin/stats", "/api/admin/live-retrieval", "/api/admin/enquiries", LINKS, "/api/admin/sources",
        "/api/enquiries/options", "/api/health")]
    bodies.append(json.dumps(client.post("/api/query", json={"question": "How much is tuition?"}).get_json()))
    for text in bodies:
        assert "gsk-test-secret-value" not in text and "mail-test-secret" not in text
        assert "correct-horse-battery-staple" not in text
