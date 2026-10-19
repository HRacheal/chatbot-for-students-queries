"""Authentication helpers: token creation, verification and route decorators.

This is the single source of truth for authentication. Every protected route
must use ``login_required`` or ``admin_required`` from this module.

Tokens carry a ``type`` claim ("user" or "admin") so that a user token can
never be accepted where an admin token is required, and vice versa.
"""

import datetime
from functools import wraps

import jwt
from flask import current_app, g, jsonify, request

JWT_ALGORITHM = "HS256"
TOKEN_TYPE_USER = "user"
TOKEN_TYPE_ADMIN = "admin"


def _secret():
    return current_app.config["SECRET_KEY"]


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def generate_user_token(user_id):
    """Generate a signed JWT for a registered user."""
    now = _now()
    payload = {
        "sub": str(user_id),
        "user_id": str(user_id),
        "type": TOKEN_TYPE_USER,
        "iat": now,
        "exp": now + datetime.timedelta(hours=current_app.config["USER_TOKEN_HOURS"]),
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def generate_admin_token():
    """Generate a signed JWT for the bootstrap administrator."""
    now = _now()
    payload = {
        "sub": "admin",
        "role": "admin",
        "type": TOKEN_TYPE_ADMIN,
        "iat": now,
        "exp": now + datetime.timedelta(hours=current_app.config["ADMIN_TOKEN_HOURS"]),
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def decode_token(token):
    """Verify a token's signature, expiry and required claims.

    Returns the payload, or ``None`` if the token is missing or invalid.
    """
    if not token:
        return None
    if token.startswith("Bearer "):
        token = token[7:]
    try:
        return jwt.decode(
            token,
            _secret(),
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "iat", "type", "sub"]},
        )
    except jwt.InvalidTokenError:
        return None


def get_bearer_token():
    """Extract the token from an ``Authorization: Bearer <token>`` header."""
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def get_optional_user_id():
    """Return the user id for a valid user token, or ``None`` for anonymous requests."""
    payload = decode_token(get_bearer_token())
    if payload and payload.get("type") == TOKEN_TYPE_USER:
        return payload.get("user_id")
    return None


def _unauthorised(message="Authentication required"):
    return jsonify({"error": message}), 401


def login_required(f):
    """Require a valid *user* token. Sets ``g.user_id``."""

    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_bearer_token()
        if not token:
            return _unauthorised()
        payload = decode_token(token)
        if not payload or payload.get("type") != TOKEN_TYPE_USER or not payload.get("user_id"):
            return _unauthorised("Invalid or expired token")
        g.user_id = payload["user_id"]
        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    """Require a valid *admin* token."""

    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_bearer_token()
        if not token:
            return _unauthorised()
        payload = decode_token(token)
        if not payload:
            return _unauthorised("Invalid or expired token")
        if payload.get("type") != TOKEN_TYPE_ADMIN or payload.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        g.admin = payload
        return f(*args, **kwargs)

    return decorated
