"""Staff accounts for the USIUBOT dashboard (collection ``staff``).

There is no public staff registration: accounts are created by a Super Administrator
(dashboard Staff tab, or ``python -m tools.create_staff`` for the first account).

* Passwords are hashed with bcrypt; plaintext is never stored or logged.
* A new account, or one whose password was reset, gets a temporary password and must
  choose its own before using the dashboard (``must_change_password``).
* Repeated failed sign-ins lock the account for a while (``STAFF_MAX_FAILED_LOGINS``,
  ``STAFF_LOCKOUT_MINUTES``).
* Deactivating an account or resetting its password ends its existing sessions
  (``token_version``). Accounts are never deleted, so histories and audit entries keep
  pointing at a real person.
"""

import datetime
import hmac
import re
import secrets

import bcrypt
from pymongo.errors import DuplicateKeyError

from models.models import to_object_id
from services.sources import DEPARTMENT_LABELS, DEPARTMENTS
from utils.auth import (ROLE_DEPARTMENT_ADMIN, ROLE_DEPARTMENT_STAFF, ROLE_LABELS, ROLE_SUPER_ADMIN, STAFF_ROLES)
from utils.validation import EMAIL_RE

MIN_STAFF_PASSWORD = 10
MAX_PASSWORD_BYTES = 72
MAX_NAME = 100
SCOPES = ("department", "assigned")
SCOPE_LABELS = {"department": "All enquiries of their departments", "assigned": "Only enquiries assigned to them"}


class StaffError(ValueError):
    """Invalid staff data. Messages are safe to show to administrators."""


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def _aware(value):
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=datetime.timezone.utc)
    return value


def hash_password(password, rounds=12):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=max(4, min(int(rounds), 16)))).decode("utf-8")


def check_password(password, password_hash):
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def validate_staff_password(password):
    if not isinstance(password, str):
        raise StaffError("Password is required")
    if len(password) < MIN_STAFF_PASSWORD:
        raise StaffError(f"Password must be at least {MIN_STAFF_PASSWORD} characters")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise StaffError("Password is too long")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"[0-9]", password):
        raise StaffError("Password must contain letters and numbers")
    return password


def temporary_password():
    # Always satisfies validate_staff_password (letters and digits guaranteed).
    return secrets.token_urlsafe(10) + secrets.choice("ABCDEFGHJKMNPQRSTUVWXYZ") + str(secrets.randbelow(10))


def public_staff(doc):
    """Staff record as shown in the dashboard (no password hash, no lockout internals)."""
    return {
        "id": str(doc["_id"]),
        "email": doc.get("email", ""),
        "name": doc.get("name", ""),
        "role": doc.get("role"),
        "role_label": ROLE_LABELS.get(doc.get("role"), doc.get("role")),
        "departments": list(doc.get("departments") or []),
        "department_labels": [DEPARTMENT_LABELS.get(d, d) for d in doc.get("departments") or []],
        "scope": doc.get("scope") or "department",
        "active": bool(doc.get("active")),
        "must_change_password": bool(doc.get("must_change_password")),
        "locked": bool(doc.get("locked_until") and _aware(doc["locked_until"]) > utcnow()),
        "created_at": doc["created_at"].isoformat() if doc.get("created_at") else None,
        "created_by": doc.get("created_by"),
        "updated_at": doc["updated_at"].isoformat() if doc.get("updated_at") else None,
        "last_login_at": doc["last_login_at"].isoformat() if doc.get("last_login_at") else None,
    }


