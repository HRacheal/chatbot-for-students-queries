"""Authentication, authorisation and configuration safety."""

import datetime

import jwt
import mongomock
import pytest

from app import create_app
from config.config import ConfigurationError, validate_config
from tests.conftest import TEST_SECRET

# Every route that must only be reachable by an administrator.
ADMIN_ROUTES = [
    ("get", "/api/admin/stats"),
    ("get", "/api/admin/chat-history"),
    ("get", "/api/admin/query-analytics"),
    ("get", "/api/admin/unanswered-queries"),
    ("delete", "/api/admin/delete-query/650000000000000000000000"),
    ("post", "/api/admin/add-response"),
    ("get", "/api/unanswered-queries"),
    ("post", "/api/add-response"),
    ("delete", "/api/delete-query/650000000000000000000000"),
    ("get", "/api/pdfs/"),
    ("post", "/api/pdfs/upload"),
    ("post", "/api/pdfs/rebuild-embeddings"),
    ("delete", "/api/pdfs/student_chatbot/pdfs/doc_1"),
]


@pytest.mark.parametrize("method,url", ADMIN_ROUTES)
def test_admin_routes_reject_missing_token(client, method, url):
    response = getattr(client, method)(url)
    assert response.status_code == 401


@pytest.mark.parametrize("method,url", ADMIN_ROUTES)
def test_admin_routes_reject_user_token(client, user_headers, method, url):
    response = getattr(client, method)(url, headers=user_headers)
    assert response.status_code == 403


@pytest.mark.parametrize("method,url", ADMIN_ROUTES)
def test_admin_routes_accept_admin_token(client, admin_headers, method, url):
    response = getattr(client, method)(url, headers=admin_headers)
    assert response.status_code not in (401, 403)


def _forge(payload, secret):
    return {"Authorization": "Bearer " + jwt.encode(payload, secret, algorithm="HS256")}


def test_token_signed_with_old_default_secret_is_rejected(client):
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {"sub": "admin", "role": "admin", "type": "admin", "iat": now,
               "exp": now + datetime.timedelta(hours=1)}
    response = client.get("/api/admin/stats", headers=_forge(payload, "your_secret_key"))
    assert response.status_code == 401


def test_legacy_token_without_type_claim_is_rejected(client):
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {"role": "admin", "exp": now + datetime.timedelta(hours=1)}
    response = client.get("/api/admin/stats", headers=_forge(payload, TEST_SECRET))
    assert response.status_code == 401


def test_expired_admin_token_is_rejected(client):
    past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2)
    payload = {"sub": "admin", "role": "admin", "type": "admin", "iat": past,
               "exp": past + datetime.timedelta(hours=1)}
    response = client.get("/api/admin/stats", headers=_forge(payload, TEST_SECRET))
    assert response.status_code == 401


def test_tampered_token_is_rejected(client, admin_headers):
    tampered = admin_headers["Authorization"][:-4] + "abcd"
    response = client.get("/api/admin/stats", headers={"Authorization": tampered})
    assert response.status_code == 401


def test_admin_token_cannot_read_user_chat_history(client, admin_headers):
    assert client.get("/api/chat-history", headers=admin_headers).status_code == 401


def test_chat_history_requires_login(client):
    assert client.get("/api/chat-history").status_code == 401


def test_user_chat_history_works_with_user_token(client, user_headers):
    response = client.get("/api/chat-history", headers=user_headers)
    assert response.status_code == 200
    assert response.get_json() == {"history": []}


# --- Login -------------------------------------------------------------------------
def test_admin_login_wrong_password(client):
    response = client.post("/api/admin/login", json={"email": "admin@example.test", "password": "nope"})
    assert response.status_code == 401


def test_admin_login_disabled_when_not_configured(make_app):
    app = make_app(ADMIN_EMAIL=None, ADMIN_PASSWORD=None)
    response = app.test_client().post("/api/admin/login", json={"email": "a@b.c", "password": "x"})
    assert response.status_code == 401


def test_user_login_wrong_password(client, user_headers):
    response = client.post("/api/login", json={"username": "student1", "password": "wrong-pass"})
    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid credentials"}


def test_user_login_unknown_user(client):
    response = client.post("/api/login", json={"username": "ghost", "password": "whatever1"})
    assert response.status_code == 401


@pytest.mark.parametrize("body,expected", [
    ({"username": "ab", "email": "a@b.co", "password": "longenough"}, "Username"),
    ({"username": "valid_name", "email": "not-an-email", "password": "longenough"}, "email"),
    ({"username": "valid_name", "email": "a@b.co", "password": "short"}, "Password"),
    ({"username": "valid_name", "email": "a@b.co", "password": "x" * 100}, "Password"),
    ({"username": "<script>", "email": "a@b.co", "password": "longenough"}, "Username"),
])
def test_signup_validation(client, body, expected):
    response = client.post("/api/signup", json=body)
    assert response.status_code == 400
    assert expected.lower() in response.get_json()["error"].lower()


def test_signup_rejects_duplicate_username_and_email(client, user_headers):
    same_email = client.post(
        "/api/signup",
        json={"username": "other", "email": "STUDENT1@example.test", "password": "s3cure-pass"},
    )
    same_username = client.post(
        "/api/signup",
        json={"username": "student1", "email": "new@example.test", "password": "s3cure-pass"},
    )
    assert same_email.status_code == 409
    assert same_username.status_code == 409


def test_signup_rejects_non_json_body(client):
    response = client.post("/api/signup", data="username=x", content_type="text/plain")
    assert response.status_code == 400


def test_passwords_are_hashed(app, client, user_headers):
    from config.database import db_instance

    user = db_instance.get_collection("users").find_one({"username": "student1"})
    assert user["password"] != "s3cure-pass"
    assert user["password"].startswith("$2")


# --- Configuration -------------------------------------------------------------------
@pytest.mark.parametrize("secret", [None, "", "your_secret_key", "short-secret"])
def test_unsafe_secret_keys_are_rejected(secret):
    with pytest.raises(ConfigurationError):
        create_app("testing", overrides={"SECRET_KEY": secret}, db_client=mongomock.MongoClient())


def test_wildcard_cors_is_rejected():
    errors = validate_config({"SECRET_KEY": TEST_SECRET, "CORS_ORIGINS": ["*"],
                              "CLOUDINARY_DELIVERY_TYPE": "authenticated"})
    assert any("CORS" in e for e in errors)


# --- Debug routes ------------------------------------------------------------------
@pytest.mark.parametrize("url", ["/debug/routes", "/debug/email", "/debug/cors", "/debug/query"])
def test_debug_routes_absent_by_default(client, url):
    assert client.get(url).status_code == 404


def test_debug_routes_never_registered_in_production(make_app):
    app = make_app("production", ENABLE_DEBUG_ROUTES=True)
    assert app.test_client().get("/debug/routes").status_code == 404


def test_debug_routes_require_admin_when_enabled(make_app):
    app = make_app("development", ENABLE_DEBUG_ROUTES=True)
    client = app.test_client()
    assert client.get("/debug/routes").status_code == 401
    login = client.post("/api/admin/login",
                        json={"email": "admin@example.test", "password": "correct-horse-battery-staple"})
    headers = {"Authorization": "Bearer " + login.get_json()["token"]}
    response = client.get("/debug/email", headers=headers)
    assert response.status_code == 200
    assert "mail_username" not in response.get_json()
