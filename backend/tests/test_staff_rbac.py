"""Staff accounts, sign-in, sessions, role/department permissions, dashboard statistics and audit log.

All accounts and enquiries here are synthetic (example.test) and live in an in-memory database.
"""

import datetime

import pytest

from services.staff_service import StaffService

PASSWORD = "Synthetic-pass-2026"


def create_account(client, admin_headers, **fields):
    data = {"email": "staff@example.test", "name": "Test Staff", "role": "department_staff",
            "departments": ["admissions"], **fields}
    response = client.post("/api/staff/accounts", json=data, headers=admin_headers)
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def sign_in(client, email, password):
    return client.post("/api/staff/login", json={"email": email, "password": password})


def ready_account(client, admin_headers, **fields):
    """Create an account, sign in with the temporary password, set a real one; return auth headers."""
    created = create_account(client, admin_headers, **fields)
    email = created["staff"]["email"]
    token = sign_in(client, email, created["temporary_password"]).get_json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    changed = client.post("/api/staff/password", json={"current_password": created["temporary_password"],
                                                        "new_password": PASSWORD}, headers=headers)
    assert changed.status_code == 200
    return headers, created["staff"]["id"]


def submit(client, question, department, email="enquirer@example.test", **extra):
    response = client.post("/api/enquiries", json={"question": question, "name": "Synthetic Enquirer",
                                                   "email": email, "consent": True, "department": department, **extra})
    assert response.status_code == 201, response.get_json()
    return response.get_json()


@pytest.fixture
def team(client, admin_headers):
    """Admissions admin + staff, Registrar staff, assigned-only Admissions staff."""
    people = {}
    people["adm_admin"] = ready_account(client, admin_headers, email="adm.admin@example.test", name="Adm Admin",
                                        role="department_admin")
    people["adm_staff"] = ready_account(client, admin_headers, email="adm.staff@example.test", name="Adm Staff")
    people["reg_staff"] = ready_account(client, admin_headers, email="reg.staff@example.test", name="Reg Staff",
                                        departments=["registrar"])
    people["adm_assigned_only"] = ready_account(client, admin_headers, email="adm.narrow@example.test",
                                                name="Adm Narrow", scope="assigned")
    submit(client, "When is the application deadline?", "admissions")
    submit(client, "How do I get my transcript?", "registrar", email="other@example.test")
    return people


# --- accounts and sign-in -------------------------------------------------------------
def test_no_public_staff_registration(client):
    assert client.post("/api/staff/accounts", json={"email": "x@example.test"}).status_code == 401
    assert client.post("/api/staff/register", json={}).status_code in (404, 405)


def test_super_admin_creates_account_with_temporary_password(client, admin_headers, app):
    body = create_account(client, admin_headers)
    assert body["temporary_password"] and body["staff"]["must_change_password"] is True
    stored = app.extensions["staff_service"].find_by_email("staff@example.test")
    assert stored["password"].startswith("$2") and body["temporary_password"] not in str(stored)
    assert "password" not in body["staff"]
    assert client.post("/api/staff/accounts", json={"email": "staff@example.test", "name": "Again",
                                                    "role": "department_staff", "departments": ["admissions"]},
                       headers=admin_headers).status_code == 400  # duplicate
    assert client.post("/api/staff/accounts", json={"email": "d@example.test", "name": "No dept",
                                                    "role": "department_admin"},
                       headers=admin_headers).status_code == 400  # department needed


def test_temporary_password_must_be_changed_before_dashboard_use(client, admin_headers):
    created = create_account(client, admin_headers)
    login = sign_in(client, "staff@example.test", created["temporary_password"])
    assert login.status_code == 200 and login.get_json()["staff"]["must_change_password"] is True
    headers = {"Authorization": f"Bearer {login.get_json()['token']}"}
    blocked = client.get("/api/admin/enquiries", headers=headers)
    assert blocked.status_code == 403 and blocked.get_json()["code"] == "password_change_required"
    assert client.get("/api/staff/me", headers=headers).status_code == 200
    weak = client.post("/api/staff/password", json={"current_password": created["temporary_password"],
                                                    "new_password": "short"}, headers=headers)
    assert weak.status_code == 400
    wrong = client.post("/api/staff/password", json={"current_password": "nope", "new_password": PASSWORD},
                        headers=headers)
    assert wrong.status_code == 400
    ok = client.post("/api/staff/password", json={"current_password": created["temporary_password"],
                                                  "new_password": PASSWORD}, headers=headers)
    assert ok.status_code == 200 and client.get("/api/admin/enquiries", headers=headers).status_code == 200
    assert sign_in(client, "staff@example.test", PASSWORD).status_code == 200


