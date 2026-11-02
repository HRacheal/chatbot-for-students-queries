"""Live integration tests against the real MongoDB Atlas cluster and the real Groq API.

Skipped by default. Run them explicitly (they read MONGO_URI / GROQ_API_KEY from backend/.env):

    $env:USIUBOT_LIVE_TESTS="1"; .venv\\Scripts\\python -m pytest tests/test_live_integration.py -v

Isolation: everything runs in a temporary database named ``usiubot_itest_<random>`` on the same
cluster, which is dropped at the end. The real ``chatbot_db`` is never written to, and all records
are synthetic (example.test addresses, "TEST FIXTURE" sources).
"""

import os
import secrets
from pathlib import Path

import pytest
from dotenv import dotenv_values

LIVE = os.getenv("USIUBOT_LIVE_TESTS") == "1"
ENV = dotenv_values(Path(__file__).resolve().parents[1] / ".env") if LIVE else {}
pytestmark = pytest.mark.skipif(not LIVE, reason="set USIUBOT_LIVE_TESTS=1 to run live Atlas/Groq tests")

ADMIN = {"email": "itest-admin@example.test", "password": "Itest-admin-pass-2026"}
STAFF_PASSWORD = "Itest-staff-pass-2026"


@pytest.fixture(scope="module")
def live_app():
    from pymongo import MongoClient

    from app import create_app
    from utils.rate_limit import limiter

    uri = ENV.get("MONGO_URI")
    if not uri:
        pytest.skip("MONGO_URI is not set in backend/.env")
    db_name = "usiubot_itest_" + secrets.token_hex(4)
    client = MongoClient(uri, serverSelectionTimeoutMS=15000)
    limiter.reset()
    app = create_app("testing", db_client=client, overrides={
        "MONGO_DB_NAME": db_name, "GROQ_API_KEY": ENV.get("GROQ_API_KEY") or "",
        "GROQ_MODEL": ENV.get("GROQ_MODEL") or "openai/gpt-oss-120b",
        "ADMIN_EMAIL": ADMIN["email"], "ADMIN_PASSWORD": ADMIN["password"], "RATE_LIMIT_ENABLED": False,
    })
    app.extensions["itest_db_name"] = db_name
    try:
        yield app
    finally:
        assert db_name.startswith("usiubot_itest_")  # never drop a real database
        client.drop_database(db_name)
        client.close()


@pytest.fixture(scope="module")
def http(live_app):
    return live_app.test_client()


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def admin_token(http):
    response = http.post("/api/staff/login", json=ADMIN)
    assert response.status_code == 200
    return response.get_json()["token"]


def test_connected_to_atlas_with_collections_and_indexes(live_app):
    from config.database import db_instance

    assert db_instance.ping()
    assert db_instance.db.name == live_app.extensions["itest_db_name"]
    names = set(db_instance.db.list_collection_names())
    for collection in ("staff", "enquiries", "sources", "audit_log", "revoked_tokens", "users"):
        assert collection in names, collection
    staff_indexes = db_instance.db["staff"].index_information()
    assert any(spec.get("unique") and spec["key"] == [("email", 1)] for spec in staff_indexes.values())
    ttl = db_instance.db["revoked_tokens"].index_information()
    assert any(spec.get("expireAfterSeconds") == 0 for spec in ttl.values())


