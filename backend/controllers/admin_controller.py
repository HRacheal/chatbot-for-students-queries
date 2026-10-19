from flask import request, jsonify
from services.admin_service import AdminService

class AdminController:
    """Controller for handling admin endpoints"""
    
    def __init__(self, email_service=None):
        self.admin_service = AdminService(email_service)
    
    def get_stats(self):
        """Get dashboard statistics"""
        try:
            result, status_code = self.admin_service.get_dashboard_stats()
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({"error": f"Failed to fetch stats: {str(e)}"}), 500
    
    def get_unanswered_queries(self):
        """Get all unanswered queries"""
        try:
           
            # Call service and get result
            result, status_code = self.admin_service.get_unanswered_queries()
            
            return jsonify(result), status_code
        except Exception as e:
            print(f"Controller error: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Failed to fetch queries: {str(e)}"}), 500
    
    def delete_query(self, query_id):
        """Delete a query"""
        try:
            result, status_code = self.admin_service.delete_query(query_id)
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({"error": f"Failed to delete query: {str(e)}"}), 500
    
    def get_chat_history(self):
        """Get all chat history for admin"""
        try:
            result, status_code = self.admin_service.get_all_chat_history()
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({"error": f"Failed to fetch chat history: {str(e)}"}), 500
    
    def get_query_analytics(self):
        """Get query analytics"""
        try:
            result, status_code = self.admin_service.get_query_analytics()
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({"error": f"Failed to generate analytics: {str(e)}"}), 500
    
    def add_response(self):
        """Add admin response to query"""
        try:
            data = request.json
            query_id = data.get("id")
            response = data.get("response")

            if not query_id or not response:
                return jsonify({"error": "Missing query ID or response"}), 400

            result, status_code = self.admin_service.add_response_to_query(query_id, response)
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({"error": f"Failed to add response: {str(e)}"}), 500
