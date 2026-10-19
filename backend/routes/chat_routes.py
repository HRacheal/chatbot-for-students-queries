from flask import Blueprint

from controllers.chat_controller import ChatController
from utils.auth import login_required
from utils.rate_limit import rate_limit


def create_chat_routes(knowledge_base, settings):
    """Create chat routes.

    Admin answers to queries are handled by the admin blueprints, not here.
    """
    chat_bp = Blueprint('chat', __name__, url_prefix='/api')
    chat_controller = ChatController(knowledge_base, settings)

    chat_bp.add_url_rule(
        '/query', 'query',
        rate_limit("query", "QUERY_RATE_LIMIT_PER_MINUTE")(chat_controller.query),
        methods=['POST'],
    )
    chat_bp.add_url_rule(
        '/chat-history', 'get_chat_history',
        login_required(chat_controller.get_chat_history),
        methods=['GET'],
    )

    return chat_bp
