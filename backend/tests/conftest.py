"""Shared test fixtures.

The tests never contact real external services: MongoDB is replaced with
mongomock, and the vector store, document storage, LLM and SMTP server are
replaced with in-memory fakes.
"""

import os
import sys

# Configure the environment *before* application modules are imported, and
# blank out external credentials so a developer's real backend/.env is never used.
TEST_SECRET = "test-secret-key-for-automated-tests-only-0123456789"
os.environ.update({
    "SECRET_KEY": TEST_SECRET,
    "FLASK_ENV": "testing",
    "ADMIN_EMAIL": "admin@example.test",
    "ADMIN_PASSWORD": "correct-horse-battery-staple",
    "MONGO_URI": "",
    "GROQ_API_KEY": "",
    "PINECONE_API_KEY": "",
    "CLOUDINARY_CLOUD_NAME": "",
    "CLOUDINARY_API_KEY": "",
    "CLOUDINARY_API_SECRET": "",
    "EMAIL_USER": "",
    "EMAIL_PASS": "",
    "LANGSMITH_TRACING": "false",
    "LANGSMITH_API_KEY": "",
    "ENABLE_DEBUG_ROUTES": "false",
    "CORS_ORIGINS": "http://localhost:5173",
})

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mongomock  # noqa: E402
import pytest  # noqa: E402

from app import create_app  # noqa: E402
from utils.rate_limit import limiter  # noqa: E402


# --- Fakes ------------------------------------------------------------------------
class FakeIndex:
    """Minimal stand-in for a Pinecone index (IDs only)."""

    def __init__(self, ids=()):
        self.ids = set(ids)
        self.deleted = []

    def list(self, namespace=None, prefix=None):
        ids = sorted(i for i in self.ids if prefix is None or i.startswith(prefix))
        for start in range(0, len(ids), 100):
            yield ids[start:start + 100]

    def delete(self, ids, namespace=None):
        self.deleted.extend(ids)
        self.ids.difference_update(ids)


class FakeVectorStore:
    """Records add_texts calls and writes the IDs into a FakeIndex."""

    def __init__(self, index):
        self.index = index
        self.records = {}

    def add_texts(self, texts, metadatas=None, ids=None, namespace=None):
        for text, metadata, vid in zip(texts, metadatas, ids):
            self.records[vid] = (text, metadata)
            self.index.ids.add(vid)
        return ids

    def as_retriever(self, **kwargs):
        return object()


class FakeKnowledgeBase:
    def __init__(self, available=True):
        self.available = available
        self.deleted = []

    def get_vectorstore(self):
        return object() if self.available else None

    def delete_document(self, source_id):
        self.deleted.append(source_id)
        return 3


class FakeStorage:
    folder = "student_chatbot/pdfs"
    delivery_type = "authenticated"

    def __init__(self, configured=True):
        self.configured = configured
        self.uploaded = []
        self.deleted = []
        self.resources = []

    def is_configured(self):
        return self.configured

    def is_in_managed_folder(self, public_id):
        return public_id.startswith(self.folder + "/") and ".." not in public_id

    def upload_pdf(self, file):
        self.uploaded.append(file.filename)
        return {
            "public_id": f"{self.folder}/doc_abc12345",
            "original_filename": file.filename,
            "type": self.delivery_type,
            "bytes": 100,
        }

    def list_pdfs(self):
        return list(self.resources)

    def delete_pdf(self, public_id):
        self.deleted.append(public_id)
        return {"result": "ok"}

    def file_url(self, resource):
        return "https://signed.example.test/" + resource["public_id"]

    def download_pdf_bytes(self, resource):
        return resource["_bytes"]


class FakeChain:
    def __init__(self, answer=None, error=None):
        self.answer = answer
        self.error = error
        self.questions = []

    def invoke(self, inputs):
        self.questions.append(inputs["question"])
        if self.error:
            raise self.error
        return {"answer": self.answer}


# --- Fixtures ---------------------------------------------------------------------
@pytest.fixture
def knowledge_base():
    return FakeKnowledgeBase()


@pytest.fixture
def storage():
    return FakeStorage()


@pytest.fixture
def make_app(knowledge_base, storage):
    def _make(config_name="testing", **overrides):
        limiter.reset()
        return create_app(
            config_name,
            overrides=overrides or None,
            db_client=mongomock.MongoClient(),
            knowledge_base=knowledge_base,
            storage=storage,
        )

    return _make


@pytest.fixture
def app(make_app):
    return make_app()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_headers(client):
    response = client.post(
        "/api/admin/login",
        json={"email": "admin@example.test", "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.get_json()['token']}"}


@pytest.fixture
def user_headers(client):
    signup = client.post(
        "/api/signup",
        json={"username": "student1", "email": "student1@example.test", "password": "s3cure-pass"},
    )
    assert signup.status_code == 201
    login = client.post("/api/login", json={"username": "student1", "password": "s3cure-pass"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.get_json()['token']}"}


@pytest.fixture
def fake_chain(app, monkeypatch):
    """Replace the LangChain pipeline with a controllable fake."""
    chain = FakeChain(answer="Applications are submitted online.")
    chat_view = app.view_functions["chat.query"]
    service = chat_view.__wrapped__.__self__.chat_service
    monkeypatch.setattr(service, "get_conversation_chain", lambda session_id, store: chain)
    chain.service = service
    return chain
