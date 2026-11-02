"""System activity / audit log (collection ``audit_log``), visible to Super Administrators.

Records who did what and when: staff sign-ins (successful and failed), sign-outs, account
changes, enquiry updates, source reviews, routing changes and dataset imports. Entries
never contain passwords, tokens, enquirers' contact details or answer text; ``details``
holds short, non-personal facts such as the new status or department.
"""

import datetime
import logging
import re

from flask import has_request_context, request

logger = logging.getLogger(__name__)

MAX_DETAIL = 300
FORBIDDEN_KEYS = {"password", "token", "tracking_key", "contact", "email_body", "staff_response", "text"}


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def _safe_details(details):
    clean = {}
    for key, value in (details or {}).items():
        if key in FORBIDDEN_KEYS:
            continue
        if isinstance(value, (list, tuple)):
            value = [str(v)[:MAX_DETAIL] for v in value][:20]
        elif value is not None and not isinstance(value, (bool, int, float)):
            value = str(value)[:MAX_DETAIL]
        clean[key] = value
    return clean


class AuditLog:
    def __init__(self, db_getter):
        self._db = db_getter

    @property
    def col(self):
        return self._db("audit_log")

    def record(self, action, actor=None, target_type=None, target_id=None, details=None, outcome="ok"):
        """Write one entry. Failures are logged and never break the request."""
        actor = actor or {}
        entry = {
            "at": utcnow(),
            "action": action,
            "outcome": outcome,
            "actor_id": actor.get("id"),
            "actor_email": actor.get("email"),
            "actor_role": actor.get("role"),
            "target_type": target_type,
            "target_id": str(target_id) if target_id is not None else None,
            "details": _safe_details(details),
            "ip": request.remote_addr if has_request_context() else None,
        }
        try:
            self.col.insert_one(entry)
        except Exception as e:  # noqa: BLE001 - auditing must not break the action itself
            logger.warning("Audit entry %s not written (%s)", action, type(e).__name__)

    def list(self, action=None, actor=None, target_type=None, limit=200, skip=0):
        query = {}
        if action:
            query["action"] = {"$regex": "^" + re.escape(action)}
        if actor:
            query["actor_email"] = {"$regex": re.escape(actor.strip().lower())}
        if target_type:
            query["target_type"] = target_type
        total = self.col.count_documents(query)
        docs = self.col.find(query).sort([("at", -1)]).skip(max(0, skip)).limit(max(1, min(limit, 500)))
        return total, [{
            "id": str(d["_id"]), "at": d["at"].isoformat() if d.get("at") else None, "action": d.get("action"),
            "outcome": d.get("outcome"), "actor_email": d.get("actor_email"), "actor_role": d.get("actor_role"),
            "target_type": d.get("target_type"), "target_id": d.get("target_id"), "details": d.get("details") or {},
            "ip": d.get("ip"),
        } for d in docs]
