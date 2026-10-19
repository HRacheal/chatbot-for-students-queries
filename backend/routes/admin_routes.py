from flask import Blueprint
from controllers.admin_controller import AdminController
from utils.auth import admin_required

def create_admin_routes(email_service=None):
    """Create admin routes"""
    admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')
    admin_controller = AdminController(email_service)
    
    # Admin routes with authentication required
    admin_bp.add_url_rule('/stats', 'get_stats', admin_required(admin_controller.get_stats), methods=['GET'])
    admin_bp.add_url_rule('/chat-history', 'get_chat_history', admin_required(admin_controller.get_chat_history), methods=['GET'])
    admin_bp.add_url_rule('/query-analytics', 'get_query_analytics', admin_required(admin_controller.get_query_analytics), methods=['GET'])
    
    # Unanswered queries routes
    admin_bp.add_url_rule('/unanswered-queries', 'get_unanswered_queries', admin_controller.get_unanswered_queries, methods=['GET'])
    admin_bp.add_url_rule('/delete-query/<query_id>', 'delete_query', lambda query_id: admin_controller.delete_query(query_id), methods=['DELETE'])
    
    return admin_bp

def create_legacy_admin_routes(email_service=None):
    """Create legacy admin routes for backward compatibility"""
    legacy_bp = Blueprint('legacy_admin', __name__, url_prefix='/api')
    admin_controller = AdminController(email_service)
    
    # Add debug route to test if blueprint is working
    @legacy_bp.route('/test-legacy', methods=['GET'])
    def test_legacy():
        return {"message": "Legacy routes working"}, 200
    
    # Legacy routes to match frontend expectations
    @legacy_bp.route('/unanswered-queries', methods=['GET'])
    def legacy_unanswered_queries():
        return admin_controller.get_unanswered_queries()
    
    @legacy_bp.route('/add-response', methods=['POST'])
    def legacy_add_response():
        return admin_controller.add_response()
    
    @legacy_bp.route('/delete-query/<query_id>', methods=['DELETE'])
    def legacy_delete_query(query_id):
        return admin_controller.delete_query(query_id)
    
    return legacy_bp
