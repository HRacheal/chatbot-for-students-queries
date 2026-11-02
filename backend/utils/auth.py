"""Authentication helpers: token creation, verification and route decorators.

This is the single source of truth for authentication. Every protected route
must use ``login_required``, ``staff_required`` or ``admin_required`` from this module.

Tokens carry a ``type`` claim ("user" or "admin") so that a user token can
never be accepted where a staff token is required, and vice versa.

Staff (``type`` "admin") tokens also carry a ``role``:

* ``super_admin`` - the whole dashboard (the bootstrap administrator configured with
  ``ADMIN_EMAIL``/``ADMIN_PASSWORD`` and staff accounts with that role; tokens issued by
  earlier versions say ``admin``),
* ``department_admin`` - their departments' enquiries, staff list and settings,
* ``department_staff`` - their departments' enquiries (or only those assigned to them).

Roles, departments and the active flag are read from the ``staff`` collection on every
request, so deactivating an account, changing its role or resetting its password takes
effect immediately (``token_version``). Each token has a ``jti``; logging out revokes it
(collection ``revoked_tokens``). The frontend never decides access on its own.
"""

import datetime
import secrets
from functools import wraps

import jwt
from flask import current_app, g, jsonify, request

JWT_ALGORITHM = "HS256"
TOKEN_TYPE_USER = "user"
TOKEN_TYPE_ADMIN = "admin"

ROLE_SUPER_ADMIN = "super_admin"
ROLE_DEPARTMENT_ADMIN = "department_admin"
ROLE_DEPARTMENT_STAFF = "department_staff"
STAFF_ROLES = (ROLE_SUPER_ADMIN, ROLE_DEPARTMENT_ADMIN, ROLE_DEPARTMENT_STAFF)
ROLE_LABELS = {ROLE_SUPER_ADMIN: "Super Administrator", ROLE_DEPARTMENT_ADMIN: "Department Administrator",
               ROLE_DEPARTMENT_STAFF: "Department Staff"}
BOOTSTRAP_ADMIN_ID = "admin"
# Endpoints a staff member may still use while a password change is required.
PASSWORD_CHANGE_ALLOWED = ("staff.me", "staff.change_password", "staff.logout")


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


def generate_admin_token(staff=None):
    """Generate a signed JWT for a staff member (``staff`` document) or the bootstrap administrator."""
    now = _now()
    payload = {
        "sub": str(staff["_id"]) if staff else BOOTSTRAP_ADMIN_ID,
        "role": staff["role"] if staff else ROLE_SUPER_ADMIN,
        "tv": int(staff.get("token_version", 0)) if staff else 0,
        "jti": secrets.token_urlsafe(16),
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


# --- staff sessions ------------------------------------------------------------------
def _collection(name):
    from config.database import db_instance

    return db_instance.get_collection(name)


def is_token_revoked(jti):
    return bool(jti) and _collection("revoked_tokens").find_one({"jti": jti}) is not None


def revoke_token(payload):
    """Revoke one staff token (logout). Kept until the token would have expired anyway."""
    if not payload or not payload.get("jti"):
        return
    expires = datetime.datetime.fromtimestamp(payload["exp"], datetime.timezone.utc)
    _collection("revoked_tokens").update_one(
        {"jti": payload["jti"]}, {"$setOnInsert": {"jti": payload["jti"], "expires_at": expires}}, upsert=True)


def bootstrap_admin_profile():
    return {"id": BOOTSTRAP_ADMIN_ID, "email": (current_app.config.get("ADMIN_EMAIL") or "").strip().lower(),
            "name": "Bootstrap administrator", "role": ROLE_SUPER_ADMIN, "departments": [],
            "scope": "department", "bootstrap": True, "must_change_password": False}


def staff_profile(doc):
    """The fields of a staff document used for authorisation (never the password hash)."""
    return {"id": str(doc["_id"]), "email": doc.get("email", ""), "name": doc.get("name", ""),
            "role": doc.get("role"), "departments": list(doc.get("departments") or []),
            "scope": doc.get("scope") or "department", "bootstrap": False,
            "must_change_password": bool(doc.get("must_change_password"))}


def current_staff_from_token():
    """Return ``(profile, payload, error_response)`` for the bearer token of a staff request."""
    token = get_bearer_token()
    if not token:
        return None, None, _unauthorised()
    payload = decode_token(token)
    if not payload:
        return None, None, _unauthorised("Invalid or expired token")
    if payload.get("type") != TOKEN_TYPE_ADMIN:
        return None, None, (jsonify({"error": "Admin access required"}), 403)
    if is_token_revoked(payload.get("jti")):
        return None, None, _unauthorised("This session has ended. Please sign in again.")
    if payload.get("sub") == BOOTSTRAP_ADMIN_ID:
        if payload.get("role") not in ("admin", ROLE_SUPER_ADMIN):
            return None, None, _unauthorised("Invalid or expired token")
        if not (current_app.config.get("ADMIN_EMAIL") and current_app.config.get("ADMIN_PASSWORD")):
            return None, None, _unauthorised("The bootstrap administrator is disabled")
        return bootstrap_admin_profile(), payload, None
    from models.models import to_object_id

    oid = to_object_id(payload.get("sub"))
    doc = _collection("staff").find_one({"_id": oid}) if oid else None
    if not doc or not doc.get("active") or doc.get("role") not in STAFF_ROLES:
        return None, None, _unauthorised("This account is not active")
    if int(doc.get("token_version", 0)) != int(payload.get("tv", -1)):
        return None, None, _unauthorised("Your session has expired. Please sign in again.")
    return staff_profile(doc), payload, None


def staff_required(f=None, roles=None):
    """Require a valid token of an *active* staff member, optionally with one of ``roles``.

    Sets ``g.staff`` (profile) and ``g.admin`` (token payload, for older code). Usable as
    ``@staff_required`` or ``staff_required(roles=(...))(view)``.
    """

    def wrap(view):
        @wraps(view)
        def decorated(*args, **kwargs):
            profile, payload, error = current_staff_from_token()
            if error:
                return error
            if profile["must_change_password"] and request.endpoint not in PASSWORD_CHANGE_ALLOWED:
                return jsonify({"error": "Please change your temporary password first",
                                "code": "password_change_required"}), 403
            if roles and profile["role"] not in roles:
                return jsonify({"error": "Admin access required" if roles == (ROLE_SUPER_ADMIN,)
                                else "You do not have permission for this action"}), 403
            g.staff = profile
            g.admin = {**payload, "email": profile["email"], "role": profile["role"]}
            return view(*args, **kwargs)

        return decorated

    return wrap(f) if f is not None else wrap


def admin_required(f):
    """Require a Super Administrator (the bootstrap administrator or an active super_admin account)."""
    return staff_required(roles=(ROLE_SUPER_ADMIN,))(f)


def staff_actor():
    """Name used in histories and audit entries for the signed-in staff member."""
    staff = getattr(g, "staff", None) or {}
    return staff.get("email") or staff.get("id") or "admin"
