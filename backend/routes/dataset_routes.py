from flask import Blueprint, current_app, g, jsonify, request

from services.dataset_import import DatasetError, DatasetImporter
from services.department_routing import RoutingError
from services.sources import CATEGORIES, SourceError
from utils.auth import ROLE_DEPARTMENT_ADMIN, ROLE_SUPER_ADMIN, admin_required, staff_actor, staff_required
from utils.permissions import can_manage_department_settings, is_super, visible_departments
from utils.validation import ValidationError, get_json_object


def _actor():
    return staff_actor()


# Settings a Department Administrator may change for their own departments.
DEPARTMENT_ADMIN_ROUTING_FIELDS = ("delivery_emails", "notes")


def create_dataset_routes(registry, routing):
    """Admin-only: import/refresh the USIUBOT dataset as draft sources, test retrieval, configure routing."""
    bp = Blueprint("dataset", __name__, url_prefix="/api/admin")

    def importer():
        return DatasetImporter(registry, current_app.config.get("DATASET_DIR"))

    def body():
        try:
            return get_json_object()
        except ValidationError:
            return {}

    @bp.route("/dataset/status", methods=["GET"])
    @admin_required
    def dataset_status():
        return jsonify(importer().status()), 200

    @bp.route("/dataset/import", methods=["POST"])
    @admin_required
    def dataset_import():
        """Create/refresh draft sources from the dataset. ``{"dry_run": true}`` only reports. Never approves."""
        dry_run = body().get("dry_run") is True
        try:
            report = importer().run(dry_run=dry_run, actor=_actor())
        except DatasetError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            current_app.logger.error("Dataset import failed (%s)", type(e).__name__)
            return jsonify({"error": "The dataset could not be imported; the database may be unavailable"}), 503
        return jsonify({"report": report, "counts": registry.counts()}), 200

    @bp.route("/dataset/search", methods=["GET"])
    @admin_required
    def dataset_search():
        """Try a question against the approved index (what the chatbot would retrieve), optionally by category."""
        query = (request.args.get("q") or "").strip()
        if not query or len(query) > current_app.config.get("MAX_QUESTION_LENGTH", 1000):
            return jsonify({"error": "Enter a question"}), 400
        categories = [c for c in (request.args.get("category") or "").split(",") if c]
        if any(c not in CATEGORIES for c in categories):
            return jsonify({"error": "Unknown category"}), 400
        results = registry.retrieve(
            query, k=current_app.config.get("SOURCE_CONTEXT_COUNT", 4),
            min_score=current_app.config.get("RETRIEVAL_MIN_SCORE", 0.5),
            min_coverage=current_app.config.get("RETRIEVAL_MIN_COVERAGE", 0.5),
            categories=categories or None)
        chat = current_app.extensions["chat_service"]
        hits = []
        for number, result in enumerate(results, start=1):
            citation = chat._result_citation(number, result, with_excerpts=True)
            citation["score"] = round(result["score"], 3)
            hits.append(citation)
        return jsonify({"results": hits, "warnings": chat._warnings(hits, False)}), 200

    # --- routing --------------------------------------------------------------------
    @bp.route("/routing", methods=["GET"])
    @staff_required(roles=(ROLE_SUPER_ADMIN, ROLE_DEPARTMENT_ADMIN))
    def routing_list():
        visible = visible_departments(g.staff)
        departments = [d for d in routing.all() if visible is None or d["department"] in visible]
        return jsonify({"departments": departments, "full_access": is_super(g.staff)}), 200

    @bp.route("/routing/<department>", methods=["PUT"])
    @staff_required(roles=(ROLE_SUPER_ADMIN, ROLE_DEPARTMENT_ADMIN))
    def routing_update(department):
        if not can_manage_department_settings(g.staff, department):
            return jsonify({"error": "You can only change the settings of your own department"}), 403
        data = body()
        if not is_super(g.staff):
            refused = [k for k in data if k not in DEPARTMENT_ADMIN_ROUTING_FIELDS]
            if refused:
                return jsonify({"error": "Only a Super Administrator can change: " + ", ".join(refused)}), 403
        try:
            return jsonify({"department": routing.update(department, data, actor=_actor())}), 200
        except RoutingError as e:
            return jsonify({"error": str(e)}), 400

    @bp.route("/routing/import-contacts", methods=["POST"])
    @admin_required
    def routing_import():
        try:
            report = routing.import_dataset_contacts(current_app.config.get("DATASET_DIR"), actor=_actor())
        except RoutingError as e:
            return jsonify({"error": str(e)}), 400
        return jsonify({"report": report, "departments": routing.all()}), 200

    return bp


def bulk_status_view(registry):
    """POST /api/admin/sources/bulk-status ``{"ids": [...], "status": "approved", "note": ""}``."""

    def view():
        try:
            data = get_json_object()
            report = registry.bulk_set_status(data.get("ids"), data.get("status"), actor=_actor(),
                                              note=data.get("note") or "")
        except (ValidationError, SourceError) as e:
            return jsonify({"error": str(e)}), 400
        return jsonify({"report": report, "counts": registry.counts()}), 200

    return view
