from flask import jsonify

from services.auth_service import AuthService
from utils.validation import (
    ValidationError,
    get_json_object,
    require_string,
    validate_email,
    validate_password,
    validate_username,
)


class AuthController:
    """Controller for handling authentication endpoints"""

    def __init__(self, app, email_service=None):
        self.auth_service = AuthService(app, email_service)

    def signup(self):
        """Handle user signup"""
        try:
            data = get_json_object()
            username = validate_username(require_string(data, "username", 30, "Username"))
            email = validate_email(require_string(data, "email", 254, "Email"))
            password = validate_password(
                require_string(data, "password", 200, "Password", strip=False)
            )
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400

        result, status_code = self.auth_service.register_user(username, email, password)
        return jsonify(result), status_code

    def login(self):
        """Handle user login"""
        try:
            data = get_json_object()
            username = require_string(data, "username", 100, "Username")
            password = require_string(data, "password", 200, "Password", strip=False)
        except ValidationError:
            return jsonify({"error": "Username and password are required"}), 400

        result, status_code = self.auth_service.login_user(username, password)
        return jsonify(result), status_code

    def admin_login(self):
        """Handle admin login"""
        try:
            data = get_json_object()
            email = require_string(data, "email", 254, "Email")
            password = require_string(data, "password", 200, "Password", strip=False)
        except ValidationError:
            return jsonify({"error": "Email and password are required"}), 400

        result, status_code = self.auth_service.login_admin(email, password)
        return jsonify(result), status_code
