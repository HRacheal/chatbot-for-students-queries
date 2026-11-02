"""Integration of the USIUBOT dataset (usiubot_datasets/) into the approved-source registry.

Every record used here is SYNTHETIC (a small dataset written to a temporary folder with a
TEST_DATASET marker). None of it is real USIU-Africa information. The real dataset is only read
in a dry run (nothing written) to check that it loads.
"""

import csv
import json
from pathlib import Path

import pytest

from services.dataset_import import DatasetImporter, department_for
from services.routing import ENQUIRY_DEPARTMENTS, classify_department
from services.sources import SourceError
from tests.test_enquiries import RecordingEmail

SITE = "https://www.usiu.ac.ke/test-fixture"
HANDBOOK = "TEST-FIXTURE-Handbook.pdf"


def chunk(section_id, n, category, text, origin="official", **extra):
    folder_fields = {
        "record_id": f"{section_id}-C{n:02d}", "chunk_id": f"{section_id}-C{n:02d}", "section_id": section_id,
        "chunk_index": n, "category_id": category, "data_origin": origin, "content": text,
        "review_status": "draft", "verification_status": "pending_verification", "approval_status": "not_approved",
        "issue_ids": [],
    }
    folder_fields.update(extra)
    return folder_fields


def pdf_chunk(section_id, n, category, text, page, heading, **extra):
    return chunk(section_id, n, category, text, document_id="test_fixture_handbook",
                 document_title="TEST FIXTURE Student Handbook", document_file=HANDBOOK, source_url=None,
                 page_start=page, page_end=page, pages=[page], section_heading=heading,
                 section_number="9.1", extraction_date="2026-11-01", publication_date="Publication date not stated",
                 academic_year="Not stated", content_fidelity="verbatim", **extra)


def web_chunk(section_id, n, category, text, path, heading, origin="official", url=None, **extra):
    return chunk(section_id, n, category, f"{heading}\n\n{text}", origin=origin,
                 document_id=f"test-fixture-{path}", document_title=f"TEST FIXTURE {path.title()} page",
                 source_url=url or f"{SITE}/{path}/", source_file=f"web_sources/snapshots/{path}.md",
                 heading_path=[heading], collection_date="2026-11-01", publication_date="Publication date not stated",
                 publisher="USIU-Africa" if origin == "official" else "TEST FIXTURE Placement Service",
                 content_fidelity="verbatim_page_text", **extra)


def write_dataset(root, extra_chunks=(), register_rows=None, test_marker=True):
    """A miniature dataset with the same layout as usiubot_datasets/."""
    root = Path(root)
    files = {
        "01_general_university_information/official/knowledge_chunks.json": [
            pdf_chunk("HB-9.1", 0, "01", "TEST FIXTURE. Zorblat parking permits are issued by the Security Office "
                      "to registered students.", 54, "Zorblat Parking Permits", issue_ids=["T01"]),
        ],
        "04_fees_and_payments/official/web_knowledge_chunks.json": [
            web_chunk("WEB-P900-S01", 0, "04", "TEST FIXTURE. Quibble tuition is charged per credit hour each "
                      "semester.", "quibble-fees", "Quibble Tuition", issue_ids=["T02", "T03"]),
            web_chunk("WEB-P900-S02", 0, "04", "TEST FIXTURE. Pay quibble fees to account number 000-TEST-000 "
                      "at the fixture bank, branch code 000.", "quibble-fees", "Quibble Bank Accounts"),
        ],
        "03_admissions_and_applications/official/web_knowledge_chunks.json": [
            web_chunk("WEB-P901-S01", 0, "03", "TEST FIXTURE. Quibble applicants submit the application online "
                      "and pay a quibble application fee.", "quibble-apply", "Quibble Applications"),
        ],
        "03_admissions_and_applications/external/web_knowledge_chunks.json": [
            web_chunk("EXT-P001-S01", 0, "03", "TEST FIXTURE. The placement service publishes quibble cut-off "
                      "points for government-sponsored students.", "placement", "Quibble Cut-off Points",
                      origin="external", url="https://kuccps.net/test-fixture/cut-off/",
                      flags=["external_source_not_usiu_policy"]),
        ],
    }
    for chunk_ in extra_chunks:
        files.setdefault(chunk_.pop("_file"), []).append(chunk_)
    for rel, chunks in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(chunks, indent=1), encoding="utf-8")
    reports = root / "validation_reports"
    reports.mkdir(parents=True, exist_ok=True)
    rows = register_rows if register_rows is not None else [
        {"issue_id": "T01", "type": "missing_source", "severity": "high", "status": "unresolved",
         "summary": "TEST FIXTURE handbook has no public link"},
        {"issue_id": "T02", "type": "conflict", "severity": "high", "status": "open",
         "summary": "TEST FIXTURE: two quibble tuition rates are printed"},
        {"issue_id": "T03", "type": "ambiguity", "severity": "low", "status": "open",
         "summary": "TEST FIXTURE: low-severity wording note"},
    ]
    with open(reports / "conflict_and_verification_register.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["issue_id", "type", "severity", "status", "summary"])
        writer.writeheader()
        writer.writerows(rows)
    contacts = root / "06_department_contacts_and_query_routing/official"
    contacts.mkdir(parents=True, exist_ok=True)
    with open(contacts / "web_department_contacts.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["record_id", "routing_department", "app_department", "office_as_printed",
                                               "contact_type", "value_as_printed", "source_title", "source_url",
                                               "issue_ids"])
        writer.writeheader()
        writer.writerow({"record_id": "CON-TEST-01", "routing_department": "finance",
                         "app_department": "general_university", "office_as_printed": "TEST FIXTURE Finance Office",
                         "contact_type": "email", "value_as_printed": "finance-fixture@example.test",
                         "source_title": "TEST FIXTURE contacts", "source_url": f"{SITE}/contacts/", "issue_ids": ""})
    if test_marker:
        (root / "TEST_DATASET").write_text("Synthetic records for automated tests only.\n", encoding="utf-8")
    return root


