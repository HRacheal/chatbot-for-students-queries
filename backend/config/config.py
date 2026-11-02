"""Application configuration.

All secrets and environment-specific values come from environment variables
(or a local, git-ignored ``backend/.env`` file). See ``backend/.env.example``
for the full list.
"""

import os
from dotenv import load_dotenv

# Load environment variables from backend/.env if present. Existing environment
# variables always take precedence over values in the file.
load_dotenv()

# Values that must never be accepted as a JWT signing secret.
INSECURE_SECRET_KEYS = {
    "",
    "your_secret_key",
    "your_secure_random_secret_key",
    "secret",
    "changeme",
    "change-me",
}
MIN_SECRET_KEY_LENGTH = 32


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name, default):
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


def _env_list(name, default):
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


class Config:
    """Base configuration shared by every environment."""

    # --- Security ---------------------------------------------------------
    # Required. Generate with: python -c "import secrets; print(secrets.token_urlsafe(48))"
    SECRET_KEY = os.getenv("SECRET_KEY")
    USER_TOKEN_HOURS = _env_int("USER_TOKEN_HOURS", 24)
    # Staff dashboard sessions (all roles) expire after this many hours.
    ADMIN_TOKEN_HOURS = _env_int("ADMIN_TOKEN_HOURS", 8)
    # Failed staff sign-ins before the account is locked, and for how long.
    STAFF_MAX_FAILED_LOGINS = _env_int("STAFF_MAX_FAILED_LOGINS", 5)
    STAFF_LOCKOUT_MINUTES = _env_int("STAFF_LOCKOUT_MINUTES", 15)
    # bcrypt cost factor for staff passwords (12 recommended; tests use a lower value for speed).
    STAFF_BCRYPT_ROUNDS = _env_int("STAFF_BCRYPT_ROUNDS", 12)

    # Optional bootstrap Super Administrator (for first setup). Staff accounts with roles are
    # created in the dashboard or with `python -m tools.create_staff`.
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

    # Browser origins allowed to call the API. Bearer tokens are used, not cookies,
    # so credentialed CORS is not needed.
    CORS_ORIGINS = _env_list(
        "CORS_ORIGINS", ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    # Debug endpoints are never registered in production, and require an admin token.
    ENABLE_DEBUG_ROUTES = _env_bool("ENABLE_DEBUG_ROUTES", False)

    # Number of reverse proxies in front of the app (for correct client IPs).
    TRUST_PROXY_HOPS = _env_int("TRUST_PROXY_HOPS", 0)

    # Request limits
    MAX_CONTENT_LENGTH = _env_int("MAX_UPLOAD_MB", 10) * 1024 * 1024
    MAX_QUESTION_LENGTH = _env_int("MAX_QUESTION_LENGTH", 2000)
    MAX_RESPONSE_LENGTH = _env_int("MAX_RESPONSE_LENGTH", 5000)

    # Simple per-client rate limits (requests per minute, per process)
    RATE_LIMIT_ENABLED = _env_bool("RATE_LIMIT_ENABLED", True)
    QUERY_RATE_LIMIT_PER_MINUTE = _env_int("QUERY_RATE_LIMIT_PER_MINUTE", 20)
    AUTH_RATE_LIMIT_PER_MINUTE = _env_int("AUTH_RATE_LIMIT_PER_MINUTE", 10)

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # --- Database ---------------------------------------------------------
    MONGODB_URI = os.getenv("MONGO_URI")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "chatbot")

    # --- Language model (Groq) ---------------------------------------------
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
    GROQ_MODEL = os.getenv("GROQ_MODEL", "").strip() or DEFAULT_GROQ_MODEL  # an empty value uses the default
    GROQ_TIMEOUT = _env_int("GROQ_TIMEOUT", 30)
    GROQ_MAX_TOKENS = _env_int("GROQ_MAX_TOKENS", 2048)
    # Reasoning models (openai/gpt-oss-*): low | medium | high | default. Empty = "low" for gpt-oss.
    GROQ_REASONING_EFFORT = os.getenv("GROQ_REASONING_EFFORT", "")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))

    # --- Embeddings and vector store ----------------------------------------
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    EMBEDDING_DIMENSION = _env_int("EMBEDDING_DIMENSION", 384)
    RETRIEVAL_K = _env_int("RETRIEVAL_K", 10)

    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "student-chatbot")
    PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE", "course_materials")
    PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
    PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")

    # --- Document storage (Cloudinary) --------------------------------------
    CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
    PDF_FOLDER = os.getenv("CLOUDINARY_PDF_FOLDER", "student_chatbot/pdfs")
    # "authenticated" = files are only reachable through signed URLs (default).
    # "upload" = public files (legacy behaviour; not recommended).
    CLOUDINARY_DELIVERY_TYPE = os.getenv("CLOUDINARY_DELIVERY_TYPE", "authenticated")
    MAX_DOWNLOAD_MB = _env_int("MAX_DOWNLOAD_MB", 50)
    MAX_PDF_PAGES = _env_int("MAX_PDF_PAGES", 500)

    # --- Email (SMTP) -------------------------------------------------------
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = _env_int("MAIL_PORT", 587)
    MAIL_USE_TLS = _env_bool("MAIL_USE_TLS", True)
    MAIL_USE_SSL = _env_bool("MAIL_USE_SSL", False)
    MAIL_TIMEOUT = _env_int("MAIL_TIMEOUT", 15)
    MAIL_USERNAME = os.getenv("EMAIL_USER")
    # Strip non-breaking spaces that often sneak in when app passwords are pasted.
    _raw_password = os.getenv("EMAIL_PASS")
    MAIL_PASSWORD = _raw_password.replace("\xa0", " ") if _raw_password else None
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER") or os.getenv("EMAIL_USER")

    # --- LLM tracing (LangSmith) — opt-in only ------------------------------
    # Tracing sends prompts, questions and retrieved text to a third party,
    # so it is disabled unless explicitly enabled.
    LANGSMITH_TRACING = _env_bool("LANGSMITH_TRACING", False)
    LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
    LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "USIUBOT")
    LANGCHAIN_ENDPOINT = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")

    # --- Approved sources and local retrieval ----------------------------------
    # Citations and source URLs must be on one of these domains (subdomains included).
    ALLOWED_SOURCE_DOMAINS = _env_list("ALLOWED_SOURCE_DOMAINS", ["usiu.ac.ke"])
    SOURCE_STALE_DAYS = _env_int("SOURCE_STALE_DAYS", 365)
    # Ranking multiplier for out-of-date sources (1.0 = no preference for current sources).
    SOURCE_STALE_PENALTY = float(os.getenv("SOURCE_STALE_PENALTY", "0.85"))
    SOURCE_MAX_TEXT_CHARS = _env_int("SOURCE_MAX_TEXT_CHARS", 200000)
    # Sources given to the model per question (each part of a multi-part question gets one of them).
    SOURCE_CONTEXT_COUNT = _env_int("SOURCE_CONTEXT_COUNT", 6)
    # Approved sections up to this many characters are given to the model whole (0 = only the best passages).
    SOURCE_FULL_SECTION_CHARS = _env_int("SOURCE_FULL_SECTION_CHARS", 6000)
    # Matching sections from the same official page as a chosen source are added up to this total
    # context size in characters (0 = off).
    # About 3,500 prompt tokens at most; keep it within the Groq account's tokens-per-minute limit.
    SOURCE_CONTEXT_MAX_CHARS = _env_int("SOURCE_CONTEXT_MAX_CHARS", 12000)
    # Weak matches are not given to the model: a source must score at least this share of the best
    # source's score (the best source for each part of a multi-part question is always kept), and a
    # same-page section at least SOURCE_SIBLING_MIN_RELATIVE of it.
    SOURCE_RELATIVE_MIN_SCORE = float(os.getenv("SOURCE_RELATIVE_MIN_SCORE", "0.3"))
    SOURCE_SIBLING_MIN_RELATIVE = float(os.getenv("SOURCE_SIBLING_MIN_RELATIVE", "0.5"))
    # Sources of the department a question is about rank this many times higher (1 = off).
    SOURCE_DEPARTMENT_BOOST = float(os.getenv("SOURCE_DEPARTMENT_BOOST", "1.5"))
    RETRIEVAL_MIN_SCORE = float(os.getenv("RETRIEVAL_MIN_SCORE", "0.5"))
    # Fraction of a question's key words a source passage must contain to count as relevant.
    RETRIEVAL_MIN_COVERAGE = float(os.getenv("RETRIEVAL_MIN_COVERAGE", "0.5"))
    SOURCE_INDEX_TTL = _env_int("SOURCE_INDEX_TTL", 60)
    # External bodies whose dataset records may be cited (always labelled "external, not USIU-Africa policy").
    EXTERNAL_SOURCE_DOMAINS = _env_list("EXTERNAL_SOURCE_DOMAINS", ["kuccps.net", "cue.or.ke", "knqa.go.ke"])
    # The completed USIUBOT dataset (imported as drafts by the admin Sources tab or tools.import_dataset).
    DATASET_DIR = os.getenv("DATASET_DIR") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "usiubot_datasets")
    # Records made for automated tests are never retrieved outside test mode.
    ALLOW_TEST_SOURCES = False

    # --- Live retrieval of official pages --------------------------------------
    # Off until a permitted access check from the deployment host succeeds
    # (python -m tools.live_check). robots.txt is always obeyed, even when enabled.
    LIVE_RETRIEVAL_ENABLED = _env_bool("LIVE_RETRIEVAL_ENABLED", False)
    # Exact host names only; subdomains are not trusted automatically. Portal hosts are always refused.
    TRUSTED_SOURCE_HOSTS = _env_list("TRUSTED_SOURCE_HOSTS", ["www.usiu.ac.ke"])
    LIVE_USER_AGENT = os.getenv("LIVE_USER_AGENT", "USIUBOT/1.0")
    OFFICIAL_PAGES_FILE = os.getenv("OFFICIAL_PAGES_FILE") or None  # default: config/official_pages.json
    LIVE_CONNECT_TIMEOUT = _env_int("LIVE_CONNECT_TIMEOUT", 5)
    LIVE_READ_TIMEOUT = _env_int("LIVE_READ_TIMEOUT", 10)
    LIVE_QUESTION_BUDGET_SECONDS = _env_int("LIVE_QUESTION_BUDGET_SECONDS", 15)
    LIVE_MAX_PAGES_PER_QUESTION = _env_int("LIVE_MAX_PAGES_PER_QUESTION", 3)
    LIVE_MAX_PAGE_BYTES = _env_int("LIVE_MAX_PAGE_KB", 2000) * 1024
    LIVE_PAGE_CACHE_SECONDS = _env_int("LIVE_PAGE_CACHE_SECONDS", 86400)
    LIVE_ROBOTS_CACHE_SECONDS = _env_int("LIVE_ROBOTS_CACHE_SECONDS", 86400)
    LIVE_FAILURE_CACHE_SECONDS = _env_int("LIVE_FAILURE_CACHE_SECONDS", 900)
    LIVE_CACHE_MAX_PAGES = _env_int("LIVE_CACHE_MAX_PAGES", 200)
    LIVE_CACHE_MAX_MB = _env_int("LIVE_CACHE_MAX_MB", 20)
    # "Unverified search" link (site:www.usiu.ac.ke) shown when an answer can't be verified.
    # It opens in the user's browser; the server never contacts the search engine.
    SITE_SEARCH_LINK_ENABLED = _env_bool("SITE_SEARCH_LINK_ENABLED", True)

    # --- Unresolved enquiries -------------------------------------------------------
    # Comma-separated staff addresses notified of new enquiries (optional; enquiries
    # are always visible in the admin dashboard).
    ENQUIRY_EMAIL_ADMISSIONS = os.getenv("ENQUIRY_EMAIL_ADMISSIONS", "")
    ENQUIRY_EMAIL_REGISTRAR = os.getenv("ENQUIRY_EMAIL_REGISTRAR", "")
    ENQUIRY_EMAIL_MARKETING = os.getenv("ENQUIRY_EMAIL_MARKETING", "")
    ENQUIRY_EMAIL_ACADEMIC_PROGRAMMES = os.getenv("ENQUIRY_EMAIL_ACADEMIC_PROGRAMMES", "")
    ENQUIRY_EMAIL_GENERAL_UNIVERSITY = os.getenv("ENQUIRY_EMAIL_GENERAL_UNIVERSITY", "")
    ENQUIRY_EMAIL_FINANCE = os.getenv("ENQUIRY_EMAIL_FINANCE", "")
    ENQUIRY_EMAIL_STUDENT_AFFAIRS = os.getenv("ENQUIRY_EMAIL_STUDENT_AFFAIRS", "")
    ENQUIRY_EMAIL_ICT = os.getenv("ENQUIRY_EMAIL_ICT", "")
    ENQUIRY_EMAIL_LIBRARY = os.getenv("ENQUIRY_EMAIL_LIBRARY", "")
    # Staff delivery addresses can also be set per department in the admin Routing tab (stored in MongoDB);
    # those override the ENQUIRY_EMAIL_* values above.
    # Minimum share of a question's key words a suggested official page must match.
    FALLBACK_LINK_MIN_COVERAGE = float(os.getenv("FALLBACK_LINK_MIN_COVERAGE", "0.5"))
    ENQUIRY_RATE_LIMIT_PER_MINUTE = _env_int("ENQUIRY_RATE_LIMIT_PER_MINUTE", 5)
    # Notification emails (only sent when SMTP is configured; every attempt is recorded on the enquiry).
    ENQUIRY_NOTIFY_ASSIGNEE = _env_bool("ENQUIRY_NOTIFY_ASSIGNEE", True)
    ENQUIRY_NOTIFY_ENQUIRER = _env_bool("ENQUIRY_NOTIFY_ENQUIRER", True)
    # `python -m tools.enquiry_reminders` reminds departments of enquiries without updates for this long.
    ENQUIRY_REMINDER_DAYS = _env_int("ENQUIRY_REMINDER_DAYS", 3)

    # --- Degree guidance (results-slip upload) --------------------------------------
    GUIDANCE_MAX_UPLOAD_MB = _env_int("GUIDANCE_MAX_UPLOAD_MB", 5)
    GUIDANCE_RATE_LIMIT_PER_MINUTE = _env_int("GUIDANCE_RATE_LIMIT_PER_MINUTE", 10)

    # --- Conversation memory ------------------------------------------------
    SESSION_TIMEOUT = _env_int("SESSION_TIMEOUT", 7200)  # seconds
    MAX_SESSIONS = _env_int("MAX_SESSIONS", 1000)


