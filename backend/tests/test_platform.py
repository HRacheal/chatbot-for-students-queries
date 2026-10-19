"""Error handling, CORS, security headers, rate limiting, logging and tracing."""

import logging
import os

from middleware.middleware import configure_tracing
from utils.logging_utils import RedactingFilter, redact


def test_method_not_allowed_returns_405_json(client):
    response = client.put("/health")
    assert response.status_code == 405
    assert response.get_json() == {"error": "Method not allowed"}


def test_unknown_route_returns_404_json(client):
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Endpoint not found"}


def test_unhandled_exception_returns_generic_message(app, admin_headers):
    def boom():
        raise RuntimeError("secret internal detail")

    app.view_functions["admin.get_stats"] = boom
    response = app.test_client().get("/api/admin/stats", headers=admin_headers)
    assert response.status_code == 500
    assert "secret internal detail" not in response.get_data(as_text=True)


def test_health_does_not_expose_environment(client):
    body = client.get("/health").get_json()
    assert set(body) == {"status", "timestamp"}


def test_security_headers_present(client):
    headers = client.get("/health").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"


def test_cors_allows_configured_origin_only(client):
    allowed = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    denied = client.get("/api/health", headers={"Origin": "https://evil.vercel.app"})
    assert allowed.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
    assert "Access-Control-Allow-Origin" not in denied.headers
    assert "Access-Control-Allow-Credentials" not in allowed.headers


def test_login_rate_limit(make_app):
    app = make_app(AUTH_RATE_LIMIT_PER_MINUTE=3)
    client = app.test_client()
    statuses = [
        client.post("/api/login", json={"username": "x", "password": "wrongpass1"}).status_code
        for _ in range(4)
    ]
    assert statuses == [401, 401, 401, 429]
    blocked = client.post("/api/login", json={"username": "x", "password": "wrongpass1"})
    assert int(blocked.headers["Retry-After"]) > 0


def test_query_rate_limit(make_app):
    app = make_app(QUERY_RATE_LIMIT_PER_MINUTE=2)
    client = app.test_client()
    statuses = [client.post("/api/query", json={"question": "hello"}).status_code for _ in range(3)]
    assert statuses == [200, 200, 429]


def test_redaction_masks_personal_data():
    text = "Contact jane.doe@example.com or +254 712 345 678, token Bearer abc.def.ghi"
    redacted = redact(text)
    assert "jane.doe" not in redacted and "712" not in redacted and "abc.def" not in redacted
    assert "[email]" in redacted and "[number]" in redacted


def test_log_records_are_redacted():
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "user %s", ("jane@example.com",), None)
    RedactingFilter().filter(record)
    assert record.getMessage() == "user [email]"


def test_tracing_is_disabled_by_default(monkeypatch):
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    enabled = configure_tracing({"LANGSMITH_TRACING": False, "LANGSMITH_API_KEY": "key"})
    assert enabled is False
    assert os.environ["LANGCHAIN_TRACING_V2"] == "false"


def test_tracing_requires_explicit_opt_in_and_key(monkeypatch):
    for var in ("LANGSMITH_API_KEY", "LANGCHAIN_PROJECT", "LANGCHAIN_ENDPOINT",
                "LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2"):
        monkeypatch.delenv(var, raising=False)
    assert configure_tracing({"LANGSMITH_TRACING": True, "LANGSMITH_API_KEY": None}) is False
    assert configure_tracing({"LANGSMITH_TRACING": True, "LANGSMITH_API_KEY": "k"}) is True
    assert os.environ["LANGCHAIN_TRACING_V2"] == "true"