@pytest.fixture
def dataset_dir(tmp_path):
    return write_dataset(tmp_path / "dataset")


@pytest.fixture
def ds_app(make_app, dataset_dir):
    return make_app(DATASET_DIR=str(dataset_dir))


@pytest.fixture
def ds_client(ds_app):
    return ds_app.test_client()


@pytest.fixture
def ds_admin(ds_client):
    response = ds_client.post("/api/admin/login",
                              json={"email": "admin@example.test", "password": "correct-horse-battery-staple"})
    return {"Authorization": f"Bearer {response.get_json()['token']}"}


def importer(app):
    return DatasetImporter(app.extensions["source_registry"], app.config["DATASET_DIR"])


def dataset_sources(app, **query):
    return list(app.extensions["source_registry"].sources.find({"dataset": {"$exists": True}, **query}))


def approve_all(client, headers, app):
    ids = [str(s["_id"]) for s in dataset_sources(app)]
    response = client.post("/api/admin/sources/bulk-status", json={"ids": ids, "status": "approved"}, headers=headers)
    assert response.status_code == 200, response.get_json()
    return response.get_json()["report"]


def by_section(app, section_id):
    return app.extensions["source_registry"].find_dataset_source(section_id)


# --- loading -------------------------------------------------------------------------------
def test_import_creates_one_draft_per_section_and_approves_nothing(ds_client, ds_admin, ds_app):
    response = ds_client.post("/api/admin/dataset/import", json={}, headers=ds_admin)
    assert response.status_code == 200
    report = response.get_json()["report"]
    assert report["outcomes"] == {"created": 5} and report["approved_by_import"] == 0
    assert report["test_dataset"] is True and report["refused_count"] == 0
    assert report["sections_by_category"] == {"01": 1, "03": 2, "04": 2}
    sources = dataset_sources(ds_app)
    assert len(sources) == 5 and {s["status"] for s in sources} == {"draft"}
    assert ds_app.extensions["source_registry"].chunks.count_documents({}) == 0  # drafts are never indexed
    status = ds_client.get("/api/admin/dataset/status", headers=ds_admin).get_json()
    assert status["imported_sections"] == 5 and status["by_status"] == {"draft": 5}


def test_dry_run_writes_nothing(ds_client, ds_admin, ds_app):
    report = ds_client.post("/api/admin/dataset/import", json={"dry_run": True}, headers=ds_admin).get_json()["report"]
    assert report["dry_run"] is True and report["outcomes"] == {"created": 5}
    assert dataset_sources(ds_app) == []