def test_login_validation_and_generic_errors(client, admin_headers):
    create_account(client, admin_headers)
    assert client.post("/api/staff/login", json={}).status_code == 400
    unknown = sign_in(client, "nobody@example.test", PASSWORD)
    wrong = sign_in(client, "staff@example.test", "Wrong-password-1")
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.get_json()["error"] == wrong.get_json()["error"]  # does not reveal which emails exist


def test_repeated_failures_lock_the_account(make_app):
    app = make_app(STAFF_MAX_FAILED_LOGINS=3, AUTH_RATE_LIMIT_PER_MINUTE=100)
    client = app.test_client()
    admin = client.post("/api/admin/login", json={"email": "admin@example.test",
                                                  "password": "correct-horse-battery-staple"}).get_json()["token"]
    created = create_account(client, {"Authorization": f"Bearer {admin}"})
    for _ in range(3):
        assert sign_in(client, "staff@example.test", "Wrong-password-1").status_code == 401
    assert sign_in(client, "staff@example.test", created["temporary_password"]).status_code == 429  # locked
    staff = app.extensions["staff_service"]
    doc = staff.find_by_email("staff@example.test")
    staff.col.update_one({"_id": doc["_id"]}, {"$set": {"locked_until": datetime.datetime.now(
        datetime.timezone.utc) - datetime.timedelta(minutes=1)}})
    assert sign_in(client, "staff@example.test", created["temporary_password"]).status_code == 200


def test_logout_revokes_the_session(client, admin_headers):
    headers, _ = ready_account(client, admin_headers)
    assert client.get("/api/staff/me", headers=headers).status_code == 200
    assert client.post("/api/staff/logout", headers=headers).status_code == 200
    assert client.get("/api/staff/me", headers=headers).status_code == 401
    assert client.post("/api/staff/logout").status_code == 401


def test_deactivation_ends_sessions_and_blocks_sign_in(client, admin_headers):
    headers, staff_id = ready_account(client, admin_headers)
    response = client.put(f"/api/staff/accounts/{staff_id}", json={"active": False}, headers=admin_headers)
    assert response.status_code == 200 and response.get_json()["staff"]["active"] is False
    assert client.get("/api/staff/me", headers=headers).status_code == 401
    assert sign_in(client, "staff@example.test", PASSWORD).status_code == 403
    client.put(f"/api/staff/accounts/{staff_id}", json={"active": True}, headers=admin_headers)
    assert sign_in(client, "staff@example.test", PASSWORD).status_code == 200


def test_password_reset_ends_sessions(client, admin_headers):
    headers, staff_id = ready_account(client, admin_headers)
    reset = client.post(f"/api/staff/accounts/{staff_id}/reset-password", headers=admin_headers).get_json()
    assert reset["temporary_password"] and reset["staff"]["must_change_password"] is True
    assert client.get("/api/staff/me", headers=headers).status_code == 401
    assert sign_in(client, "staff@example.test", PASSWORD).status_code == 401
    assert sign_in(client, "staff@example.test", reset["temporary_password"]).status_code == 200


