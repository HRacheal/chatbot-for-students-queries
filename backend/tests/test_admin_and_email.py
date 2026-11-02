"""Admin answers to unanswered queries and email failure handling."""

import smtplib

from config.database import db_instance


def _create_unanswered(user_id=None):
    from models.models import Query

    return str(Query().create_query("When is graduation?", user_id, answered=False))


def test_add_response_marks_query_answered(client, admin_headers, storage):
    storage.configured = False  # knowledge-base document step is skipped
    query_id = _create_unanswered()
    response = client.post("/api/add-response", json={"id": query_id, "response": "In June."},
                           headers=admin_headers)
    body = response.get_json()
    assert response.status_code == 200
    assert body["email_notification"] == "not_applicable"
    stored = db_instance.get_collection("queries").find_one({})
    assert stored["answered"] is True and stored["answer"] == "In June."


def test_add_response_reports_email_failure_without_failing(client, admin_headers, user_headers,
                                                           storage, app, monkeypatch):
    storage.configured = False
    user = db_instance.get_collection("users").find_one({"username": "student1"})
    query_id = _create_unanswered(str(user["_id"]))

    app.extensions["email_service"].settings = dict(
        app.config, MAIL_USERNAME="bot@example.test", MAIL_PASSWORD="pw"
    )

    def broken_smtp(*args, **kwargs):
        raise smtplib.SMTPConnectError(421, "unavailable")

    monkeypatch.setattr(smtplib, "SMTP", broken_smtp)
    response = client.post("/api/add-response", json={"id": query_id, "response": "In June."},
                           headers=admin_headers)
    assert response.status_code == 200
    assert response.get_json()["email_notification"] == "failed"
    assert db_instance.get_collection("queries").find_one({})["answered"] is True


def test_email_not_sent_when_smtp_not_configured(app):
    email_service = app.extensions["email_service"]
    assert email_service.is_configured() is False
    assert email_service.send("someone@example.test", "Subject", "Body") is False


def test_add_response_validation(client, admin_headers):
    bad_id = client.post("/api/add-response", json={"id": "not-an-id", "response": "x"},
                         headers=admin_headers)
    empty = client.post("/api/add-response", json={"id": "650000000000000000000000", "response": " "},
                        headers=admin_headers)
    missing = client.post("/api/add-response", json={"id": "650000000000000000000000", "response": "x"},
                          headers=admin_headers)
    assert bad_id.status_code == 400
    assert empty.status_code == 400
    assert missing.status_code == 404


def test_delete_query_invalid_id(client, admin_headers):
    assert client.delete("/api/delete-query/xyz", headers=admin_headers).status_code == 400


def test_delete_query(client, admin_headers):
    query_id = _create_unanswered()
    assert client.delete(f"/api/delete-query/{query_id}", headers=admin_headers).status_code == 200
    assert client.delete(f"/api/delete-query/{query_id}", headers=admin_headers).status_code == 404


def test_admin_dashboard_endpoints(client, admin_headers):
    _create_unanswered()
    stats = client.get("/api/admin/stats", headers=admin_headers).get_json()
    queries = client.get("/api/unanswered-queries", headers=admin_headers).get_json()["queries"]
    analytics = client.get("/api/admin/query-analytics", headers=admin_headers)
    assert stats["unanswered_queries"] == 1
    assert queries[0]["question"] == "When is graduation?"
    assert analytics.status_code == 200


# --- Admin answers become draft sources -----------------------------------------------------------
def _answer(client, admin_headers, query_id, text="TEST FIXTURE. Graduation is held once a year.", **extra):
    return client.post("/api/add-response", json={"id": query_id, "response": text, **extra},
                       headers=admin_headers)


def test_admin_answer_is_saved_as_a_draft_source_not_trusted_knowledge(client, admin_headers, storage, registry):
    query_id = _create_unanswered()
    body = _answer(client, admin_headers, query_id).get_json()
    assert body["draft_source_created"] is True
    source = registry.get(body["draft_source_id"])
    assert source["status"] == "draft"
    assert source["content_type"] == "staff_answer"
    assert source["url"] is None
    assert "When is graduation?" in source["text"] and "once a year" in source["text"]
    assert storage.uploaded == []  # the legacy Q&A PDF in Cloudinary is no longer written
    # A draft never influences answers.
    answer = client.post("/api/query", json={"question": "When is graduation held?"}).get_json()
    assert answer["status"] == "unanswered"


def test_approved_staff_answer_is_cited_without_a_link(client, admin_headers, registry, app, monkeypatch):
    from tests.conftest import FakeLLM

    query_id = _create_unanswered()
    source_id = _answer(client, admin_headers, query_id, department="registrar").get_json()["draft_source_id"]
    approved = client.post(f"/api/admin/sources/{source_id}/status", json={"status": "approved"},
                           headers=admin_headers)
    assert approved.status_code == 200
    llm = FakeLLM(answer="Graduation is held once a year [1].")
    monkeypatch.setattr(app.extensions["chat_service"], "_get_llm", lambda: llm)
    body = client.post("/api/query", json={"question": "When is graduation held?"}).get_json()
    assert body["status"] == "answered"
    [citation] = body["citations"]
    assert citation["content_type"] == "staff_answer"
    assert citation["url"] is None
    assert citation["department"] == "registrar"


def test_answering_again_updates_the_same_draft(client, admin_headers, registry):
    query_id = _create_unanswered()
    first = _answer(client, admin_headers, query_id).get_json()["draft_source_id"]
    second = _answer(client, admin_headers, query_id, text="TEST FIXTURE. Updated answer.").get_json()
    assert second["draft_source_id"] == first
    assert "Updated answer" in registry.get(first)["text"]


def test_reanswering_an_approved_staff_answer_requires_reapproval(client, admin_headers, registry):
    query_id = _create_unanswered()
    source_id = _answer(client, admin_headers, query_id).get_json()["draft_source_id"]
    registry.set_status(source_id, "approved")
    _answer(client, admin_headers, query_id, text="TEST FIXTURE. Changed.")
    assert registry.get(source_id)["status"] == "draft"


def test_staff_answer_url_and_type_cannot_be_changed(client, admin_headers):
    query_id = _create_unanswered()
    source_id = _answer(client, admin_headers, query_id).get_json()["draft_source_id"]
    for change in ({"url": "https://www.usiu.ac.ke/x"}, {"content_type": "html"}):
        response = client.put(f"/api/admin/sources/{source_id}", json=change, headers=admin_headers)
        assert response.status_code == 400


def test_invalid_department_for_admin_answer_is_rejected(client, admin_headers):
    query_id = _create_unanswered()
    response = _answer(client, admin_headers, query_id, department="bursary")
    assert response.status_code == 400


def test_api_cannot_create_a_url_less_source(client, admin_headers):
    response = client.post("/api/admin/sources", json={
        "title": "x", "department": "admissions", "content_type": "staff_answer", "text": "x"},
        headers=admin_headers)
    assert response.status_code == 400
