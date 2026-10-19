from flask import Blueprint

from controllers.admin_controller import AdminController
from utils.auth import admin_required


def create_admin_routes(admin_controller):
    """Create admin routes. Every route requires an admin token."""
    admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

    admin_bp.add_url_rule('/stats', 'get_stats', admin_required(admin_controller.get_stats), methods=['GET'])
    admin_bp.add_url_rule(
        '/chat-history', 'get_chat_history', admin_required(admin_controller.get_chat_history), methods=['GET']
    )
    admin_bp.add_url_rule(
        '/query-analytics', 'get_query_analytics',
        admin_required(admin_controller.get_query_analytics), methods=['GET'],
    )
    admin_bp.add_url_rule(
        '/unanswered-queries', 'get_unanswered_queries',
        admin_required(admin_controller.get_unanswered_queries), methods=['GET'],
    )
    admin_bp.add_url_rule(
        '/delete-query/<query_id>', 'delete_query',
        admin_required(admin_controller.delete_query), methods=['DELETE'],
    )
    admin_bp.add_url_rule(
        '/add-response', 'add_response', admin_required(admin_controller.add_response), methods=['POST']
    )

    return admin_bp


def create_legacy_admin_routes(admin_controller):
    """Older URLs still used by the frontend. Every route requires an admin token."""
    legacy_bp = Blueprint('legacy_admin', __name__, url_prefix='/api')

    legacy_bp.add_url_rule(
        '/unanswered-queries', 'legacy_unanswered_queries',
        admin_required(admin_controller.get_unanswered_queries), methods=['GET'],
    )
    legacy_bp.add_url_rule(
        '/add-response', 'legacy_add_response',
        admin_required(admin_controller.add_response), methods=['POST'],
    )
    legacy_bp.add_url_rule(
        '/delete-query/<query_id>', 'legacy_delete_query',
        admin_required(admin_controller.delete_query), methods=['DELETE'],
    )

    return legacy_bp


__all__ = ["AdminController", "create_admin_routes", "create_legacy_admin_routes"]
