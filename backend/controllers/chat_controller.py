from flask import current_app, g, jsonify

from models.models import ChatHistory
from services.chat_service import ChatService
from utils.auth import get_optional_user_id
from utils.helpers import format_response_data
from utils.validation import ValidationError, get_json_object, require_string


class ChatController:
    """Controller for handling chat endpoints"""

    def __init__(self, knowledge_base, settings):
        self.chat_service = ChatService(knowledge_base, settings)
        self.chat_history_model = ChatHistory()

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
        return jsonify(result), status_code

    def get_chat_history(self):
        """Get the logged-in user's chat history (route requires ``login_required``)."""
        history = self.chat_history_model.get_user_history(g.user_id)
        return jsonify({"history": format_response_data(history)}), 200
