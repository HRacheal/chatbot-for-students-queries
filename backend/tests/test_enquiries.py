"""Unresolved enquiries: consent, routing, duplicates, tracking, admin management, notifications."""

import pytest

from services.routing import ENQUIRY_DEPARTMENTS, classify_department

VALID = {"question": "When does the next undergraduate intake start?", "name": "Test Applicant",
         "email": "applicant@example.test", "phone": "+254 700 000000", "consent": True}


def submit(client, headers=None, **changes):
    return client.post("/api/enquiries", json={**VALID, **changes}, headers=headers or {})


@pytest.mark.parametrize("question,department", [
    ("How do I apply for admission to an undergraduate programme?", "admissions"),
    ("Is there a scholarship for new applicants?", "admissions"),
    ("How do I request my official transcript?", "registrar"),
    ("When is graduation and how do I clear?", "registrar"),
    ("Can I get a brochure or book a campus tour?", "marketing"),
    ("I want to discuss a sponsorship partnership", "marketing"),
    ("What degrees does the School of Science offer?", "academic_programmes"),
    ("What are the prerequisites for the BSc in Applied Computer Technology?", "academic_programmes"),
    ("Where is the library and what are its hours?", "library"),
    ("What is the phone number of the university?", "general_university"),
    ("When is course registration?", "registrar"),
    ("Hello there", None),
])
def test_department_routing(question, department):
    assert classify_department(question)[0] == department


def test_submission_requires_consent_and_valid_contact(client):
    assert submit(client, consent=False).status_code == 400
    assert submit(client, consent="yes").status_code == 400
    assert submit(client, email="not-an-email").status_code == 400
    assert submit(client, name="").status_code == 400
    assert submit(client, phone="call me").status_code == 400
    assert submit(client, question="").status_code == 400
    assert submit(client, department="bursary").status_code == 400
    from config.database import db_instance

    assert db_instance.get_collection("enquiries").count_documents({}) == 0


def test_unclear_department_must_be_chosen(client):
    response = submit(client, question="Hello, can someone call me back?")
    assert response.status_code == 400 and "choose the department" in response.get_json()["error"]
    assert submit(client, question="Hello, can someone call me back?", department="marketing").status_code == 201


def test_submission_is_saved_routed_and_confirmed(client, app):
    response = submit(client)
    assert response.status_code == 201
    body = response.get_json()
    enquiry = body["enquiry"]
    assert body["created"] is True and body["tracking_key"]
    assert enquiry["reference"].startswith("ENQ-") and enquiry["department"] == "admissions"
    assert enquiry["status"] == "new" and enquiry["created_at"]
    assert "contact" not in enquiry and "applicant@example.test" not in str(body)
    stored = app.extensions["enquiry_service"].collection.find_one({"reference": enquiry["reference"]})
    assert stored["contact"]["email"] == "applicant@example.test"
    assert stored["consent"]["given"] is True and stored["consent"]["at"]
    assert body["tracking_key"] not in str(stored)                      # only its hash is stored
    assert stored["notification"]["status"] == "not_configured"
    assert body["delivery"] == "not_configured" and "not been emailed" in body["message"]  # never claims delivery


def test_duplicate_submission_returns_the_open_enquiry(client, app):
    first = submit(client).get_json()
    again = submit(client, question="  when does the NEXT undergraduate intake start ", email="APPLICANT@example.test")
    assert again.status_code == 200
    body = again.get_json()
    assert body["created"] is False and "tracking_key" not in body
    assert body["enquiry"]["reference"] == first["enquiry"]["reference"]
    assert app.extensions["enquiry_service"].collection.count_documents({}) == 1


def test_closed_enquiry_can_be_asked_again(client, app, admin_headers):
    first = submit(client).get_json()
    enquiry_id = str(app.extensions["enquiry_service"].collection.find_one()["_id"])
    client.post(f"/api/admin/enquiries/{enquiry_id}/status", json={"status": "closed"}, headers=admin_headers)
    again = submit(client)
    assert again.status_code == 201
    assert again.get_json()["enquiry"]["reference"] != first["enquiry"]["reference"]


def test_tracking_requires_reference_and_key(client):
    body = submit(client).get_json()
    reference, key = body["enquiry"]["reference"], body["tracking_key"]
    ok = client.post("/api/enquiries/track", json={"reference": reference.lower(), "tracking_key": key})
    assert ok.status_code == 200 and ok.get_json()["enquiry"]["status"] == "new"
    assert "contact" not in ok.get_json()["enquiry"]
    assert client.post("/api/enquiries/track", json={"reference": reference, "tracking_key": "wrong"}).status_code == 404
    assert client.post("/api/enquiries/track", json={"reference": "ENQ-NOPE", "tracking_key": key}).status_code == 404


def test_logged_in_user_sees_only_their_own_enquiries(client, user_headers):
    submit(client, headers=user_headers)
    submit(client, question="How do I order a transcript?", email="someone@example.test")
    mine = client.get("/api/my-enquiries", headers=user_headers).get_json()["enquiries"]
    assert [e["question"] for e in mine] == [VALID["question"]]
    assert client.get("/api/my-enquiries").status_code == 401


