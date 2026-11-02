import logging

from flask import current_app, g, jsonify

from models.models import ChatHistory, QueryLog
from services.routing import classify_department
from utils.auth import get_optional_user_id
from utils.helpers import format_response_data
from utils.validation import ValidationError, get_json_object, require_string

logger = logging.getLogger(__name__)


class ChatController:
    """Controller for handling chat endpoints"""

    def __init__(self, chat_service):
        self.chat_service = chat_service
        self.chat_history_model = ChatHistory()
        self.query_log = QueryLog()

    def query(self):
        """Handle a user question. Anonymous users are allowed."""
        try:
            data = get_json_object()
            question = require_string(
                data, "question", current_app.config["MAX_QUESTION_LENGTH"], "Question"
            )
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400

        user_id = get_optional_user_id()
        result, status_code = self.chat_service.process_query(
            question, data.get("session_id"), user_id
        )
        try:
            self.query_log.record(
                result.get("status", "error"),
                classify_department(question)[0],
                result.get("evidence"),
                authenticated=bool(user_id),
            )
        except Exception as e:  # analytics must never break answering
            logger.error("Could not record query statistics (%s)", type(e).__name__)
        return jsonify(result), status_code

    def get_chat_history(self):
        """Get the logged-in user's chat history (route requires ``login_required``)."""
        history = self.chat_history_model.get_user_history(g.user_id)
        # Citations are re-checked so a source archived since then is no longer linked.
        for chat in history:
            chat["citations"] = self.chat_service.registry.check_citations(chat.get("citations"))
        return jsonify({"history": format_response_data(history)}), 200
