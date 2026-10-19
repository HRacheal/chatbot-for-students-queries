from flask import Blueprint
from controllers.chat_controller import ChatController

def create_chat_routes(vectorstore):
    """Create chat routes"""
    chat_bp = Blueprint('chat', __name__, url_prefix='/api')
    chat_controller = ChatController(vectorstore)
    
    # Chat routes
    chat_bp.add_url_rule('/query', 'query', chat_controller.query, methods=['POST'])
    chat_bp.add_url_rule('/chat-history', 'get_chat_history', chat_controller.get_chat_history, methods=['GET'])
    chat_bp.add_url_rule('/add-response', 'add_response', chat_controller.add_response, methods=['POST'])
    
    return chat_bp
