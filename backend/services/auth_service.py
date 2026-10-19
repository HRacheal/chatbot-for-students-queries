from flask_bcrypt import Bcrypt
from models.models import User
from utils.auth import generate_user_token
from config.config import Config

class AuthService:
    """Service for handling authentication operations"""
    
    def __init__(self, app):
        self.bcrypt = Bcrypt(app)
        self.user_model = User()
    
    def register_user(self, username, email, password):
        """Register a new user"""
        try:
            # Check if user already exists
            if self.user_model.find_by_email(email):
                return {"error": "User already exists"}, 409
            
            # Hash password
            hashed_password = self.bcrypt.generate_password_hash(password).decode("utf-8")
            
            # Create user
            user_id = self.user_model.create_user(username, email, hashed_password)

            # Send email notification if user exists
            if user_id:
                try:
                    from flask import current_app
                    email_service = current_app.config.get('EMAIL_SERVICE')
                    if email_service:
                        email_service.send_welcome_email(email, username)
                        print("Email sent successfully")
                    else:
                        print("Email service not found in app config")
                except Exception as e:
                    print(f"Error sending email: {str(e)}")
            
            return {"message": "User registered successfully", "user_id": str(user_id)}, 201
            
        except Exception as e:
            return {"error": f"Registration failed: {str(e)}"}, 500
    
    def login_user(self, username, password):
        """Authenticate user login"""
        try:
            user = self.user_model.find_by_username(username)
            
            if user and self.bcrypt.check_password_hash(user["password"], password):
                token = generate_user_token(user["_id"])
                return {"token": token, "user_id": str(user["_id"])}, 200
            
            return {"error": "Invalid credentials"}, 401
            
        except Exception as e:
            return {"error": f"Login failed: {str(e)}"}, 500
    
    def login_admin(self, email, password):
        """Authenticate admin login"""
        try:
            if email == Config.ADMIN_EMAIL and password == Config.ADMIN_PASSWORD:
                from utils.auth import generate_admin_token
                token = generate_admin_token()
                return {"token": token}, 200
            
            return {"error": "Invalid credentials"}, 401
            
        except Exception as e:
            return {"error": f"Admin login failed: {str(e)}"}, 500
