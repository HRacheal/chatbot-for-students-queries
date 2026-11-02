"""
USIUBOT API (adapted from the chatbot-for-students-queries project).

Flask application factory. Start locally with ``python app.py``; in
production run ``gunicorn wsgi:app``.
"""

import logging
import os
import sys
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
from routes.enquiry_routes import create_enquiry_routes
from routes.guidance_routes import create_guidance_routes
from routes.official_link_routes import create_official_link_routes
from routes.pdf_routes import create_pdf_routes
from routes.source_routes import create_source_routes
from routes.dataset_routes import create_dataset_routes
from routes.staff_routes import create_staff_routes
from services.audit_service import AuditLog
from services.chat_service import ChatService
from services.cloudinary_service import CloudinaryService
from services.department_routing import DepartmentRouting
from services.email_service import EmailService
from services.enquiry_service import EnquiryService
from services.guidance_service import GuidanceService
from services.knowledge_base import KnowledgeBase
from services.live_retrieval import DEFAULT_CATALOGUE, LiveRetriever
from services.official_links import ManagedCatalogue
from services.sources import SourceRegistry
from services.staff_service import StaffService
from services.web_access import WebsiteAccess
from flask import g, request

from utils.auth import admin_required
from utils.logging_utils import configure_logging

logger = logging.getLogger(__name__)


def create_app(config_name=None, overrides=None, db_client=None, knowledge_base=None, storage=None,
               website_access=None):
    """Application factory.

    ``overrides``, ``db_client``, ``knowledge_base``, ``storage`` and ``website_access``
    let tests run the real application against in-memory or fake services.
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
        raise RuntimeError("Failed to connect to the database. " + (db_instance.last_error or ""))

    email_service = EmailService(app.config)
    storage = storage or CloudinaryService(app.config)
    # The knowledge base connects lazily on first use, so startup never writes
    # to the vector index or downloads documents.
    knowledge_base = knowledge_base or KnowledgeBase(app.config)
    app.extensions["email_service"] = email_service
    app.extensions["storage"] = storage
    app.extensions["knowledge_base"] = knowledge_base
    # Chat answers come from approved sources in the local MongoDB index. The
    # Pinecone knowledge base above is only used by the legacy PDF management routes.
    source_registry = SourceRegistry(db_instance.get_collection, app.config)
    # Live retrieval of official pages: catalogue of candidate URLs (metadata only) plus
    # permitted in-memory fetching. Disabled unless LIVE_RETRIEVAL_ENABLED=true.
    website = website_access or WebsiteAccess(app.config)
    # The file catalogue plus administrator changes stored in MongoDB (see services/official_links.py).
    catalogue = ManagedCatalogue(db_instance.get_collection, app.config.get("OFFICIAL_PAGES_FILE") or DEFAULT_CATALOGUE,
                                 website.is_trusted)
    live_retriever = LiveRetriever(app.config, website, catalogue)
    source_registry.live_url_checker = website.is_trusted
    department_routing = DepartmentRouting(db_instance.get_collection, app.config)
    chat_service = ChatService(source_registry, app.config, live_retriever, catalogue, routing=department_routing)
    enquiry_service = EnquiryService(db_instance.get_collection, app.config, email_service, department_routing)
    try:
        migrated = enquiry_service.migrate_legacy_statuses()
        if migrated:
            logger.info("Renamed %d enquiry statuses from an earlier version", migrated)
    except Exception as e:
        logger.warning("Enquiry status migration skipped (%s)", type(e).__name__)
    chat_service.staff_reply_email_available = email_service.is_configured
    guidance_service = GuidanceService(db_instance.get_collection, app.config, catalogue, website.is_trusted)
    staff_service = StaffService(db_instance.get_collection, app.config)
    audit = AuditLog(db_instance.get_collection)
    app.extensions["staff_service"] = staff_service
    app.extensions["audit_log"] = audit
    app.extensions["source_registry"] = source_registry
    app.extensions["chat_service"] = chat_service
    app.extensions["live_retriever"] = live_retriever
    app.extensions["enquiry_service"] = enquiry_service
    app.extensions["department_routing"] = department_routing
    app.extensions["guidance_service"] = guidance_service
    app.extensions["official_links"] = catalogue
    logger.info("Live retrieval %s (%d catalogue pages, %d reviewed)",
                "enabled" if live_retriever.enabled else "disabled",
                len(catalogue.entries), catalogue.reviewed_count)

    admin_controller = AdminController(email_service, storage, source_registry, enquiry_service)
    app.register_blueprint(create_auth_routes(app, email_service, staff_service, audit))
    app.register_blueprint(create_staff_routes(staff_service, audit))
    app.register_blueprint(create_chat_routes(chat_service))
    app.register_blueprint(create_admin_routes(admin_controller))
    app.register_blueprint(create_legacy_admin_routes(admin_controller))
    app.register_blueprint(create_pdf_routes(storage, knowledge_base))
    app.register_blueprint(create_source_routes(source_registry))
    app.register_blueprint(create_dataset_routes(source_registry, department_routing))
    app.register_blueprint(create_enquiry_routes(enquiry_service, staff_service, audit, db_instance.get_collection))
    app.register_blueprint(create_guidance_routes(guidance_service, live_retriever))
    app.register_blueprint(create_official_link_routes(catalogue, chat_service))

    _register_audit_hook(app, audit)

    @app.route('/health', methods=['GET'])
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Liveness plus a database check. No configuration or error details are returned."""
        database = "ok" if db_instance.ping() else "unavailable"
        return jsonify({
            "status": "healthy" if database == "ok" else "degraded",
            "database": database,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }), 200 if database == "ok" else 503

    @app.route('/', methods=['GET'])
    def root():
        return jsonify({"message": "USIUBOT API"}), 200

    if app.config["ENABLE_DEBUG_ROUTES"] and config_name != "production":
        _register_debug_routes(app, email_service)
        logger.warning("Debug routes are enabled (admin token required)")

    return app


