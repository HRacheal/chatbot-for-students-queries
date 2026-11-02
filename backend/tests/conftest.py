"""Shared test fixtures.

The tests never contact real external services: MongoDB is replaced with
mongomock, and the vector store, document storage, LLM and SMTP server are
replaced with in-memory fakes.
"""

import os
import sys
from types import SimpleNamespace

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
    # Live retrieval stays off unless a test enables it with a fake transport.
    "LIVE_RETRIEVAL_ENABLED": "false",
    "TRUSTED_SOURCE_HOSTS": "www.usiu.ac.ke",
    "OFFICIAL_PAGES_FILE": "",
    "ENQUIRY_EMAIL_ADMISSIONS": "",
    "ENQUIRY_EMAIL_REGISTRAR": "",
    "ENQUIRY_EMAIL_MARKETING": "",
    # Rate limits for the new endpoints are tested explicitly; keep them out of the way elsewhere.
    "ENQUIRY_RATE_LIMIT_PER_MINUTE": "1000",
    "GUIDANCE_RATE_LIMIT_PER_MINUTE": "1000",
    # Fast password hashing for tests only (production default is 12).
    "STAFF_BCRYPT_ROUNDS": "4",
    "STAFF_MAX_FAILED_LOGINS": "5",
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


class FakeLLM:
    """Stand-in for the chat model. Records the questions it was asked."""

    def __init__(self, answer="Applications are submitted online [1].", error=None, scope_answer="OUT_OF_SCOPE"):
        self.answer = answer
        self.error = error
        self.scope_answer = scope_answer
        self.questions = []
        self.prompts = []
        self.scope_checks = []

    def invoke(self, messages):
        human = messages[-1].content
        if human.startswith("<message>"):  # scope check for a question with no matching source
            self.scope_checks.append(human.split("\n")[1])
            return SimpleNamespace(content=self.scope_answer)
        self.prompts.append(human)
        self.questions.append(human.split("<question>\n", 1)[1].split("\n</question>", 1)[0])
        if self.error:
            raise self.error
        return SimpleNamespace(content=self.answer)


# Synthetic sources for tests only. They are NOT real USIU-Africa information.
TEST_SOURCES = [
    {
        "url": "https://www.usiu.ac.ke/test-fixture/how-to-apply/",
        "title": "TEST FIXTURE: How to Apply",
        "department": "admissions",
        "source_date": "2026-01",
        "text": "TEST FIXTURE. Applications are submitted online through the applicant portal. "
                "Each programme lists its entry requirements. Admitted applicants may ask to defer "
                "their admission. Advisers explain which programmes suit different academic qualifications.",
    },
    {
        "url": "https://www.usiu.ac.ke/test-fixture/registration/",
        "title": "TEST FIXTURE: Registration Procedures",
        "department": "registrar",
        "source_date": "2026-02-01",
        "text": "TEST FIXTURE. Registration opens online before each semester. Students request an "
                "official transcript from the Registrar in writing.",
    },
]


class FakeTransport:
    """Stand-in for the HTTP client used by ``WebsiteAccess``.

    ``routes`` maps a URL to ``(status, headers, body)`` or to an exception to raise.
    Every requested URL is recorded, so tests can prove what was (not) fetched.
    """

    def __init__(self, routes=None):
        self.routes = dict(routes or {})
        self.requests = []

    def get(self, url, headers=None, timeout=None, max_bytes=None):
        self.requests.append((url, dict(headers or {})))
        route = self.routes.get(url)
        if route is None:
            return 404, {"content-type": "text/html"}, b"<html><body>Not found</body></html>"
        if isinstance(route, Exception):
            raise route
        status, response_headers, body = route
        if max_bytes is not None and len(body) > max_bytes:
            from services.web_access import TOO_LARGE, FetchError

            raise FetchError(TOO_LARGE)
        return status, {k.lower(): v for k, v in response_headers.items()}, body

    def fetched(self, url):
        return any(u == url for u, _ in self.requests)


ROBOTS_ALLOW_USIUBOT = b"User-agent: USIUBOT\nAllow: /\n\nUser-agent: *\nDisallow: /\n"
ROBOTS_DENY_ALL = b"User-agent: Googlebot\nAllow: /\n\nUser-agent: *\nDisallow: /\n"


def html_page(title, body, published=None):
    meta = f'<meta property="article:modified_time" content="{published}">' if published else ""
    return (f"<html><head><title>{title}</title>{meta}</head><body><nav>Menu Home About</nav>"
            f"<main><h1>{title}</h1>{body}</main><footer>Copyright</footer></body></html>").encode("utf-8")


def add_source(registry, approve=True, **fields):
    data = {**TEST_SOURCES[0], **fields}
    source = registry.create(data)
    if approve:
        source = registry.set_status(str(source["_id"]), "approved")
    return source


# --- Fixtures ---------------------------------------------------------------------
@pytest.fixture
def knowledge_base():
    return FakeKnowledgeBase()


@pytest.fixture
def storage():
    return FakeStorage()


@pytest.fixture
def make_app(knowledge_base, storage):
    def _make(config_name="testing", website_access=None, **overrides):
        limiter.reset()
        return create_app(
            config_name,
            overrides=overrides or None,
            db_client=mongomock.MongoClient(),
            knowledge_base=knowledge_base,
            storage=storage,
            website_access=website_access,
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
def registry(app):
    return app.extensions["source_registry"]


@pytest.fixture
def approved_sources(registry):
    return [add_source(registry, **source) for source in TEST_SOURCES]


@pytest.fixture
def fake_llm(app, monkeypatch, approved_sources):
    """Replace the language model with a controllable fake (approved test sources are loaded)."""
    llm = FakeLLM()
    service = app.extensions["chat_service"]
    monkeypatch.setattr(service, "_get_llm", lambda: llm)
    llm.service = service
    return llm