def test_dataset_metadata_is_preserved(ds_app):
    importer(ds_app).run()
    pdf = by_section(ds_app, "HB-9.1")
    assert pdf["content_type"] == "pdf" and pdf["url"] is None and pdf["category"] == "01"
    assert pdf["dataset"]["document_file"] == HANDBOOK and pdf["dataset"]["page_start"] == 54
    assert pdf["dataset"]["section_heading"] == "Zorblat Parking Permits"
    assert "no_public_url" in pdf["review_flags"]
    web = by_section(ds_app, "WEB-P900-S01")
    assert web["url"] == f"{SITE}/quibble-fees/" and web["dataset"]["collected_at"] == "2026-11-01"
    assert web["department"] == "finance" and web["data_origin"] == "official"
    ext = by_section(ds_app, "EXT-P001-S01")
    assert ext["data_origin"] == "external" and "external_source" in ext["review_flags"]
    # Open issues from the register travel with the section; resolved ones would not.
    assert {i["id"] for i in web["dataset"]["issues"]} == {"T02", "T03"}
    assert "conflict" in web["review_flags"]
    assert "payment_details" in by_section(ds_app, "WEB-P900-S02")["review_flags"]


def test_admin_endpoints_require_an_admin(ds_client):
    for method, url in (("get", "/api/admin/dataset/status"), ("post", "/api/admin/dataset/import"),
                        ("get", "/api/admin/dataset/search?q=fees"), ("get", "/api/admin/routing"),
                        ("post", "/api/admin/sources/bulk-status"), ("post", "/api/admin/routing/import-contacts")):
        assert getattr(ds_client, method)(url).status_code == 401