class DevelopmentConfig(Config):
    DEBUG = True
    ENV_NAME = "development"


class ProductionConfig(Config):
    DEBUG = False
    ENV_NAME = "production"


class TestingConfig(Config):
    DEBUG = False
    TESTING = True
    ENV_NAME = "testing"
    ALLOW_TEST_SOURCES = True


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": ProductionConfig,
}


class ConfigurationError(RuntimeError):
    """Raised when the application is started with unsafe or invalid settings."""


def validate_config(app_config):
    """Return a list of problems that must be fixed before the app can start."""
    errors = []

    secret = app_config.get("SECRET_KEY") or ""
    if secret in INSECURE_SECRET_KEYS:
        errors.append("SECRET_KEY is missing or uses a known placeholder value.")
    elif len(secret) < MIN_SECRET_KEY_LENGTH:
        errors.append(f"SECRET_KEY must be at least {MIN_SECRET_KEY_LENGTH} characters long.")

    if app_config.get("CLOUDINARY_DELIVERY_TYPE") not in ("authenticated", "upload"):
        errors.append("CLOUDINARY_DELIVERY_TYPE must be 'authenticated' or 'upload'.")

    domains = app_config.get("ALLOWED_SOURCE_DOMAINS") or []
    if not domains or any("*" in d or "/" in d or not d.strip() for d in domains):
        errors.append("ALLOWED_SOURCE_DOMAINS must list plain domain names (e.g. usiu.ac.ke).")

    from services.web_access import check_trusted_hosts

    hosts = app_config.get("TRUSTED_SOURCE_HOSTS") or []
    if not hosts:
        errors.append("TRUSTED_SOURCE_HOSTS must list at least one exact host (e.g. www.usiu.ac.ke).")
    errors.extend(check_trusted_hosts(hosts))

    external = app_config.get("EXTERNAL_SOURCE_DOMAINS") or []
    if any("*" in d or "/" in d or not d.strip() for d in external):
        errors.append("EXTERNAL_SOURCE_DOMAINS must list plain domain names (e.g. kuccps.net).")
    if set(d.lower() for d in external) & set(d.lower() for d in domains):
        errors.append("EXTERNAL_SOURCE_DOMAINS must not include an official USIU-Africa domain.")
    if app_config.get("ENV_NAME") == "production" and app_config.get("ALLOW_TEST_SOURCES"):
        errors.append("ALLOW_TEST_SOURCES must be off in production.")

    if not 1 <= app_config.get("SOURCE_DEPARTMENT_BOOST", 1.5) <= 5:
        errors.append("SOURCE_DEPARTMENT_BOOST must be between 1 and 5.")
    if not 0 < app_config.get("SOURCE_STALE_PENALTY", 0.85) <= 1:
        errors.append("SOURCE_STALE_PENALTY must be greater than 0 and at most 1.")

    if "*" in app_config.get("CORS_ORIGINS", []):
        errors.append("CORS_ORIGINS must list explicit origins; '*' is not allowed.")

    return errors
