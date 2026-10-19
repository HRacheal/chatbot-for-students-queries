from flask import request, jsonify
from services.auth_service import AuthService

class AuthController:
    """Controller for handling authentication endpoints"""
    
    def __init__(self, app):
        self.auth_service = AuthService(app)
    
    def signup(self):
        """Handle user signup"""
        try:
            data = request.json
            username = data.get("username")
            email = data.get("email")
            password = data.get("password")

            if not username or not email or not password:
                return jsonify({"error": "All fields are required"}), 400

            result, status_code = self.auth_service.register_user(username, email, password)
            return jsonify(result), status_code
            
        except Exception as e:
            return jsonify({"error": f"Signup failed: {str(e)}"}), 500
    
    def login(self):
        """Handle user login"""
        try:
            data = request.json
            username = data.get("username")
            password = data.get("password")
            
            if not username or not password:
                return jsonify({"error": "Username and password are required"}), 400
            
            result, status_code = self.auth_service.login_user(username, password)
            return jsonify(result), status_code
            
        except Exception as e:
            return jsonify({"error": f"Login failed: {str(e)}"}), 500
    
    def admin_login(self):
        """Handle admin login"""
        try:
            data = request.json
            email = data.get('email')
            password = data.get('password')
            
            if not email or not password:
                return jsonify({"error": "Email and password are required"}), 400
            
            result, status_code = self.auth_service.login_admin(email, password)
            return jsonify(result), status_code
            
        except Exception as e:
            return jsonify({"error": f"Admin login failed: {str(e)}"}), 500