def test_missing_dataset_folder_is_reported(make_app, tmp_path):
    app = make_app(DATASET_DIR=str(tmp_path / "nowhere"))
    c = app.test_client()
    token = c.post("/api/admin/login", json={"email": "admin@example.test",
                                             "password": "correct-horse-battery-staple"}).get_json()["token"]
    response = c.post("/api/admin/dataset/import", json={}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 400 and "DATASET_DIR" in response.get_json()["error"]


# --- approval and retrieval ------------------------------------------------------------------
def test_sources_are_retrieved_only_after_approval(ds_client, ds_admin, ds_app):
    registry = ds_app.extensions["source_registry"]
    importer(ds_app).run()
    assert registry.retrieve("quibble tuition per credit hour") == []
    report = approve_all(ds_client, ds_admin, ds_app)
    assert len(report["changed"]) == 5 and report["failed"] == []
    results = registry.retrieve("quibble tuition per credit hour")
    assert results and results[0]["source"]["dataset"]["section_id"] == "WEB-P900-S01"
    # The dataset's own chunks are indexed as they are (one passage per chunk, with page metadata).
    assert registry.chunks.count_documents({}) == 5
    pdf_chunk_doc = registry.chunks.find_one({"meta.chunk_id": "HB-9.1-C00"})
    assert pdf_chunk_doc["meta"]["page_start"] == 54 and pdf_chunk_doc["category"] == "01"


def test_category_filter(ds_client, ds_admin, ds_app):
    registry = ds_app.extensions["source_registry"]
    importer(ds_app).run()
    approve_all(ds_client, ds_admin, ds_app)
    everything = {r["source"]["category"] for r in registry.retrieve("quibble application fee", k=5)}
    assert {"03", "04"} <= everything
    only_fees = registry.retrieve("quibble application fee", k=5, categories=["04"])
    assert only_fees and {r["source"]["category"] for r in only_fees} == {"04"}
    assert registry.retrieve("quibble application fee", categories=["02"]) == []
    response = ds_client.get("/api/admin/dataset/search?q=quibble+application+fee&category=03", headers=ds_admin)
    assert response.status_code == 200
    assert {r["category"] for r in response.get_json()["results"]} == {"03"}
    assert ds_client.get("/api/admin/dataset/search?q=x&category=99", headers=ds_admin).status_code == 400


def test_bulk_approval_reports_failures_and_rejects_bad_input(ds_client, ds_admin, ds_app):
    importer(ds_app).run()
    good = str(dataset_sources(ds_app)[0]["_id"])
    report = ds_client.post("/api/admin/sources/bulk-status", headers=ds_admin,
                            json={"ids": [good, "0" * 24], "status": "approved"}).get_json()["report"]
    assert report["changed"] == [good] and len(report["failed"]) == 1
    assert ds_client.post("/api/admin/sources/bulk-status", headers=ds_admin,
                          json={"ids": [], "status": "approved"}).status_code == 400
    assert ds_client.post("/api/admin/sources/bulk-status", headers=ds_admin,
                          json={"ids": [good], "status": "published"}).status_code == 400


def test_dataset_text_cannot_be_edited_in_the_form(ds_client, ds_admin, ds_app):
    importer(ds_app).run()
    sid = str(by_section(ds_app, "WEB-P901-S01")["_id"])
    response = ds_client.put(f"/api/admin/sources/{sid}", json={"text": "Changed"}, headers=ds_admin)
    assert response.status_code == 400 and "re-imported" in response.get_json()["error"]
    assert ds_client.put(f"/api/admin/sources/{sid}", json={"department": "registrar"},
                         headers=ds_admin).status_code == 200


def test_source_list_filters(ds_client, ds_admin, ds_app):
    importer(ds_app).run()
    get = lambda q: ds_client.get("/api/admin/sources" + q, headers=ds_admin).get_json()["sources"]  # noqa: E731
    assert len(get("?kind=dataset")) == 5
    assert [s["category"] for s in get("?category=01")] == ["01"]
    ext = get("?origin=external")
    assert len(ext) == 1 and ext[0]["data_origin"] == "external" and ext[0]["from_dataset"]
    assert len(get("?search=Quibble+Bank")) == 1
    assert ds_client.get("/api/admin/sources?category=99", headers=ds_admin).status_code == 400


# --- citations and warnings ------------------------------------------------------------------
def ask(client, question):
    return client.post("/api/query", json={"question": question}).get_json()


@pytest.fixture
def approved_dataset(ds_client, ds_admin, ds_app, monkeypatch):
    from tests.conftest import FakeLLM

    importer(ds_app).run()
    approve_all(ds_client, ds_admin, ds_app)
    llm = FakeLLM(answer="The answer is in the source [1].")
    monkeypatch.setattr(ds_app.extensions["chat_service"], "_get_llm", lambda: llm)
    return llm


def test_pdf_citation_has_file_page_and_section(ds_client, approved_dataset):
    body = ask(ds_client, "How do I get a zorblat parking permit?")
    assert body["status"] == "answered"
    c = body["citations"][0]
    assert c["url"] is None and c["document_file"] == HANDBOOK
    assert c["page_start"] == 54 and c["page_end"] == 54 and c["section_heading"] == "Zorblat Parking Permits"
    assert c["category"] == "01" and c["external"] is False
    # The model is told the page and the source; a document-level note (no public link) is not a warning.
    assert "page 54" in approved_dataset.prompts[0]
    assert not [w for w in body["warnings"] if w["type"].startswith("dataset_")]


def test_web_citation_has_url_and_collection_date(ds_client, approved_dataset):
    body = ask(ds_client, "How do quibble applicants submit the application?")
    c = body["citations"][0]
    assert c["url"] == f"{SITE}/quibble-apply/" and c["document_file"] is None
    assert c["collected_at"] == "2026-11-01" and c["section_heading"] == "Quibble Applications"


def test_external_source_is_labelled(ds_client, approved_dataset):
    body = ask(ds_client, "What are the quibble cut-off points for government-sponsored students?")
    c = body["citations"][0]
    assert c["external"] is True and c["data_origin"] == "external"
    assert c["publisher"] == "TEST FIXTURE Placement Service"
    assert any(w["type"] == "external" and "not USIU-Africa policy" in w["message"] for w in body["warnings"])
    assert "EXTERNAL source from TEST FIXTURE Placement Service" in approved_dataset.prompts[0]


def test_every_unresolved_conflict_or_ambiguity_is_explained(ds_client, approved_dataset):
    # Sources may be bulk-approved without a reviewer, so low-severity unresolved items are shown too.
    body = ask(ds_client, "How is quibble tuition charged per credit hour?")
    types = [w["type"] for w in body["warnings"]]
    assert "dataset_conflict" in types and "dataset_ambiguity" in types
    assert "Known issue (conflict, open)" in approved_dataset.prompts[0]
    assert "Known issue (ambiguity, open)" in approved_dataset.prompts[0]


def test_payment_details_warn_to_confirm_with_finance(ds_client, approved_dataset):
    body = ask(ds_client, "Which account number do I use to pay quibble fees at the fixture bank?")
    assert any(w["type"] == "payment" and "Finance Office" in w["message"] for w in body["warnings"])
    from services.chat_service import SYSTEM_PROMPT

    assert "Never present bank account numbers" in SYSTEM_PROMPT


def test_sources_only_reply_shows_the_approved_passages(ds_client, ds_admin, ds_app):
    importer(ds_app).run()
    approve_all(ds_client, ds_admin, ds_app)
    body = ask(ds_client, "How do I get a zorblat parking permit?")  # no language model configured
    assert body["status"] == "sources_only" and body["verified"] is False
    assert "Security Office" in body["citations"][0]["excerpts"][0]


# --- unresolved questions and routing ---------------------------------------------------------
def test_unanswerable_question_is_logged_and_routed_to_finance(ds_client, ds_app, approved_dataset):
    approved_dataset.answer = "I do not know."
    body = ask(ds_client, "Can I pay my tuition balance in instalments by cheque?")
    assert body["status"] == "unanswered" and body["verified"] is False
    assert body["enquiry"]["suggested_department"] == "finance"
    assert body["enquiry"]["suggested_department_label"] == "Finance"
    assert body["enquiry"]["contacts"] == []  # nothing is shown until an administrator publishes contacts
    from config.database import db_instance

    from bson import ObjectId

    logged = db_instance.get_collection("queries").find_one({"_id": ObjectId(body["enquiry"]["query_id"])})
    assert logged["answered"] is False and logged["department"] == "finance"


@pytest.mark.parametrize("question,department", [
    ("How much is tuition and when is the fee payment deadline?", "finance"),
    ("What is the M-PESA paybill for fees?", "finance"),
    ("I need a refund of my deposit", "finance"),
    ("How do I apply for a scholarship?", "admissions"),
    ("I cannot log in to the student portal or wifi", "ict"),
    ("How many books can I borrow from the library?", "library"),
    ("Is hostel accommodation available?", "student_affairs"),
    ("Where is the counselling centre?", "student_affairs"),
    ("How do I request a transcript?", "registrar"),
    ("Can I get a brochure?", "marketing"),
    ("What are the prerequisites for the BSc?", "academic_programmes"),
    ("What is the university phone number?", "general_university"),
])
def test_department_routing_includes_finance_separately(question, department):
    assert classify_department(question)[0] == department


def test_all_nine_departments_accept_enquiries():
    assert set(ENQUIRY_DEPARTMENTS) == {"admissions", "registrar", "finance", "academic_programmes", "marketing",
                                        "student_affairs", "ict", "library", "general_university"}


def test_dataset_department_suggestions():
    assert department_for("04", "tuition-fees", "Other Charges") == "finance"
    assert department_for("04", "financial-aid", "Scholarships") == "admissions"
    assert department_for("03", "admission-fees", "Application Fee") == "admissions"
    assert department_for("02", "programs__master-of-arts-in-counseling", "Overview") == "academic_programmes"
    assert department_for("01", "academics__library-and-e-resources", "Opening Hours") == "library"


def test_routing_is_admin_configurable_and_contacts_are_not_invented(ds_client, ds_admin, ds_app):
    listing = ds_client.get("/api/admin/routing", headers=ds_admin).get_json()["departments"]
    assert len(listing) == 9 and all(d["delivery_emails"] == [] and d["public_contacts"] == [] for d in listing)
    imported = ds_client.post("/api/admin/routing/import-contacts", headers=ds_admin).get_json()
    assert imported["report"]["filled"] == ["finance"]
    finance = next(d for d in imported["departments"] if d["department"] == "finance")
    # Copied exactly as printed in the (synthetic) dataset, unpublished, and never used for delivery.
    assert finance["public_contacts"][0]["value"] == "finance-fixture@example.test"
    assert finance["publish_contacts"] is False and finance["delivery_emails"] == []
    routing = ds_app.extensions["department_routing"]
    assert routing.published_contacts("finance") == []
    ds_client.put("/api/admin/routing/finance", json={"publish_contacts": True}, headers=ds_admin)
    assert routing.published_contacts("finance")[0]["value"] == "finance-fixture@example.test"
    # Importing again never overwrites what an administrator has.
    again = ds_client.post("/api/admin/routing/import-contacts", headers=ds_admin).get_json()["report"]
    assert again["filled"] == [] and again["skipped_existing"] == ["finance"]
    bad = ds_client.put("/api/admin/routing/finance", json={"delivery_emails": ["not an email"]}, headers=ds_admin)
    assert bad.status_code == 400
    assert ds_client.put("/api/admin/routing/bursary", json={"notes": "x"}, headers=ds_admin).status_code == 400


def test_admin_delivery_address_overrides_environment(make_app, dataset_dir):
    app = make_app(DATASET_DIR=str(dataset_dir), ENQUIRY_EMAIL_FINANCE="env-finance@example.test")
    service = app.extensions["enquiry_service"]
    assert service.department_recipients("finance") == ["env-finance@example.test"]
    app.extensions["department_routing"].update("finance", {"delivery_emails": ["staff-finance@example.test"]})
    assert service.department_recipients("finance") == ["staff-finance@example.test"]
    email = RecordingEmail(configured=True, succeed=True)
    service.email_service = email
    response = app.test_client().post("/api/enquiries", json={
        "question": "Can I pay my tuition balance by cheque?", "name": "Test Applicant",
        "email": "applicant@example.test", "phone": "+254 700 000000", "consent": True})
    assert response.status_code == 201 and response.get_json()["enquiry"]["department"] == "finance"
    assert email.sent[0][0] == "staff-finance@example.test"


def test_unresolved_reply_shows_published_contacts(ds_client, ds_admin, ds_app, approved_dataset):
    ds_app.extensions["department_routing"].update("finance", {"public_contacts": [
        {"type": "email", "value": "finance-fixture@example.test", "office": "TEST FIXTURE Finance"}],
        "publish_contacts": True})
    approved_dataset.answer = "I do not know."
    body = ask(ds_client, "Can I pay my tuition balance in instalments by cheque?")
    assert body["enquiry"]["contacts"] == [{"type": "email", "value": "finance-fixture@example.test",
                                            "office": "TEST FIXTURE Finance", "source_url": ""}]


# --- duplicates and refresh -------------------------------------------------------------------
def test_reimport_is_idempotent_and_duplicates_are_skipped(tmp_path, make_app):
    dup = web_chunk("WEB-P902-S01", 0, "04", "TEST FIXTURE. Quibble tuition is charged per credit hour each "
                    "semester.", "quibble-fees-copy", "Quibble Tuition")
    root = write_dataset(tmp_path / "d", extra_chunks=[{**dup, "_file": "04_fees_and_payments/official/web_knowledge_chunks.json"}])
    app = make_app(DATASET_DIR=str(root))
    first = importer(app).run()
    assert first["read"]["duplicate_chunks_skipped"] == 1 and first["outcomes"] == {"created": 5}
    second = importer(app).run()
    assert second["outcomes"] == {"unchanged": 5} and second["archived_missing"] == 0
    assert len(dataset_sources(app)) == 5


def test_refresh_returns_changed_approved_sources_to_draft_and_archives_removed(tmp_path, make_app):
    root = write_dataset(tmp_path / "d")
    app = make_app(DATASET_DIR=str(root))
    registry = app.extensions["source_registry"]
    importer(app).run()
    for s in dataset_sources(app):
        registry.set_status(str(s["_id"]), "approved")
    registry.update(str(by_section(app, "WEB-P901-S01")["_id"]), {"title": "TEST FIXTURE corrected title"})
    assert registry.retrieve("quibble tuition per credit hour")

    path = root / "04_fees_and_payments/official/web_knowledge_chunks.json"
    chunks = json.loads(path.read_text(encoding="utf-8"))
    chunks[0]["content"] = chunks[0]["content"].replace("per credit hour", "per quibble unit")
    path.write_text(json.dumps(chunks[:1]), encoding="utf-8")  # S02 removed, S01 changed

    report = importer(app).run()
    assert report["outcomes"] == {"returned_to_draft": 1, "unchanged": 3} and report["archived_missing"] == 1
    changed = by_section(app, "WEB-P900-S01")
    assert changed["status"] == "draft" and "re-approval" in changed["status_history"][-1]["note"]
    assert by_section(app, "WEB-P900-S02")["status"] == "archived"
    hits = {r["source"]["dataset"]["section_id"] for r in registry.retrieve("quibble tuition per credit unit", k=5)}
    assert "WEB-P900-S01" not in hits  # changed text is not used until re-approved
    assert registry.chunks.count_documents({"source_id": changed["_id"]}) == 0
    assert by_section(app, "WEB-P901-S01")["title"] == "TEST FIXTURE corrected title"  # admin edit kept


# --- synthetic data never reaches production retrieval -----------------------------------------
def test_test_dataset_is_refused_outside_test_mode(make_app, dataset_dir):
    app = make_app(DATASET_DIR=str(dataset_dir), ALLOW_TEST_SOURCES=False)
    report = importer(app).run()
    assert report["refused_count"] == 5 and dataset_sources(app) == []
    assert "test mode" in report["refused"][0]["error"]


def test_test_records_are_not_retrieved_outside_test_mode(make_app, dataset_dir):
    app = make_app(DATASET_DIR=str(dataset_dir))
    registry = app.extensions["source_registry"]
    importer(app).run()
    for s in dataset_sources(app):
        registry.set_status(str(s["_id"]), "approved")
    assert registry.retrieve("quibble tuition per credit hour")
    registry.settings = {**registry.settings, "ALLOW_TEST_SOURCES": False}
    assert registry.retrieve("quibble tuition per credit hour") == []


def test_records_without_an_official_or_external_origin_are_refused(app):
    registry = app.extensions["source_registry"]
    with pytest.raises(SourceError, match="synthetic"):
        registry.upsert_dataset_source({"section_id": "X", "data_origin": "synthetic", "chunks": [{"text": "x"}]})


def test_external_records_need_an_allowed_external_domain(make_app, tmp_path):
    root = write_dataset(tmp_path / "d")
    app = make_app(DATASET_DIR=str(root), EXTERNAL_SOURCE_DOMAINS=[])
    report = importer(app).run()
    assert report["refused_count"] == 1 and report["refused"][0]["section_id"] == "EXT-P001-S01"


def test_production_config_rejects_test_sources():
    from config.config import validate_config

    errors = validate_config({"SECRET_KEY": "x" * 64, "CLOUDINARY_DELIVERY_TYPE": "authenticated",
                              "ALLOWED_SOURCE_DOMAINS": ["usiu.ac.ke"], "TRUSTED_SOURCE_HOSTS": ["www.usiu.ac.ke"],
                              "ENV_NAME": "production", "ALLOW_TEST_SOURCES": True,
                              "EXTERNAL_SOURCE_DOMAINS": ["usiu.ac.ke"]})
    assert any("ALLOW_TEST_SOURCES" in e for e in errors)
    assert any("must not include an official" in e for e in errors)


# --- the real dataset (read only) ---------------------------------------------------------------
REAL_DATASET = Path(__file__).resolve().parents[2] / "usiubot_datasets"


@pytest.mark.skipif(not (REAL_DATASET / "validation_reports").exists(), reason="usiubot_datasets not present")
def test_real_dataset_loads_in_a_dry_run(make_app):
    app = make_app(DATASET_DIR=str(REAL_DATASET))
    imp = importer(app)
    assert imp.is_test_dataset is False
    report = imp.run(dry_run=True)
    assert report["refused_count"] == 0 and report["read"].get("chunks_without_text", 0) == 0
    assert report["outcomes"] == {"created": report["read"]["sections"]}
    assert set(report["sections_by_category"]) <= {"01", "02", "03", "04", "05", "06", "07", "08"}
    assert dataset_sources(app) == []  # dry run: nothing written
    sections, _, _ = imp.load_sections()
    records = [imp.build_record(sid, sec, imp.issues()) for sid, sec in sections.items()]
    assert {r["data_origin"] for r in records} == {"official", "external"}
    assert all(r["is_test"] is False for r in records)
    pdfs = [r for r in records if r["content_type"] == "pdf"]
    assert pdfs and all(isinstance(r["dataset"]["page_start"], int) and r["dataset"]["document_file"] for r in pdfs)
    assert all(r["url"] for r in records if r["content_type"] == "html")