def test_admin_endpoints_require_an_admin_token(client, user_headers):
    submit(client)
    for method, url in (("get", "/api/admin/enquiries"), ("get", "/api/admin/enquiries/0123456789abcdef01234567"),
                        ("post", "/api/admin/enquiries/0123456789abcdef01234567/status")):
        assert getattr(client, method)(url).status_code == 401
        assert getattr(client, method)(url, headers=user_headers).status_code == 403


def test_admin_filters_details_and_status_tracking(client, admin_headers):
    submit(client)
    submit(client, question="How do I request my official transcript?", email="b@example.test")
    submit(client, question="Can I get a brochure?", email="c@example.test")

    listing = client.get("/api/admin/enquiries", headers=admin_headers).get_json()
    assert len(listing["enquiries"]) == 3
    assert listing["stats"]["unresolved"] == 3
    assert listing["notifications"]["departments"] == {d: False for d in ENQUIRY_DEPARTMENTS}

    registrar = client.get("/api/admin/enquiries?department=registrar", headers=admin_headers).get_json()
    [enquiry] = registrar["enquiries"]
    assert enquiry["contact"]["email"] == "b@example.test"
    assert client.get("/api/admin/enquiries?department=bursary", headers=admin_headers).status_code == 400

    url = f"/api/admin/enquiries/{enquiry['id']}/status"
    assert client.post(url, json={"status": "done"}, headers=admin_headers).status_code == 400
    progress = client.post(url, json={"status": "in_progress", "note": "Called the student"}, headers=admin_headers)
    assert progress.status_code == 200 and progress.get_json()["enquiry"]["status"] == "in_progress"
    assert client.post(url, json={"status": "resolved"}, headers=admin_headers).status_code == 400  # reply needed
    resolved = client.post(url, json={"status": "resolved", "staff_response": "Synthetic test reply."},
                           headers=admin_headers).get_json()["enquiry"]
    assert resolved["resolved_at"] and [h["status"] for h in resolved["history"]] == ["new", "in_progress",
                                                                                      "resolved"]

    detail = client.get(f"/api/admin/enquiries/{enquiry['id']}", headers=admin_headers).get_json()["enquiry"]
    assert detail["history"][1]["note"] == "Called the student"
    assert client.get("/api/admin/enquiries?status=open", headers=admin_headers).get_json()["stats"]["unresolved"] == 2
    assert len(client.get("/api/admin/enquiries?status=resolved", headers=admin_headers).get_json()["enquiries"]) == 1

    stats = client.get("/api/admin/stats", headers=admin_headers).get_json()
    assert stats["unresolved_enquiries"] == 2 and stats["total_enquiries"] == 3
    assert stats["enquiries_by_department"]["registrar"]["resolved"] == 1


def test_staff_can_reroute_an_enquiry(client, admin_headers):
    submit(client)
    enquiry = client.get("/api/admin/enquiries", headers=admin_headers).get_json()["enquiries"][0]
    moved = client.post(f"/api/admin/enquiries/{enquiry['id']}/status",
                        json={"status": "in_progress", "department": "registrar"}, headers=admin_headers)
    assert moved.get_json()["enquiry"]["department"] == "registrar"


class RecordingEmail:
    def __init__(self, configured=True, succeed=True):
        self.configured, self.succeed, self.sent = configured, succeed, []

    def is_configured(self):
        return self.configured

    def send(self, recipient, subject, body):
        self.sent.append((recipient, subject, body))
        return self.succeed


@pytest.mark.parametrize("configured,succeed,expected", [(True, True, "sent"), (True, False, "failed"),
                                                         (False, True, "not_configured")])
def test_department_email_notification(make_app, configured, succeed, expected):
    app = make_app(ENQUIRY_EMAIL_ADMISSIONS="admissions-team@example.test")
    email = RecordingEmail(configured, succeed)
    app.extensions["enquiry_service"].email_service = email
    body = submit(app.test_client()).get_json()
    stored = app.extensions["enquiry_service"].collection.find_one()
    assert stored["notification"]["status"] == expected
    if configured:
        recipient, subject, text = email.sent[0]
        assert recipient == "admissions-team@example.test" and body["enquiry"]["reference"] in subject
        assert "consent given" in text
    else:
        assert email.sent == []


def test_enquiry_submission_is_rate_limited(make_app):
    app = make_app(ENQUIRY_RATE_LIMIT_PER_MINUTE=2)
    client = app.test_client()
    codes = [submit(client, email=f"user{i}@example.test").status_code for i in range(3)]
    assert codes == [201, 201, 429]


def test_unverified_chat_reply_links_to_enquiry(client):
    body = client.post("/api/query", json={"question": "Is there a gym on campus?"}).get_json()
    assert body["status"] == "unanswered"
    response = submit(client, question="Is there a gym on campus?", department="marketing",
                      query_id=body["enquiry"]["query_id"])
    assert response.status_code == 201


