"""Staff sign-in, sessions, accounts and the audit log (``/api/staff/*``).

There is deliberately no public registration endpoint: only a Super Administrator can
create staff accounts. ``/api/admin/login`` (older URL) uses the same sign-in.
"""

from flask import Blueprint, current_app, g, jsonify, request

from services.sources import DEPARTMENT_LABELS
from services.staff_service import SCOPE_LABELS, StaffError, public_staff
from utils.auth import (ROLE_DEPARTMENT_ADMIN, ROLE_LABELS, ROLE_SUPER_ADMIN, bootstrap_admin_profile,
                        current_staff_from_token, generate_admin_token, revoke_token, staff_actor, staff_profile,
                        staff_required)
from utils.permissions import is_super, permissions_summary, visible_departments
from utils.rate_limit import rate_limit
from utils.validation import ValidationError, get_json_object, require_string, validate_object_id

import hmac

GENERIC_LOGIN_ERROR = "Invalid email or password"


def _me(profile):
    return {**{k: profile[k] for k in ("id", "email", "name", "role", "departments", "scope", "bootstrap",
                                       "must_change_password")},
            "role_label": ROLE_LABELS.get(profile["role"], profile["role"]),
            "department_labels": {d: DEPARTMENT_LABELS[d] for d in (visible_departments(profile) or DEPARTMENT_LABELS)},
            "permissions": permissions_summary(profile),
            "session_hours": current_app.config.get("ADMIN_TOKEN_HOURS", 8)}


def staff_login(staff_service, audit):
    """Shared sign-in for the bootstrap administrator and staff accounts."""

    def view():
        try:
            data = get_json_object()
            email = require_string(data, "email", 254, "Email").lower()
            password = require_string(data, "password", 200, "Password", strip=False)
        except ValidationError:
            return jsonify({"error": "Email and password are required"}), 400

        admin_email = (current_app.config.get("ADMIN_EMAIL") or "").strip().lower()
        admin_password = current_app.config.get("ADMIN_PASSWORD") or ""
        if admin_email and admin_password and hmac.compare_digest(email.encode(), admin_email.encode()):
            if hmac.compare_digest(password.encode("utf-8"), admin_password.encode("utf-8")):
                profile = bootstrap_admin_profile()
                audit.record("auth.login", profile, "staff", profile["id"])
                return jsonify({"token": generate_admin_token(), "staff": _me(profile)}), 200
            audit.record("auth.login", {"email": email}, "staff", None, outcome="failed")
            return jsonify({"error": GENERIC_LOGIN_ERROR}), 401

        doc, error = staff_service.authenticate(email, password)
        if error:
            audit.record("auth.login", {"email": email}, "staff", None, {"reason": error}, outcome="failed")
            if error == "locked":
                return jsonify({"error": "Too many failed attempts. This account is locked for a few minutes."}), 429
            if error == "inactive":
                return jsonify({"error": "This account has been deactivated. Contact your administrator."}), 403
            return jsonify({"error": GENERIC_LOGIN_ERROR}), 401
        profile = staff_profile(doc)
        audit.record("auth.login", profile, "staff", profile["id"])
        return jsonify({"token": generate_admin_token(doc), "staff": _me(profile)}), 200

    return view


