"""
Student Chatbot Application (being adapted into USIUBOT).

Flask application factory. Start locally with ``python app.py``; in
production run ``gunicorn wsgi:app``.
"""

import logging
import os
from datetime import datetime, timezone

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from config.config import ConfigurationError, ProductionConfig, config, validate_config
from config.database import db_instance
from controllers.admin_controller import AdminController
from middleware.middleware import ErrorHandlingMiddleware, configure_tracing, register_security_headers
from routes.admin_routes import create_admin_routes, create_legacy_admin_routes
from routes.auth_routes import create_auth_routes
from routes.chat_routes import create_chat_routes
from routes.pdf_routes import create_pdf_routes
from services.cloudinary_service import CloudinaryService
from services.email_service import EmailService
from services.knowledge_base import KnowledgeBase
from utils.auth import admin_required
from utils.logging_utils import configure_logging

logger = logging.getLogger(__name__)


def create_app(config_name=None, overrides=None, db_client=None, knowledge_base=None, storage=None):
    """Application factory.

    ``overrides``, ``db_client``, ``knowledge_base`` and ``storage`` let tests
    run the real application against in-memory or fake services.
    """
    config_name = config_name or os.getenv("FLASK_ENV", "production")
    app = Flask(__name__)
    app.config.from_object(config.get(config_name, ProductionConfig))
    if overrides:
        app.config.update(overrides)

    configure_logging(app.config["LOG_LEVEL"])

    problems = validate_config(app.config)
    if problems:
        raise ConfigurationError("Invalid configuration: " + " ".join(problems))

    if app.config["TRUST_PROXY_HOPS"]:
        hops = app.config["TRUST_PROXY_HOPS"]
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=hops, x_host=hops)

    # Bearer tokens are sent in the Authorization header, so credentialed CORS is not needed.
    CORS(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
        supports_credentials=False,
    )

    configure_tracing(app.config)
    ErrorHandlingMiddleware(app)
    register_security_headers(app)

    if not db_instance.connect(app.config["MONGODB_URI"], app.config["MONGO_DB_NAME"], client=db_client):
        raise RuntimeError("Failed to connect to database")

    email_service = EmailService(app.config)
    storage = storage or CloudinaryService(app.config)
    # The knowledge base connects lazily on first use, so startup never writes
    # to the vector index or downloads documents.
    knowledge_base = knowledge_base or KnowledgeBase(app.config)
    app.extensions["email_service"] = email_service
    app.extensions["storage"] = storage
    app.extensions["knowledge_base"] = knowledge_base

    admin_controller = AdminController(email_service, storage)
    app.register_blueprint(create_auth_routes(app, email_service))
    app.register_blueprint(create_chat_routes(knowledge_base, app.config))
    app.register_blueprint(create_admin_routes(admin_controller))
    app.register_blueprint(create_legacy_admin_routes(admin_controller))
    app.register_blueprint(create_pdf_routes(storage, knowledge_base))

    @app.route('/health', methods=['GET'])
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }), 200

    @app.route('/', methods=['GET'])
    def root():
        return jsonify({"message": "Student Chatbot API"}), 200

    if app.config["ENABLE_DEBUG_ROUTES"] and config_name != "production":
        _register_debug_routes(app, email_service)
        logger.warning("Debug routes are enabled (admin token required)")

    return app


def _register_debug_routes(app, email_service):
    """Diagnostic endpoints. Never registered in production; admin-only."""

    @app.route('/debug/routes', methods=['GET'])
    @admin_required
    def list_routes():
        routes = [
            {"endpoint": rule.endpoint, "methods": sorted(rule.methods), "url": str(rule)}
            for rule in app.url_map.iter_rules()
        ]
        return jsonify({"routes": routes}), 200

    @app.route('/debug/email', methods=['GET'])
    @admin_required
    def email_status():
        return jsonify({"mail_configured": email_service.is_configured()}), 200

    @app.route('/debug/send-test-email', methods=['POST'])
    @admin_required
    def send_test_email():
        sender = app.config.get("MAIL_USERNAME")
        if not sender or not email_service.send(sender, "Test email", "SMTP test from the chatbot."):
            return jsonify({"error": "Test email could not be sent"}), 502
        return jsonify({"status": "Test email sent"}), 200


def main():
    """Run the development server."""
    env = os.getenv("FLASK_ENV", "development")
    app = create_app(env)
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 5000))
    logger.info("Starting API in %s mode on http://%s:%d", env, host, port)
    app.run(host=host, port=port, debug=app.config.get("DEBUG", False))


if __name__ == "__main__":
    main()
