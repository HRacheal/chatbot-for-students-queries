import logging
import os

from flask import jsonify, request
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)

# Safe, user-facing messages for common HTTP errors.
HTTP_ERROR_MESSAGES = {
    400: "Bad request",
    401: "Authentication required",
    403: "Forbidden",
    404: "Endpoint not found",
    405: "Method not allowed",
    413: "The uploaded file is too large",
    415: "Unsupported media type",
    429: "Too many requests. Please wait a moment and try again.",
}


def configure_tracing(app_config):
    """Configure LangChain/LangSmith tracing.

    Tracing is opt-in: it is only enabled when LANGSMITH_TRACING=true *and* an
    API key is configured. Otherwise it is explicitly disabled so prompts and
    user questions are never sent to a third party by accident.
    """
    enabled = bool(app_config.get("LANGSMITH_TRACING") and app_config.get("LANGSMITH_API_KEY"))
    flag = "true" if enabled else "false"
    os.environ["LANGSMITH_TRACING"] = flag
    os.environ["LANGCHAIN_TRACING_V2"] = flag
    if enabled:
        os.environ["LANGSMITH_API_KEY"] = app_config["LANGSMITH_API_KEY"]
        os.environ["LANGCHAIN_PROJECT"] = app_config.get("LANGCHAIN_PROJECT", "USIUBOT")
        os.environ["LANGCHAIN_ENDPOINT"] = app_config.get("LANGCHAIN_ENDPOINT", "")
        logger.warning("LangSmith tracing is ENABLED: prompts and questions are sent to LangSmith")

    # langchain-pinecone reads the key from the environment.
    if app_config.get("PINECONE_API_KEY"):
        os.environ["PINECONE_API_KEY"] = app_config["PINECONE_API_KEY"]
    return enabled


def register_security_headers(app):
    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cache-Control", "no-store")
        return response


class ErrorHandlingMiddleware:
    """Return consistent JSON errors without leaking internal details."""

    def __init__(self, app):
        self.app = app
        app.register_error_handler(HTTPException, self.handle_http_exception)
        app.register_error_handler(Exception, self.handle_exception)

    @staticmethod
    def handle_http_exception(error):
        code = error.code or 500
        message = HTTP_ERROR_MESSAGES.get(code, error.name)
        return jsonify({"error": message}), code

    def handle_exception(self, error):
        if isinstance(error, HTTPException):
            return self.handle_http_exception(error)
        from pymongo.errors import PyMongoError

        if isinstance(error, PyMongoError):
            logger.error("Database error on %s %s (%s)", request.method, request.path, type(error).__name__)
            return jsonify({"error": "The USIUBOT database is temporarily unavailable. Please try again shortly.",
                            "code": "database_unavailable"}), 503
        logger.exception("Unhandled error on %s %s", request.method, request.path)
        return jsonify({"error": "An unexpected error occurred. Please try again later."}), 500