# Staff changes recorded automatically (enquiries, staff accounts and sign-in record their own entries).
AUDITED_PREFIXES = ("/api/admin/sources", "/api/admin/dataset", "/api/admin/routing", "/api/admin/official-links",
                    "/api/admin/programme-requirements", "/api/pdfs", "/api/add-response", "/api/admin/add-response",
                    "/api/delete-query", "/api/admin/delete-query")


def _register_audit_hook(app, audit):
    """Write an audit entry for every successful change made through the administration API.

    Only the endpoint, the ids in the URL and the new status (if any) are stored; never request bodies.
    """

    @app.after_request
    def audit_admin_changes(response):
        if request.method in ("POST", "PUT", "DELETE") and response.status_code < 400 \
                and request.path.startswith(AUDITED_PREFIXES) and getattr(g, "staff", None):
            details = {k: v for k, v in (request.view_args or {}).items()}
            body = request.get_json(silent=True) if request.is_json else None
            if isinstance(body, dict):
                if isinstance(body.get("status"), str):
                    details["status"] = body["status"][:40]
                if body.get("dry_run") is True:
                    details["dry_run"] = True
                if isinstance(body.get("ids"), list):
                    details["count"] = len(body["ids"])
            audit.record(request.endpoint or request.path, g.staff, request.blueprint,
                         next(iter((request.view_args or {}).values()), None), details)
        return response


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
    try:
        app = create_app(env)
    except ConfigurationError as e:
        # Without a running API the frontend's dev proxy can only answer /api/* with an error.
        sys.exit(f"USIUBOT API not started. {e}\n"
                 "Copy backend/.env.example to backend/.env and fill in the required values, "
                 "or run `python -m tools.run_local` for a local test server.")
    except RuntimeError as e:
        # Database unreachable: the message explains the cause without credentials.
        sys.exit(f"USIUBOT API not started. {e}\n"
                 "Run `python -m tools.connection_check` for details.")
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 5000))
    logger.info("Starting API in %s mode on http://%s:%d", env, host, port)
    logger.info("Database: %s", db_instance.describe())
    app.run(host=host, port=port, debug=app.config.get("DEBUG", False))


if __name__ == "__main__":
    main()
