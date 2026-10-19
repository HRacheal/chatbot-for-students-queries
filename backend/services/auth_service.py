import hmac
import logging

from flask_bcrypt import Bcrypt
from pymongo.errors import DuplicateKeyError

from models.models import User
from utils.auth import generate_admin_token, generate_user_token

logger = logging.getLogger(__name__)


class AuthService:
    """Service for handling authentication operations"""

    def __init__(self, app, email_service=None):
        self.bcrypt = Bcrypt(app)
        self.user_model = User()
        self.email_service = email_service
        self.settings = app.config
        # Used to keep login timing similar whether or not the username exists.
        self._dummy_hash = self.bcrypt.generate_password_hash("timing-equaliser").decode("utf-8")

    def register_user(self, username, email, password):
        """Register a new user (inputs are already validated)."""
        if self.user_model.find_by_email(email) or self.user_model.find_by_username(username):
            return {"error": "An account with that username or email already exists"}, 409

        hashed_password = self.bcrypt.generate_password_hash(password).decode("utf-8")
        try:
            user_id = self.user_model.create_user(username, email, hashed_password)
        except DuplicateKeyError:
            return {"error": "An account with that username or email already exists"}, 409
        logger.info("User registered: %s", user_id)

        if self.email_service:
            self.email_service.send_welcome_email(email, username)

        return {"message": "User registered successfully", "user_id": str(user_id)}, 201

    def login_user(self, username, password):
        """Authenticate user login"""
        user = self.user_model.find_by_username(username)
        password_hash = user["password"] if user else self._dummy_hash
        password_ok = self.bcrypt.check_password_hash(password_hash, password)
        if user and password_ok:
            return {"token": generate_user_token(user["_id"]), "user_id": str(user["_id"])}, 200
        return {"error": "Invalid credentials"}, 401

    def login_admin(self, email, password):
        """Authenticate the bootstrap administrator configured in the environment."""
        admin_email = self.settings.get("ADMIN_EMAIL")
        admin_password = self.settings.get("ADMIN_PASSWORD")
        if not admin_email or not admin_password:
            logger.warning("Admin login attempted but ADMIN_EMAIL/ADMIN_PASSWORD are not configured")
            return {"error": "Invalid credentials"}, 401

        email_ok = hmac.compare_digest(
            email.strip().lower().encode("utf-8"), admin_email.strip().lower().encode("utf-8")
        )
        password_ok = hmac.compare_digest(password.encode("utf-8"), admin_password.encode("utf-8"))
        if email_ok and password_ok:
            logger.info("Admin login succeeded")
            return {"token": generate_admin_token()}, 200
        logger.warning("Admin login failed")
        return {"error": "Invalid credentials"}, 401