def test_expired_token_is_refused(make_app):
    app = make_app(ADMIN_TOKEN_HOURS=-1)
    client = app.test_client()
    token = client.post("/api/admin/login", json={"email": "admin@example.test",
                                                  "password": "correct-horse-battery-staple"}).get_json()["token"]
    assert client.get("/api/staff/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_me_reports_role_and_permissions(client, admin_headers, team):
    me = client.get("/api/staff/me", headers=admin_headers).get_json()["staff"]
    assert me["role"] == "super_admin" and me["permissions"]["manage_staff"] is True
    adm = client.get("/api/staff/me", headers=team["adm_admin"][0]).get_json()["staff"]
    assert adm["role"] == "department_admin" and list(adm["department_labels"]) == ["admissions"]
    assert adm["permissions"]["manage_staff"] is False and adm["permissions"]["assign_enquiries"] is True
    assert adm["permissions"]["manage_programmes"] is True
    staff = client.get("/api/staff/me", headers=team["adm_staff"][0]).get_json()["staff"]
    assert staff["permissions"]["assign_enquiries"] is False


# --- role and department permissions ---------------------------------------------------
@pytest.mark.parametrize("person", ["adm_admin", "adm_staff", "reg_staff"])
def test_only_super_admin_reaches_admin_only_areas(client, team, person):
    headers = team[person][0]
    for method, url in (("get", "/api/admin/sources"), ("post", "/api/admin/dataset/import"),
                        ("get", "/api/admin/chat-history"), ("get", "/api/admin/official-links"),
                        ("post", "/api/staff/accounts"), ("get", "/api/staff/audit"),
                        ("get", "/api/admin/unanswered-queries"), ("get", "/api/pdfs/")):
        assert getattr(client, method)(url, headers=headers).status_code == 403, url


def test_departments_see_only_their_own_enquiries(client, admin_headers, team):
    all_refs = client.get("/api/admin/enquiries", headers=admin_headers).get_json()["enquiries"]
    assert len(all_refs) == 2
    adm = client.get("/api/admin/enquiries", headers=team["adm_staff"][0]).get_json()
    assert [e["department"] for e in adm["enquiries"]] == ["admissions"]
    assert list(adm["departments"]) == ["admissions"] and list(adm["stats"]["by_department"]) == ["admissions"]
    reg = client.get("/api/admin/enquiries", headers=team["reg_staff"][0]).get_json()
    assert [e["department"] for e in reg["enquiries"]] == ["registrar"]
    # Asking for another department, or opening/updating its enquiry, is refused.
    assert client.get("/api/admin/enquiries?department=registrar", headers=team["adm_staff"][0]).status_code == 403
    registrar_id = next(e["id"] for e in all_refs if e["department"] == "registrar")
    assert client.get(f"/api/admin/enquiries/{registrar_id}", headers=team["adm_staff"][0]).status_code == 404
    assert client.post(f"/api/admin/enquiries/{registrar_id}/status", json={"status": "closed"},
                       headers=team["adm_admin"][0]).status_code == 404
    assert client.post(f"/api/admin/enquiries/{registrar_id}/notes", json={"text": "x"},
                       headers=team["adm_staff"][0]).status_code == 404


def test_assigned_only_staff_see_just_their_assignments(client, admin_headers, team):
    narrow_headers, narrow_id = team["adm_assigned_only"]
    assert client.get("/api/admin/enquiries", headers=narrow_headers).get_json()["enquiries"] == []
    enquiry = client.get("/api/admin/enquiries?department=admissions", headers=admin_headers).get_json()["enquiries"][0]
    assigned = client.post(f"/api/admin/enquiries/{enquiry['id']}/status",
                           json={"assigned_to_id": narrow_id}, headers=team["adm_admin"][0])
    assert assigned.status_code == 200
    assert [e["id"] for e in client.get("/api/admin/enquiries", headers=narrow_headers).get_json()["enquiries"]] == [
        enquiry["id"]]


def test_assignment_rules(client, admin_headers, team):
    enquiry = client.get("/api/admin/enquiries?department=admissions", headers=admin_headers).get_json()["enquiries"][0]
    url = f"/api/admin/enquiries/{enquiry['id']}/status"
    adm_staff_id, reg_staff_id = team["adm_staff"][1], team["reg_staff"][1]
    # Department admin assigns within the department, not to another department's staff.
    assert client.post(url, json={"assigned_to_id": reg_staff_id}, headers=team["adm_admin"][0]).status_code == 403
    ok = client.post(url, json={"assigned_to_id": adm_staff_id, "status": "in_progress"},
                     headers=team["adm_admin"][0]).get_json()["enquiry"]
    assert ok["assigned_to_id"] == adm_staff_id and ok["assigned_to"] == "Adm Staff"
    # Department staff cannot assign colleagues or change free-text assignment, but can take an enquiry.
    assert client.post(url, json={"assigned_to_id": team["adm_admin"][1]},
                       headers=team["adm_staff"][0]).status_code == 403
    assert client.post(url, json={"assigned_to": "Desk"}, headers=team["adm_staff"][0]).status_code == 403
    assert client.post(url, json={"assigned_to_id": "me"}, headers=team["adm_staff"][0]).status_code == 200
    assert client.post(url, json={"assigned_to_id": ""}, headers=team["adm_staff"][0]).status_code == 403
    # Unknown or inactive people cannot be assigned.
    assert client.post(url, json={"assigned_to_id": "0123456789abcdef01234567"},
                       headers=team["adm_admin"][0]).status_code == 400
    mine = client.get("/api/admin/enquiries?assigned=me", headers=team["adm_staff"][0]).get_json()["enquiries"]
    assert [e["id"] for e in mine] == [enquiry["id"]]


def test_moving_departments_requires_an_administrator(client, admin_headers, team):
    enquiry = client.get("/api/admin/enquiries?department=admissions", headers=admin_headers).get_json()["enquiries"][0]
    url = f"/api/admin/enquiries/{enquiry['id']}/status"
    assert client.post(url, json={"department": "finance"}, headers=team["adm_staff"][0]).status_code == 403
    moved = client.post(url, json={"department": "finance", "note": "Fees question"}, headers=team["adm_admin"][0])
    assert moved.status_code == 200 and moved.get_json()["visible"] is False
    assert client.get(f"/api/admin/enquiries/{enquiry['id']}", headers=team["adm_admin"][0]).status_code == 404


def test_staff_workflow_notes_response_and_resolution(client, admin_headers, team):
    headers = team["adm_staff"][0]
    enquiry = client.get("/api/admin/enquiries", headers=headers).get_json()["enquiries"][0]
    assert enquiry["status"] == "new" and enquiry["awaiting_attention"] is True
    detail = client.get(f"/api/admin/enquiries/{enquiry['id']}", headers=headers).get_json()["enquiry"]
    assert detail["contact"]["email"] == "enquirer@example.test" and detail["question"] and detail["created_at"]
    note = client.post(f"/api/admin/enquiries/{enquiry['id']}/notes", json={"text": "Checked with the office."},
                       headers=headers)
    assert note.status_code == 201 and note.get_json()["enquiry"]["notes"][0]["by"] == "Adm Staff"
    assert client.post(f"/api/admin/enquiries/{enquiry['id']}/notes", json={"text": " "},
                       headers=headers).status_code == 400
    url = f"/api/admin/enquiries/{enquiry['id']}/status"
    assert client.post(url, json={"status": "resolved"}, headers=headers).status_code == 400
    resolved = client.post(url, json={"status": "resolved", "resolution": "Phoned the enquirer.",
                                      "staff_response": "Synthetic reply for the enquirer."},
                           headers=headers).get_json()["enquiry"]
    assert resolved["status"] == "resolved" and resolved["resolution"] == "Phoned the enquirer."
    assert resolved["history"][-1]["by"] == "adm.staff@example.test"
    # The enquirer sees the reply but never internal notes or the resolution note.
    tracked = client.get("/api/admin/enquiries", headers=headers)
    assert tracked.status_code == 200


def test_internal_notes_are_not_shown_to_the_enquirer(client):
    body = submit(client, "Synthetic question about admissions?", "admissions")
    service_note = "INTERNAL-ONLY-NOTE"
    app = client.application
    enquiry = app.extensions["enquiry_service"].collection.find_one()
    app.extensions["enquiry_service"].add_note(str(enquiry["_id"]), service_note, {"id": "x", "name": "Staff"})
    tracked = client.post("/api/enquiries/track", json={"reference": body["enquiry"]["reference"],
                                                        "tracking_key": body["tracking_key"]}).get_json()
    assert service_note not in str(tracked) and "contact" not in tracked["enquiry"]


def test_user_group_is_optional_and_validated(client, admin_headers):
    submit(client, "Admissions question one?", "admissions", user_group="parent_guardian")
    bad = client.post("/api/enquiries", json={"question": "Q?", "name": "N", "email": "n@example.test",
                                              "consent": True, "department": "admissions", "user_group": "alien"})
    assert bad.status_code == 400
    enquiry = client.get("/api/admin/enquiries", headers=admin_headers).get_json()["enquiries"][0]
    assert enquiry["user_group_label"] == "Parent or guardian"
    assert "user_groups" in client.get("/api/enquiries/options").get_json()


def test_search_and_filters(client, admin_headers, team):
    get = lambda q: client.get("/api/admin/enquiries" + q, headers=admin_headers).get_json()["enquiries"]  # noqa
    assert len(get("?q=transcript")) == 1 and len(get("?q=OTHER@example")) == 1
    assert len(get("?status=attention")) == 2 and get("?status=resolved") == []
    assert len(get("?assigned=unassigned")) == 2


# --- department settings and programme requirements -------------------------------------
def test_department_admin_manages_only_own_department_settings(client, team):
    headers = team["adm_admin"][0]
    listing = client.get("/api/admin/routing", headers=headers).get_json()
    assert [d["department"] for d in listing["departments"]] == ["admissions"] and listing["full_access"] is False
    ok = client.put("/api/admin/routing/admissions", json={"notes": "Synthetic note"}, headers=headers)
    assert ok.status_code == 200
    assert client.put("/api/admin/routing/registrar", json={"notes": "x"}, headers=headers).status_code == 403
    assert client.put("/api/admin/routing/admissions", json={"publish_contacts": True},
                      headers=headers).status_code == 403
    assert client.get("/api/admin/routing", headers=team["adm_staff"][0]).status_code == 403


def test_programme_requirements_limited_to_admissions_and_programmes_admins(client, team):
    assert client.get("/api/admin/programme-requirements", headers=team["adm_admin"][0]).status_code == 200
    assert client.get("/api/admin/programme-requirements", headers=team["adm_staff"][0]).status_code == 403


def test_staff_directory_respects_departments(client, admin_headers, team):
    people = client.get("/api/staff/directory?department=admissions", headers=team["adm_admin"][0]).get_json()["staff"]
    assert {p["email"] for p in people} == {"adm.admin@example.test", "adm.staff@example.test",
                                            "adm.narrow@example.test"}
    assert client.get("/api/staff/directory?department=registrar", headers=team["adm_admin"][0]).status_code == 403
    assert client.get("/api/staff/directory", headers=team["adm_staff"][0]).status_code == 403
    accounts = client.get("/api/staff/accounts", headers=team["adm_admin"][0]).get_json()["staff"]
    assert all("admissions" in a["departments"] for a in accounts)
    assert len(client.get("/api/staff/accounts", headers=admin_headers).get_json()["staff"]) == 4


def test_super_admin_cannot_lock_themselves_out(client, admin_headers, app):
    headers, staff_id = ready_account(client, admin_headers, email="super@example.test", name="Super Two",
                                      role="super_admin", departments=[])
    assert client.put(f"/api/staff/accounts/{staff_id}", json={"active": False}, headers=headers).status_code == 400
    assert client.put(f"/api/staff/accounts/{staff_id}", json={"role": "department_staff",
                                                               "departments": ["ict"]},
                      headers=headers).status_code == 400
    # A database Super Administrator has full access.
    assert client.get("/api/admin/sources", headers=headers).status_code == 200


# --- dashboard statistics -----------------------------------------------------------------
def test_dashboard_statistics_come_from_the_database(client, admin_headers, team, app):
    service = app.extensions["enquiry_service"]
    first = service.collection.find_one({"department": "admissions"})
    service.update_status(str(first["_id"]), "resolved", staff_response="Synthetic reply.")
    app.extensions["chat_service"].query_model.create_query("Unanswered synthetic?", department="registrar")
    full = client.get("/api/admin/dashboard", headers=admin_headers).get_json()
    assert full["stats"]["total"] == 2 and full["stats"]["by_status"]["resolved"] == 1
    assert full["stats"]["unresolved"] == 1 and full["stats"]["awaiting_attention"] == 1
    assert full["unresolved_chatbot_questions"] >= 1
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    assert full["trend"][-1] == {"date": today, "received": 2, "resolved": 1} and len(full["trend"]) == 30
    adm = client.get("/api/admin/dashboard?days=7", headers=team["adm_staff"][0]).get_json()
    assert adm["stats"]["total"] == 1 and list(adm["departments"]) == ["admissions"]
    assert adm["unresolved_chatbot_questions"] == 0 and len(adm["trend"]) == 7
    reg = client.get("/api/admin/dashboard", headers=team["reg_staff"][0]).get_json()
    assert reg["unresolved_chatbot_questions"] == 1 and reg["stats"]["awaiting_attention"] == 1
    assert client.get("/api/admin/dashboard").status_code == 401


# --- notifications ------------------------------------------------------------------------
class RecordingEmail:
    def __init__(self):
        self.sent = []

    def is_configured(self):
        return True

    def send(self, recipient, subject, body):
        self.sent.append((recipient, subject, body))
        return True


def test_assignment_and_resolution_notifications(client, admin_headers, team, app):
    email = RecordingEmail()
    app.extensions["enquiry_service"].email_service = email
    enquiry = client.get("/api/admin/enquiries?department=admissions", headers=admin_headers).get_json()["enquiries"][0]
    url = f"/api/admin/enquiries/{enquiry['id']}/status"
    client.post(url, json={"assigned_to_id": team["adm_staff"][1]}, headers=admin_headers)
    client.post(url, json={"status": "resolved", "staff_response": "Synthetic reply."}, headers=admin_headers)
    recipients = [r for r, _, _ in email.sent]
    assert recipients == ["adm.staff@example.test", "enquirer@example.test"]
    detail = client.get(f"/api/admin/enquiries/{enquiry['id']}", headers=admin_headers).get_json()["enquiry"]
    assert [(n["event"], n["status"]) for n in detail["notifications_log"]] == [
        ("new_enquiry", "not_configured"), ("assigned", "sent"), ("resolved", "sent")]


def test_notifications_are_not_claimed_without_email(client, admin_headers, team):
    enquiry = client.get("/api/admin/enquiries?department=admissions", headers=admin_headers).get_json()["enquiries"][0]
    url = f"/api/admin/enquiries/{enquiry['id']}/status"
    client.post(url, json={"assigned_to_id": team["adm_staff"][1]}, headers=admin_headers)
    detail = client.get(f"/api/admin/enquiries/{enquiry['id']}", headers=admin_headers).get_json()["enquiry"]
    assert detail["notifications_log"][-1] == {**detail["notifications_log"][-1], "event": "assigned",
                                               "status": "not_configured"}


def test_reminders_for_overdue_enquiries(client, team, app):
    service = app.extensions["enquiry_service"]
    old = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=5)
    service.collection.update_many({}, {"$set": {"updated_at": old}})
    assert len(service.overdue(3)) == 2
    report = service.send_reminders(3)
    assert report == {"admissions": {"count": 1, "status": "not_configured"},
                      "registrar": {"count": 1, "status": "not_configured"}}


