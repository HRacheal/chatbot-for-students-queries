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
    ADMIN_TOKEN_HOURS = _env_int("ADMIN_TOKEN_HOURS", 8)

    # Single bootstrap administrator (role-based staff accounts arrive in a later phase).
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
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GROQ_TIMEOUT = _env_int("GROQ_TIMEOUT", 30)
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

    if "*" in app_config.get("CORS_ORIGINS", []):
        errors.append("CORS_ORIGINS must list explicit origins; '*' is not allowed.")

    return errors
