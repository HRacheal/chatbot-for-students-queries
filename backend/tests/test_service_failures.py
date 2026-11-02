"""MongoDB / Groq failure handling and the connection-check tool (no real services are contacted)."""

import mongomock
import pytest
from pymongo.errors import OperationFailure, ServerSelectionTimeoutError

from config.database import Database, explain_mongo_error
from tools.connection_check import check_groq, check_mongo, mask_uri


def test_mongo_errors_are_explained_without_credentials():
    auth = explain_mongo_error(OperationFailure("bad auth : authentication failed"))
    assert "Authentication failed" in auth and "<db_password>" in auth
    assert "Network Access" in explain_mongo_error(ServerSelectionTimeoutError("timed out"))


def test_connect_failure_sets_a_safe_message(monkeypatch):
    import config.database as database

    class Refusing:
        def __init__(self, *a, **k):
            self.admin = self

        def command(self, *_):
            raise OperationFailure("bad auth : authentication failed for user secretuser")

    monkeypatch.setattr(database, "MongoClient", Refusing)
    db = Database()
    assert db.connect("mongodb+srv://secretuser:secretpass@cluster0.example.mongodb.net", "x") is False
    assert "Authentication failed" in db.last_error and "secret" not in db.last_error
    assert Database().connect("", "x") is False


def test_app_refuses_to_start_with_an_understandable_error(monkeypatch, make_app):
    import config.database as database
    from app import create_app

    monkeypatch.setattr(database.db_instance, "connect", lambda *a, **k: False)
    monkeypatch.setattr(database.db_instance, "last_error", "The MongoDB cluster could not be reached.")
    with pytest.raises(RuntimeError, match="could not be reached"):
        create_app("testing")


def test_database_outage_during_a_request_returns_503(app, client, admin_headers, monkeypatch):
    service = app.extensions["enquiry_service"]

    def down(*_a, **_k):
        raise ServerSelectionTimeoutError("cluster0.example.mongodb.net:27017: timed out")

    monkeypatch.setattr(service, "list", down)
    response = client.get("/api/admin/enquiries", headers=admin_headers)
    assert response.status_code == 503 and response.get_json()["code"] == "database_unavailable"
    assert "mongodb.net" not in response.get_data(as_text=True)


def test_mask_uri_hides_credentials_and_cluster_id():
    masked = mask_uri("mongodb+srv://user:p%40ss@usiubot.ab12cd.mongodb.net/?retryWrites=true")
    assert masked == "mongodb+srv://***@usiubot.***.mongodb.net" and "p%40ss" not in masked
    assert mask_uri("") == "<not set>"


def test_check_mongo_reports_failure_safely(monkeypatch, capsys):
    import pymongo

    class Refusing:
        def __init__(self, *a, **k):
            self.admin = self

        def command(self, *_):
            raise OperationFailure("bad auth : authentication failed")

    monkeypatch.setattr(pymongo, "MongoClient", Refusing)
    assert check_mongo("mongodb+srv://u:topsecret@c.x.mongodb.net", "chatbot") is False
    out = capsys.readouterr().out
    assert "Authentication failed" in out and "topsecret" not in out


def test_check_mongo_with_working_database(monkeypatch, capsys):
    import pymongo

    monkeypatch.setattr(pymongo, "MongoClient", lambda *a, **k: mongomock.MongoClient())
    assert check_mongo("mongodb://localhost", "chatbot", write_test=True) is True
    assert "write test" in capsys.readouterr().out


def test_check_groq_without_key_and_with_failures(monkeypatch, capsys):
    assert check_groq("", "openai/gpt-oss-120b", 5) is False
    import langchain_groq

    class Failing:
        def __init__(self, **kwargs):
            pass

        def invoke(self, _):
            raise RuntimeError("Error code: 429 - rate limit reached")

    monkeypatch.setattr(langchain_groq, "ChatGroq", Failing)
    assert check_groq("gsk_secret_value", "openai/gpt-oss-120b", 5) is False
    out = capsys.readouterr().out
    assert "rate limit" in out and "gsk_secret_value" not in out
