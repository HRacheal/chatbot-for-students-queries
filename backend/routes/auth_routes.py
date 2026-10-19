from flask import Blueprint
from controllers.auth_controller import AuthController

def create_auth_routes(app):
    """Create authentication routes"""
    auth_bp = Blueprint('auth', __name__, url_prefix='/api')
    auth_controller = AuthController(app)
    
    # User authentication routes
    auth_bp.add_url_rule('/signup', 'signup', auth_controller.signup, methods=['POST'])
    auth_bp.add_url_rule('/login', 'login', auth_controller.login, methods=['POST'])
    
    # Admin authentication routes
    auth_bp.add_url_rule('/admin/login', 'admin_login', auth_controller.admin_login, methods=['POST'])
    
    return auth_bp
