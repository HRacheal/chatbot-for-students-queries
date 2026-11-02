from flask import Blueprint, g, jsonify, request

from services.official_links import LinkError
from utils.auth import admin_required, staff_actor
from utils.validation import ValidationError, get_json_object


def _serialize(entry):
    data = dict(entry)
    if data.get("updated_at") is not None and hasattr(data["updated_at"], "isoformat"):
        data["updated_at"] = data["updated_at"].isoformat()
    return data


def create_official_link_routes(catalogue, chat_service):
    """Admin-only management of the official fallback links shown when an answer can't be verified."""
    bp = Blueprint('official_links', __name__, url_prefix='/api/admin/official-links')

    @bp.route('', methods=['GET'])
    @admin_required
    def list_links():
        links = catalogue.merged(include_hidden=True)
        return jsonify({
            "links": [_serialize(link) for link in links],
            "counts": {"total": len(links), "reviewed": sum(link["reviewed"] for link in links),
                       "hidden": sum(link["hidden"] for link in links)},
        }), 200

    @bp.route('', methods=['POST'])
    @admin_required
    def save_link():
        try:
            data = get_json_object()
            link = catalogue.save(data, actor=staff_actor())
        except (ValidationError, LinkError) as e:
            return jsonify({"error": str(e)}), 400
        return jsonify({"link": _serialize(link)}), 200

    @bp.route('/preview', methods=['GET'])
    @admin_required
    def preview():
        """The links a user would be offered for this question (to check the fallback)."""
        question = (request.args.get("q") or "").strip()
        if not question or len(question) > 500:
            return jsonify({"error": "Enter a question (at most 500 characters)"}), 400
        return jsonify({"question": question, "places_to_look": chat_service.places_to_look(question)}), 200

    return bp
