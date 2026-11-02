from flask import Blueprint

from controllers.source_controller import SourceController
from routes.dataset_routes import bulk_status_view
from utils.auth import admin_required


def create_source_routes(registry):
    """Admin-only management of approved knowledge sources."""
    source_bp = Blueprint('sources', __name__, url_prefix='/api/admin/sources')
    controller = SourceController(registry)

    source_bp.add_url_rule('', 'list_sources', admin_required(controller.list_sources), methods=['GET'])
    source_bp.add_url_rule('', 'create_source', admin_required(controller.create_source), methods=['POST'])
    source_bp.add_url_rule('/<source_id>', 'get_source', admin_required(controller.get_source), methods=['GET'])
    source_bp.add_url_rule(
        '/<source_id>', 'update_source', admin_required(controller.update_source), methods=['PUT']
    )
    source_bp.add_url_rule(
        '/<source_id>/status', 'set_status', admin_required(controller.set_status), methods=['POST']
    )
    source_bp.add_url_rule(
        '/bulk-status', 'bulk_status', admin_required(bulk_status_view(registry)), methods=['POST']
    )
    source_bp.add_url_rule(
        '/rebuild-index', 'rebuild_index', admin_required(controller.rebuild_index), methods=['POST']
    )
    return source_bp