def create_staff_routes(staff_service, audit):
    bp = Blueprint("staff", __name__, url_prefix="/api/staff")
    login_view = rate_limit("staff_login", "AUTH_RATE_LIMIT_PER_MINUTE")(staff_login(staff_service, audit))
    bp.add_url_rule("/login", "login", login_view, methods=["POST"])

    def body():
        try:
            return get_json_object()
        except ValidationError:
            return {}

    @bp.route("/logout", methods=["POST"])
    def logout():
        # Works with any valid staff token, even one that must change its password.
        profile, payload, error = current_staff_from_token()
        if error:
            return error
        revoke_token(payload)
        audit.record("auth.logout", profile, "staff", profile["id"])
        return jsonify({"message": "Signed out"}), 200

    @bp.route("/me", methods=["GET"])
    @staff_required
    def me():
        return jsonify({"staff": _me(g.staff)}), 200

    @bp.route("/password", methods=["POST"])
    @staff_required
    def change_password():
        if g.staff.get("bootstrap"):
            return jsonify({"error": "The bootstrap administrator's password is set in backend/.env"}), 400
        data = body()
        try:
            doc = staff_service.change_password(g.staff["id"], data.get("current_password"), data.get("new_password"))
        except StaffError as e:
            audit.record("staff.password_change", g.staff, "staff", g.staff["id"], outcome="failed")
            return jsonify({"error": str(e)}), 400
        audit.record("staff.password_change", g.staff, "staff", g.staff["id"])
        return jsonify({"staff": _me(staff_profile(doc)), "message": "Password changed"}), 200

    @bp.route("/options", methods=["GET"])
    @staff_required
    def options():
        return jsonify({"roles": ROLE_LABELS, "departments": DEPARTMENT_LABELS, "scopes": SCOPE_LABELS}), 200

    # --- accounts ------------------------------------------------------------------------
    @bp.route("/accounts", methods=["GET"])
    @staff_required(roles=(ROLE_SUPER_ADMIN, ROLE_DEPARTMENT_ADMIN))
    def list_accounts():
        active = request.args.get("active")
        active = None if active in (None, "", "all") else active == "true"
        search = (request.args.get("q") or "")[:100]
        docs = staff_service.list(visible_departments(g.staff), active, search)
        return jsonify({"staff": [public_staff(d) for d in docs]}), 200

    @bp.route("/accounts", methods=["POST"])
    @staff_required(roles=(ROLE_SUPER_ADMIN,))
    def create_account():
        try:
            doc, temp = staff_service.create(body(), actor=staff_actor())
        except StaffError as e:
            return jsonify({"error": str(e)}), 400
        audit.record("staff.create", g.staff, "staff", doc["_id"],
                     {"role": doc["role"], "departments": doc["departments"]})
        return jsonify({"staff": public_staff(doc), "temporary_password": temp,
                        "message": "Account created. Give the temporary password to the staff member in "
                                   "person or by a secure channel; they must change it at first sign-in."}), 201

    @bp.route("/accounts/<staff_id>", methods=["PUT"])
    @staff_required(roles=(ROLE_SUPER_ADMIN,))
    def update_account(staff_id):
        try:
            validate_object_id(staff_id, "staff id")
            before = staff_service.get(staff_id)
            doc = staff_service.update(staff_id, body(), g.staff)
        except (ValidationError, StaffError) as e:
            return jsonify({"error": str(e)}), 400
        if not doc:
            return jsonify({"error": "Staff account not found"}), 404
        changes = {k: doc.get(k) for k in ("role", "departments", "active", "scope", "name", "email")
                   if before.get(k) != doc.get(k)}
        action = "staff.deactivate" if changes.get("active") is False else (
            "staff.activate" if changes.get("active") is True else "staff.update")
        audit.record(action, g.staff, "staff", staff_id, {k: v for k, v in changes.items() if k != "email"})
        return jsonify({"staff": public_staff(doc)}), 200

    @bp.route("/accounts/<staff_id>/reset-password", methods=["POST"])
    @staff_required(roles=(ROLE_SUPER_ADMIN,))
    def reset_password(staff_id):
        try:
            validate_object_id(staff_id, "staff id")
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400
        doc, temp = staff_service.reset_password(staff_id, actor=staff_actor())
        if not doc:
            return jsonify({"error": "Staff account not found"}), 404
        audit.record("staff.password_reset", g.staff, "staff", staff_id)
        return jsonify({"staff": public_staff(doc), "temporary_password": temp,
                        "message": "Password reset. Existing sessions of this account have ended."}), 200

    @bp.route("/directory", methods=["GET"])
    @staff_required(roles=(ROLE_SUPER_ADMIN, ROLE_DEPARTMENT_ADMIN))
    def directory():
        """Active staff who can be assigned enquiries of a department."""
        department = request.args.get("department") or None
        visible = visible_departments(g.staff)
        if department and department not in DEPARTMENT_LABELS:
            return jsonify({"error": "Unknown department"}), 400
        if department and visible is not None and department not in visible:
            return jsonify({"error": "You do not have access to that department"}), 403
        departments = [department] if department else visible
        people = staff_service.directory(departments)
        if is_super(g.staff) and department:
            supers = [p for p in staff_service.directory() if p["role"] == ROLE_SUPER_ADMIN]
            people += [p for p in supers if p["id"] not in {x["id"] for x in people}]
        return jsonify({"staff": people}), 200

    # --- audit log -----------------------------------------------------------------------
    @bp.route("/audit", methods=["GET"])
    @staff_required(roles=(ROLE_SUPER_ADMIN,))
    def audit_log():
        try:
            limit = int(request.args.get("limit") or 100)
            skip = int(request.args.get("skip") or 0)
        except ValueError:
            return jsonify({"error": "limit and skip must be numbers"}), 400
        total, entries = audit.list(request.args.get("action") or None, request.args.get("actor") or None,
                                    request.args.get("target_type") or None, limit, skip)
        return jsonify({"total": total, "entries": entries}), 200

    return bp
