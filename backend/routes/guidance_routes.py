from flask import Blueprint, g, jsonify

from controllers.guidance_controller import GuidanceController
from utils.auth import ROLE_DEPARTMENT_ADMIN, ROLE_SUPER_ADMIN, admin_required, staff_required
from utils.permissions import can_manage_programmes
from utils.rate_limit import rate_limit


def create_guidance_routes(guidance_service, live_retriever=None):
    """Degree guidance (rate limited) and programme-requirement management (admin token)."""
    bp = Blueprint('guidance', __name__, url_prefix='/api')
    controller = GuidanceController(guidance_service)
    limit = lambda bucket: rate_limit(bucket, "GUIDANCE_RATE_LIMIT_PER_MINUTE")  # noqa: E731

    bp.add_url_rule('/guidance/options', 'options', controller.options, methods=['GET'])
    bp.add_url_rule('/guidance/extract', 'extract', limit("guidance_extract")(controller.extract), methods=['POST'])
    bp.add_url_rule('/guidance/recommend', 'recommend', limit("guidance_recommend")(controller.recommend),
                    methods=['POST'])

    # Super Administrators, and administrators of Admissions or Academic Programmes.
    def programmes(view):
        def guarded(*args, **kwargs):
            if not can_manage_programmes(g.staff):
                return jsonify({"error": "Only Admissions or Academic Programmes administrators can manage "
                                         "programme requirements"}), 403
            return view(*args, **kwargs)

        guarded.__name__ = view.__name__
        return staff_required(roles=(ROLE_SUPER_ADMIN, ROLE_DEPARTMENT_ADMIN))(guarded)

    bp.add_url_rule('/admin/programme-requirements', 'admin_list',
                    programmes(controller.admin_list), methods=['GET'])
    bp.add_url_rule('/admin/programme-requirements', 'admin_create',
                    programmes(controller.admin_create), methods=['POST'])
    bp.add_url_rule('/admin/programme-requirements/<requirement_id>', 'admin_update',
                    programmes(controller.admin_update), methods=['PUT'])
    bp.add_url_rule('/admin/programme-requirements/<requirement_id>', 'admin_delete',
                    programmes(controller.admin_delete), methods=['DELETE'])

    @bp.route('/admin/live-retrieval', methods=['GET'])
    @admin_required
    def live_status():
        """Live retrieval settings and the most recent fetch attempt (no page text)."""
        if live_retriever is None:
            return jsonify({"enabled": False}), 200
        return jsonify(live_retriever.status()), 200

    return bp