# --- audit log -------------------------------------------------------------------------
def test_audit_log_records_actions_without_secrets(client, admin_headers, team):
    enquiry = client.get("/api/admin/enquiries", headers=team["adm_staff"][0]).get_json()["enquiries"][0]
    client.post(f"/api/admin/enquiries/{enquiry['id']}/status", json={"status": "in_progress"},
                headers=team["adm_staff"][0])
    sign_in(client, "adm.staff@example.test", "Wrong-password-1")
    client.post("/api/admin/sources", json={}, headers=admin_headers)  # failed request: not audited
    log = client.get("/api/staff/audit?limit=200", headers=admin_headers).get_json()
    actions = [e["action"] for e in log["entries"]]
    assert "staff.create" in actions and "auth.login" in actions and "enquiry.update" in actions
    assert any(e["action"] == "auth.login" and e["outcome"] == "failed" for e in log["entries"])
    text = str(log)
    assert PASSWORD not in text and "enquirer@example.test" not in text and "Wrong-password" not in text
    assert client.get("/api/staff/audit?action=enquiry", headers=admin_headers).get_json()["total"] == 1


def test_admin_changes_are_audited_automatically(client, admin_headers):
    client.put("/api/admin/routing/admissions", json={"notes": "Synthetic"}, headers=admin_headers)
    entries = client.get("/api/staff/audit?action=dataset.routing_update", headers=admin_headers).get_json()["entries"]
    assert entries and entries[0]["target_id"] == "admissions"


def test_staff_service_password_hashing():
    from services.staff_service import check_password, hash_password, temporary_password, validate_staff_password

    hashed = hash_password(PASSWORD)
    assert hashed != PASSWORD and check_password(PASSWORD, hashed) and not check_password("other", hashed)
    for _ in range(20):
        validate_staff_password(temporary_password())
    assert StaffService({}.get, {"STAFF_BCRYPT_ROUNDS": 4}).rounds == 4
