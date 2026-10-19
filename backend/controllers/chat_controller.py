from flask import request, jsonify
from services.chat_service import ChatService
from models.models import ChatHistory
from utils.helpers import format_response_data
from utils.auth import decode_token

class ChatController:
    """Controller for handling chat endpoints"""
    
    def __init__(self, vectorstore):
        self.chat_service = ChatService(vectorstore)
        self.chat_history_model = ChatHistory()
    
    def query(self):
        """Handle user query"""
        try:
            data = request.json
            question = data.get("question")
            session_id = data.get("session_id")
            user_token = request.headers.get('Authorization')
            
            if not question:
                return jsonify({"error": "Question not provided"}), 400
            
            # Extract user_id from token if available
            user_id = None
            if user_token:
                # Remove 'Bearer ' prefix if present
                if user_token.startswith('Bearer '):
                    user_token = user_token[7:]
                payload = decode_token(user_token)
                if payload:
                    user_id = payload.get('user_id')
            
            result, status_code = self.chat_service.process_query(question, session_id, user_id)
            return jsonify(result), status_code
            
        except Exception as e:
            error_msg = str(e)
            # Check if this is a timeout error from the embedding service
            if "504 Deadline Exceeded" in error_msg or "Error embedding content" in error_msg:
                return jsonify({
                    "error": "The AI service is currently experiencing high demand. Please try again in a few moments.",
                    "user_friendly_error": True
                }), 503  # Service Unavailable
            return jsonify({"error": f"Query processing failed: {error_msg}"}), 500
    
    def get_chat_history(self):
        """Get user's chat history"""
        try:
            user_token = request.headers.get('Authorization')
            if not user_token:
                return jsonify({"error": "Authentication required"}), 401
            
            # Remove 'Bearer ' prefix if present
            if user_token.startswith('Bearer '):
                user_token = user_token[7:]
                
            payload = decode_token(user_token)
            if not payload:
                return jsonify({"error": "Invalid token"}), 401
            
            user_id = payload.get('user_id')
            
            # Fetch chat history for the user
            history = self.chat_history_model.get_user_history(user_id)
            formatted_history = format_response_data(history)
            
            return jsonify({"history": formatted_history}), 200
            
        except Exception as e:
            return jsonify({"error": f"Failed to fetch chat history: {str(e)}"}), 500
    
    def add_response(self):
        """Add admin response to query"""
        try:
            data = request.json
            query_id = data.get("id")
            response = data.get("response")

            if not query_id or not response:
                return jsonify({"error": "Missing query ID or response"}), 400

            result, status_code = self.chat_service.add_response_to_query(query_id, response)
            return jsonify(result), status_code
            
        except Exception as e:
            return jsonify({"error": f"Failed to add response: {str(e)}"}), 500
