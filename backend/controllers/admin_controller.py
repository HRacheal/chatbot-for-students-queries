from flask import current_app, jsonify

from services.admin_service import AdminService
from utils.validation import ValidationError, get_json_object, require_string, validate_object_id


class AdminController:
    """Controller for handling admin endpoints.

    Every method here must be registered behind ``admin_required``.
    Unexpected errors propagate to the global error handler, which logs them
    and returns a generic message.
    """

    def __init__(self, email_service=None, storage=None):
        self.admin_service = AdminService(email_service, storage)

    def get_stats(self):
        result, status_code = self.admin_service.get_dashboard_stats()
        return jsonify(result), status_code

    def get_unanswered_queries(self):
        result, status_code = self.admin_service.get_unanswered_queries()
        return jsonify(result), status_code

    def delete_query(self, query_id):
        try:
            validate_object_id(query_id, "query id")
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400
        result, status_code = self.admin_service.delete_query(query_id)
        return jsonify(result), status_code

    def get_chat_history(self):
        result, status_code = self.admin_service.get_all_chat_history()
        return jsonify(result), status_code

    def get_query_analytics(self):
        result, status_code = self.admin_service.get_query_analytics()
        return jsonify(result), status_code

    def add_response(self):
        try:
            data = get_json_object()
            query_id = validate_object_id(data.get("id"), "query id")
            response = require_string(
                data, "response", current_app.config["MAX_RESPONSE_LENGTH"], "Response"
            )
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400

        result, status_code = self.admin_service.add_response_to_query(query_id, response)
        return jsonify(result), status_code
