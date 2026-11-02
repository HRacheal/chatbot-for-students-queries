from flask import Blueprint

from controllers.enquiry_controller import EnquiryController
from utils.auth import login_required, staff_required
from utils.rate_limit import rate_limit


def create_enquiry_routes(enquiry_service, staff_service=None, audit=None, db_getter=None):
    """Unresolved enquiries. Submission and tracking are rate limited; management requires a staff token,
    and every staff endpoint limits results to the caller's departments (utils/permissions.py)."""
    bp = Blueprint('enquiries', __name__, url_prefix='/api')
    controller = EnquiryController(enquiry_service, staff_service, audit, db_getter)
    limit = lambda bucket: rate_limit(bucket, "ENQUIRY_RATE_LIMIT_PER_MINUTE")  # noqa: E731

    bp.add_url_rule('/enquiries/options', 'options', controller.options, methods=['GET'])
    bp.add_url_rule('/enquiries', 'submit', limit("enquiry_submit")(controller.submit), methods=['POST'])
    bp.add_url_rule('/enquiries/track', 'track', limit("enquiry_track")(controller.track), methods=['POST'])
    bp.add_url_rule('/my-enquiries', 'mine', login_required(controller.mine), methods=['GET'])

    bp.add_url_rule('/admin/dashboard', 'dashboard', staff_required(controller.dashboard), methods=['GET'])
    bp.add_url_rule('/admin/enquiries', 'admin_list', staff_required(controller.admin_list), methods=['GET'])
    bp.add_url_rule('/admin/enquiries/<enquiry_id>', 'admin_get',
                    staff_required(controller.admin_get), methods=['GET'])
    bp.add_url_rule('/admin/enquiries/<enquiry_id>/status', 'admin_update',
                    staff_required(controller.admin_update), methods=['POST'])
    bp.add_url_rule('/admin/enquiries/<enquiry_id>/notes', 'admin_add_note',
                    staff_required(controller.admin_add_note), methods=['POST'])
    return bp
