from flask import Blueprint

from controllers.auth_controller import AuthController
from utils.rate_limit import rate_limit


def create_auth_routes(app, email_service=None):
    """Create authentication routes"""
    auth_bp = Blueprint('auth', __name__, url_prefix='/api')
    auth_controller = AuthController(app, email_service)

    limit = lambda bucket: rate_limit(bucket, "AUTH_RATE_LIMIT_PER_MINUTE")  # noqa: E731

    # User authentication routes
    auth_bp.add_url_rule('/signup', 'signup', limit("signup")(auth_controller.signup), methods=['POST'])
    auth_bp.add_url_rule('/login', 'login', limit("login")(auth_controller.login), methods=['POST'])

    # Admin authentication routes
    auth_bp.add_url_rule(
        '/admin/login', 'admin_login', limit("admin_login")(auth_controller.admin_login), methods=['POST']
    )

    return auth_bp