def admin_enquiry(client, admin_headers):
    return client.get("/api/admin/enquiries", headers=admin_headers).get_json()["enquiries"][0]


def test_assignment_lifecycle_and_closing(client, admin_headers):
    submit(client)
    url = f"/api/admin/enquiries/{admin_enquiry(client, admin_headers)['id']}/status"
    assert client.post(url, json={"status": "assigned"}, headers=admin_headers).status_code == 400  # old status
    pending = client.post(url, json={"status": "pending", "assigned_to": "  Admissions   desk "},
                          headers=admin_headers).get_json()["enquiry"]
    assert pending["status"] == "pending" and pending["assigned_to"] == "Admissions desk"
    assert client.post(url, json={"status": "in_progress"}, headers=admin_headers).get_json()["enquiry"][
        "assigned_to"] == "Admissions desk"  # kept
    waiting = client.post(url, json={"status": "awaiting_response", "staff_response": "Synthetic reply."},
                          headers=admin_headers).get_json()["enquiry"]
    resolved = client.post(url, json={"status": "resolved"}, headers=admin_headers).get_json()["enquiry"]
    closed = client.post(url, json={"status": "closed"}, headers=admin_headers).get_json()["enquiry"]
    assert waiting["staff_response"] == closed["staff_response"] == "Synthetic reply."
    assert resolved["resolved_at"] == closed["resolved_at"]  # first resolution time is kept
    assert [h["status"] for h in closed["history"]] == ["new", "pending", "in_progress", "awaiting_response",
                                                        "resolved", "closed"]
    assert client.post(url, json={"status": "pending", "assigned_to": "x" * 101},
                       headers=admin_headers).status_code == 400


def test_new_departments_can_receive_enquiries(client, admin_headers):
    assert submit(client, question="Where is the library?", email="l@example.test").get_json()["enquiry"][
        "department"] == "library"
    response = submit(client, question="Hello, please call me", department="academic_programmes")
    assert response.status_code == 201 and response.get_json()["enquiry"]["department_label"] == "Academic Programmes"
    listing = client.get("/api/admin/enquiries?department=academic_programmes", headers=admin_headers).get_json()
    assert len(listing["enquiries"]) == 1 and listing["stats"]["by_department"]["library"]["new"] == 1


def test_enquiries_can_be_filtered_by_date_and_done_status(client, app, admin_headers):
    import datetime

    submit(client)
    collection = app.extensions["enquiry_service"].collection
    collection.update_one({}, {"$set": {"created_at": datetime.datetime(2026, 1, 15, 12, 0)}})
    submit(client, question="How do I request my official transcript?", email="b@example.test")
    get = lambda q: client.get("/api/admin/enquiries" + q, headers=admin_headers)  # noqa: E731
    assert len(get("?from=2026-01-15&to=2026-01-15").get_json()["enquiries"]) == 1
    assert len(get("?from=2026-02-01").get_json()["enquiries"]) == 1
    assert get("?from=15/01/2026").status_code == 400
    assert get("?status=done").get_json()["enquiries"] == []


def test_enquiries_from_an_earlier_version_are_migrated_not_lost(app, client, admin_headers):
    service = app.extensions["enquiry_service"]
    submit(client)
    service.collection.update_one({}, {"$set": {"status": "assigned", "assigned_to": "Desk"}})
    submit(client, question="How do I request my official transcript?", email="b@example.test")
    service.collection.update_one({"contact.email": "b@example.test"}, {"$set": {"status": "answered"}})
    listing = client.get("/api/admin/enquiries", headers=admin_headers).get_json()
    assert sorted(e["status"] for e in listing["enquiries"]) == ["in_progress", "resolved"]  # read correctly
    assert listing["stats"]["unresolved"] == 1
    assert len(client.get("/api/admin/enquiries?status=resolved", headers=admin_headers).get_json()["enquiries"]) == 1
    assert service.migrate_legacy_statuses() == 2 and service.migrate_legacy_statuses() == 0
    assert service.collection.count_documents({}) == 2
    docs = list(service.collection.find())
    assert sorted(d["status"] for d in docs) == ["in_progress", "resolved"]
    assert sorted(d["status_migrated_from"] for d in docs) == ["answered", "assigned"]
    assert any(d.get("assigned_to") == "Desk" for d in docs)  # assignee kept


def test_delivery_message_says_emailed_only_when_the_email_was_sent(make_app):
    app = make_app(ENQUIRY_EMAIL_ADMISSIONS="admissions-team@example.test")
    app.extensions["enquiry_service"].email_service = RecordingEmail(configured=True, succeed=True)
    body = submit(app.test_client()).get_json()
    assert body["delivery"] == "sent" and "emailed to Admissions" in body["message"]
    app.extensions["enquiry_service"].email_service = RecordingEmail(configured=True, succeed=False)
    body = submit(app.test_client(), email="other@example.test").get_json()
    assert body["delivery"] == "failed" and "not been emailed" in body["message"]