def test_staff_roles_and_department_permissions_on_atlas(http, admin_token):
    def make(email, role, departments):
        created = http.post("/api/staff/accounts", headers=auth(admin_token), json={
            "email": email, "name": email.split("@")[0], "role": role, "departments": departments})
        assert created.status_code == 201
        token = http.post("/api/staff/login", json={"email": email, "password": created.get_json()[
            "temporary_password"]}).get_json()["token"]
        changed = http.post("/api/staff/password", headers=auth(token), json={
            "current_password": created.get_json()["temporary_password"], "new_password": STAFF_PASSWORD})
        assert changed.status_code == 200
        return token, created.get_json()["staff"]["id"]

    adm_admin, _ = make("itest-adm-admin@example.test", "department_admin", ["admissions"])
    adm_staff, adm_staff_id = make("itest-adm-staff@example.test", "department_staff", ["admissions"])
    reg_staff, _ = make("itest-reg-staff@example.test", "department_staff", ["registrar"])

    for department, question in (("admissions", "TEST: When is the intake?"), ("registrar", "TEST: Transcript?")):
        response = http.post("/api/enquiries", json={"question": question, "name": "Synthetic", "consent": True,
                                                     "email": f"{department}@example.test", "department": department})
        assert response.status_code == 201

    admissions = http.get("/api/admin/enquiries", headers=auth(adm_staff)).get_json()["enquiries"]
    assert [e["department"] for e in admissions] == ["admissions"]
    registrar_view = http.get("/api/admin/enquiries", headers=auth(reg_staff)).get_json()["enquiries"]
    assert [e["department"] for e in registrar_view] == ["registrar"]
    assert http.get(f"/api/admin/enquiries/{registrar_view[0]['id']}", headers=auth(adm_staff)).status_code == 404
    assert http.get("/api/admin/sources", headers=auth(adm_admin)).status_code == 403

    enquiry_id = admissions[0]["id"]
    url = f"/api/admin/enquiries/{enquiry_id}/status"
    assert http.post(url, headers=auth(adm_admin), json={"assigned_to_id": adm_staff_id,
                                                         "status": "in_progress"}).status_code == 200
    assert http.post(f"/api/admin/enquiries/{enquiry_id}/notes", headers=auth(adm_staff),
                     json={"text": "Synthetic internal note"}).status_code == 201
    resolved = http.post(url, headers=auth(adm_staff), json={"status": "resolved",
                                                             "staff_response": "Synthetic reply."}).get_json()
    assert resolved["enquiry"]["status"] == "resolved" and resolved["enquiry"]["resolved_at"]

    dashboard = http.get("/api/admin/dashboard", headers=auth(admin_token)).get_json()
    assert dashboard["stats"]["total"] == 2 and dashboard["stats"]["by_status"]["resolved"] == 1
    assert dashboard["trend"][-1]["received"] == 2 and dashboard["trend"][-1]["resolved"] == 1
    dept = http.get("/api/admin/dashboard", headers=auth(adm_staff)).get_json()
    assert dept["stats"]["total"] == 1

    assert http.post("/api/staff/logout", headers=auth(adm_staff)).status_code == 200
    assert http.get("/api/staff/me", headers=auth(adm_staff)).status_code == 401
    audit = http.get("/api/staff/audit?action=enquiry", headers=auth(admin_token)).get_json()
    assert audit["total"] >= 3


@pytest.mark.skipif(LIVE and not ENV.get("GROQ_API_KEY"), reason="GROQ_API_KEY is not set")
def test_groq_answers_from_approved_sources_only(live_app, http):
    registry = live_app.extensions["source_registry"]
    source = registry.create({
        "url": "https://www.usiu.ac.ke/test-fixture/how-to-apply/", "title": "TEST FIXTURE: How to Apply",
        "department": "admissions", "source_date": "2026-01",
        "text": "TEST FIXTURE. Applications are submitted online through the applicant portal. "
                "Each programme lists its entry requirements."})
    question = {"question": "How are applications to USIU-Africa submitted?"}
    draft = http.post("/api/query", json=question).get_json()
    assert draft["status"] != "answered" and not draft.get("citations")  # drafts are never used
    registry.set_status(str(source["_id"]), "approved")
    answered = http.post("/api/query", json=question).get_json()
    assert answered["status"] == "answered", answered.get("status")
    assert (answered.get("answer") or "").strip()  # real generated text, not empty
    assert "online" in answered["answer"].lower() or "portal" in answered["answer"].lower()
    assert [c["url"] for c in answered["citations"]] == ["https://www.usiu.ac.ke/test-fixture/how-to-apply/"]
    unknown = http.post("/api/query", json={"question": "What is the exact MBA tuition fee for 2031?"}).get_json()
    assert unknown["status"] != "answered" and (unknown.get("enquiry") or {}).get("available")