class StaffService:
    def __init__(self, db_getter, settings):
        self._db = db_getter
        self.settings = settings
        self.rounds = settings.get("STAFF_BCRYPT_ROUNDS", 12)
        self._dummy_hash = hash_password("timing-equaliser-0", self.rounds)

    @property
    def col(self):
        return self._db("staff")

    # --- validation ----------------------------------------------------------------------
    def _clean(self, data, partial=False):
        if not isinstance(data, dict):
            raise StaffError("Expected a JSON object")
        fields = {}
        if not partial or "email" in data:
            email = data.get("email")
            if not isinstance(email, str) or len(email) > 254 or not EMAIL_RE.match(email.strip()):
                raise StaffError("A valid email address is required")
            fields["email"] = email.strip().lower()
        if not partial or "name" in data:
            name = data.get("name")
            if not isinstance(name, str) or not name.strip() or len(name.strip()) > MAX_NAME:
                raise StaffError(f"Name is required (at most {MAX_NAME} characters)")
            fields["name"] = " ".join(name.split())
        if not partial or "role" in data:
            if data.get("role") not in STAFF_ROLES:
                raise StaffError("Role must be one of: " + ", ".join(ROLE_LABELS.values()))
            fields["role"] = data["role"]
        if not partial or "departments" in data:
            departments = data.get("departments") or []
            if isinstance(departments, str):
                departments = [departments]
            if not isinstance(departments, list) or any(d not in DEPARTMENTS for d in departments):
                raise StaffError("Unknown department")
            fields["departments"] = [d for d in DEPARTMENTS if d in departments]
        if "scope" in data or not partial:
            scope = data.get("scope") or "department"
            if scope not in SCOPES:
                raise StaffError("Scope must be 'department' or 'assigned'")
            fields["scope"] = scope
        if "active" in data:
            if not isinstance(data["active"], bool):
                raise StaffError("active must be true or false")
            fields["active"] = data["active"]
        return fields

    @staticmethod
    def _check_role_departments(role, departments):
        if role in (ROLE_DEPARTMENT_ADMIN, ROLE_DEPARTMENT_STAFF) and not departments:
            raise StaffError("Choose at least one department for this role")

    # --- accounts ------------------------------------------------------------------------
    def get(self, staff_id):
        oid = to_object_id(staff_id)
        return self.col.find_one({"_id": oid}) if oid else None

    def find_by_email(self, email):
        return self.col.find_one({"email": (email or "").strip().lower()})

    def list(self, departments=None, active=None, search=None):
        query = {}
        if departments is not None:
            query["departments"] = {"$in": list(departments)}
        if active is not None:
            query["active"] = active
        docs = list(self.col.find(query).sort([("name", 1)]).limit(1000))
        if search:
            needle = search.strip().lower()
            docs = [d for d in docs if needle in d.get("name", "").lower() or needle in d.get("email", "")]
        return docs

    def create(self, data, actor="admin", password=None):
        """Create an account. Returns ``(doc, temporary_password)``; the password is shown once."""
        fields = self._clean(data)
        self._check_role_departments(fields["role"], fields["departments"])
        bootstrap = (self.settings.get("ADMIN_EMAIL") or "").strip().lower()
        if bootstrap and fields["email"] == bootstrap:
            raise StaffError("That email is used by the bootstrap administrator in backend/.env")
        if self.find_by_email(fields["email"]):
            raise StaffError("A staff account with that email already exists")
        temp = password or temporary_password()
        validate_staff_password(temp)
        now = utcnow()
        doc = {**fields, "active": fields.get("active", True), "password": hash_password(temp, self.rounds),
               "must_change_password": password is None or bool(data.get("must_change_password", True)),
               "token_version": 0, "failed_logins": 0, "locked_until": None,
               "created_at": now, "created_by": actor, "updated_at": now, "updated_by": actor}
        try:
            doc["_id"] = self.col.insert_one(doc).inserted_id
        except DuplicateKeyError:
            raise StaffError("A staff account with that email already exists") from None
        return doc, temp

    def update(self, staff_id, data, actor_profile):
        doc = self.get(staff_id)
        if not doc:
            return None
        fields = self._clean(data, partial=True)
        if fields.get("email") == doc.get("email"):
            fields.pop("email")
        if "email" in fields and self.col.find_one({"email": fields["email"], "_id": {"$ne": doc["_id"]}}):
            raise StaffError("A staff account with that email already exists")
        role = fields.get("role", doc.get("role"))
        departments = fields.get("departments", doc.get("departments") or [])
        self._check_role_departments(role, departments)
        if str(doc["_id"]) == actor_profile.get("id"):
            if fields.get("active") is False:
                raise StaffError("You cannot deactivate your own account")
            if role != doc.get("role"):
                raise StaffError("You cannot change your own role")
        if doc.get("role") == ROLE_SUPER_ADMIN and (role != ROLE_SUPER_ADMIN or fields.get("active") is False):
            others = self.col.count_documents({"role": ROLE_SUPER_ADMIN, "active": True, "_id": {"$ne": doc["_id"]}})
            if others == 0 and not self.settings.get("ADMIN_EMAIL"):
                raise StaffError("At least one active Super Administrator must remain")
        if not fields:
            raise StaffError("Nothing to update")
        update = {"$set": {**fields, "updated_at": utcnow(), "updated_by": actor_profile.get("email") or "admin"}}
        if fields.get("active") is False and doc.get("active"):
            update["$inc"] = {"token_version": 1}  # end existing sessions
        self.col.update_one({"_id": doc["_id"]}, update)
        return self.get(staff_id)

    def reset_password(self, staff_id, actor="admin"):
        """New temporary password (returned once); ends the account's sessions and unlocks it."""
        doc = self.get(staff_id)
        if not doc:
            return None, None
        temp = temporary_password()
        self.col.update_one({"_id": doc["_id"]}, {
            "$set": {"password": hash_password(temp, self.rounds), "must_change_password": True, "failed_logins": 0,
                     "locked_until": None, "updated_at": utcnow(), "updated_by": actor},
            "$inc": {"token_version": 1}})
        return self.get(staff_id), temp

    def change_password(self, staff_id, current_password, new_password):
        doc = self.get(staff_id)
        if not doc or not check_password(current_password or "", doc.get("password", "")):
            raise StaffError("Your current password is not correct")
        validate_staff_password(new_password)
        if hmac.compare_digest(current_password.encode("utf-8"), new_password.encode("utf-8")):
            raise StaffError("Choose a password different from the current one")
        self.col.update_one({"_id": doc["_id"]}, {"$set": {
            "password": hash_password(new_password, self.rounds), "must_change_password": False,
            "password_changed_at": utcnow(), "updated_at": utcnow()}})
        return self.get(staff_id)

    # --- sign-in -------------------------------------------------------------------------
    def authenticate(self, email, password):
        """Return ``(doc, error)``. Error messages never say whether the email exists."""
        doc = self.find_by_email(email)
        ok = check_password(password, doc.get("password", "") if doc else self._dummy_hash)
        if not doc:
            return None, "invalid"
        now = utcnow()
        if doc.get("locked_until") and _aware(doc["locked_until"]) > now:
            return None, "locked"
        if not ok:
            failures = int(doc.get("failed_logins", 0)) + 1
            changes = {"failed_logins": failures}
            if failures >= self.settings.get("STAFF_MAX_FAILED_LOGINS", 5):
                changes.update({"failed_logins": 0, "locked_until": now + datetime.timedelta(
                    minutes=self.settings.get("STAFF_LOCKOUT_MINUTES", 15))})
            self.col.update_one({"_id": doc["_id"]}, {"$set": changes})
            return None, "invalid"
        if not doc.get("active"):
            return None, "inactive"
        self.col.update_one({"_id": doc["_id"]}, {"$set": {"failed_logins": 0, "locked_until": None,
                                                           "last_login_at": now}})
        return doc, None

    def directory(self, departments=None):
        """Active staff who can be assigned enquiries (optionally of given departments)."""
        query = {"active": True}
        if departments is not None:
            query["departments"] = {"$in": list(departments)}
        return [{"id": str(d["_id"]), "name": d.get("name", ""), "email": d.get("email", ""), "role": d.get("role"),
                 "departments": d.get("departments") or []}
                for d in self.col.find(query).sort([("name", 1)]).limit(1000)]
