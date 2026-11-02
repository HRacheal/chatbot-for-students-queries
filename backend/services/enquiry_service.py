"""Unresolved enquiries (unresolved-query agent).

When USIUBOT cannot verify an answer, the user may ask USIU staff to follow up. With
explicit consent, the minimum contact details (name, email, optional phone, and
optionally which group they belong to) are saved with the question, routed to a
department, and managed in the staff dashboard through these statuses:

    new -> pending -> in_progress -> awaiting_response -> resolved -> closed

* ``new``               just received; nobody has looked at it yet
* ``pending``           seen, waiting for the department to act
* ``in_progress``       a staff member is working on it
* ``awaiting_response`` staff are waiting for the enquirer (or another office)
* ``resolved``          answered / dealt with (a reply or resolution note is required)
* ``closed``            no further action

``new`` and ``pending`` count as "awaiting departmental attention". Statuses written by
earlier versions (``assigned``, ``answered``) are migrated at startup to ``in_progress``
and ``resolved``; nothing is deleted.

Delivery: an email is sent only when SMTP and the department's staff address are
configured (admin Routing tab or ``ENQUIRY_EMAIL_<DEPARTMENT>``). Otherwise the enquiry
is stored and shown in the dashboard, and the user is told exactly that (never "emailed").
Further notifications (assignment, staff reply, resolution, reminders) follow the same
rule and each attempt is recorded on the enquiry as sent / failed / not_configured.

Privacy and security:
* Contact details are visible only to authorised staff (see utils/permissions.py). The
  enquirer can track the status with the reference and a one-time tracking key (only a
  hash is stored) or, when logged in, from their account. Tracking never returns contact
  details or internal notes.
* Submitting the same question with the same email while an earlier enquiry is still
  open returns the existing enquiry instead of creating a duplicate.
* Contact details are never written to logs or the audit log.
"""

import datetime
import hashlib
import hmac
import logging
import re
import secrets

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from models.models import to_object_id
from services.routing import ENQUIRY_DEPARTMENT_LABELS, ENQUIRY_DEPARTMENTS, classify_department
from utils.validation import EMAIL_RE

logger = logging.getLogger(__name__)

STATUSES = ("new", "pending", "in_progress", "awaiting_response", "resolved", "closed")
OPEN_STATUSES = ("new", "pending", "in_progress", "awaiting_response")
DONE_STATUSES = ("resolved", "closed")
ATTENTION_STATUSES = ("new", "pending")
STATUS_LABELS = {"new": "New", "pending": "Pending", "in_progress": "In Progress",
                 "awaiting_response": "Awaiting Response", "resolved": "Resolved", "closed": "Closed"}
# Statuses written by earlier versions.
LEGACY_STATUSES = {"assigned": "in_progress", "answered": "resolved"}
USER_GROUPS = {
    "current_student": "Current student",
    "prospective_student": "Prospective student",
    "parent_guardian": "Parent or guardian",
    "faculty": "Faculty member",
    "staff": "University administrator or staff",
    "other": "Other",
}
MAX_ASSIGNEE = 100
CONSENT_VERSION = "2026-10-20"
CONSENT_TEXT = (
    "I agree that USIU-Africa staff may use the contact details I provide to respond to this "
    "enquiry. They are stored with my question and visible only to authorised staff."
)
PHONE_RE = re.compile(r"^\+?[0-9 ()-]{7,20}$")
REFERENCE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
DUPLICATE_WINDOW_DAYS = 14
MAX_NAME = 100
MAX_NOTE = 2000
MAX_NOTES = 200


class EnquiryError(ValueError):
    """Invalid enquiry data. The message is safe to show to users."""


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def _iso(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


def _aware(value):
    if isinstance(value, datetime.datetime) and value.tzinfo is None:
        return value.replace(tzinfo=datetime.timezone.utc)
    return value


def _normalise_question(question):
    return re.sub(r"[^a-z0-9]+", " ", question.lower()).strip()


def _hash_key(key):
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def new_reference():
    return "ENQ-" + "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(8))


def status_of(enquiry):
    return LEGACY_STATUSES.get(enquiry.get("status"), enquiry.get("status"))


def _status_query(status):
    return {"$in": [status] + [old for old, new in LEGACY_STATUSES.items() if new == status]}


def delivery_message(enquiry):
    """What the user is told about delivery. Says "emailed" only when the email was really sent."""
    label = ENQUIRY_DEPARTMENT_LABELS.get(enquiry["department"], enquiry["department"])
    if (enquiry.get("notification") or {}).get("status") == "sent":
        return f"Your enquiry {enquiry['reference']} has been recorded and emailed to {label}."
    return (f"Your enquiry {enquiry['reference']} has been recorded for {label}. Staff review it in the "
            "USIUBOT dashboard; it has not been emailed to the office.")


def public_view(enquiry):
    """What the person who submitted the enquiry may see (no contact details, no internal notes)."""
    status = status_of(enquiry)
    return {
        "reference": enquiry["reference"],
        "question": enquiry["question"],
        "department": enquiry["department"],
        "department_label": ENQUIRY_DEPARTMENT_LABELS.get(enquiry["department"], enquiry["department"]),
        "status": status,
        "status_label": STATUS_LABELS.get(status, status),
        "created_at": _iso(enquiry.get("created_at")),
        "updated_at": _iso(enquiry.get("updated_at")),
        "staff_response": enquiry.get("staff_response") or None,
    }


def admin_view(enquiry, include_history=False):
    consent = enquiry.get("consent", {})
    data = {
        **public_view(enquiry),
        "id": str(enquiry["_id"]),
        "department_source": enquiry.get("department_source"),
        "contact": dict(enquiry.get("contact", {})),
        "user_group": enquiry.get("user_group"),
        "user_group_label": USER_GROUPS.get(enquiry.get("user_group")),
        "consent": {"given": consent.get("given", False), "at": _iso(consent.get("at")),
                    "version": consent.get("version")},
        "registered_user": bool(enquiry.get("user_id")),
        "notification": {k: _iso(v) for k, v in (enquiry.get("notification") or {}).items()},
        "assigned_to": enquiry.get("assigned_to") or "",
        "assigned_to_id": enquiry.get("assigned_to_id"),
        "resolution": enquiry.get("resolution") or "",
        "resolved_at": _iso(enquiry.get("resolved_at")),
        "awaiting_attention": status_of(enquiry) in ATTENTION_STATUSES,
        "note_count": len(enquiry.get("notes") or []),
    }
    if include_history:
        data["history"] = [
            {**h, "status": LEGACY_STATUSES.get(h.get("status"), h.get("status")), "at": _iso(h.get("at"))}
            for h in enquiry.get("history", [])
        ]
        data["notes"] = [{**n, "at": _iso(n.get("at"))} for n in enquiry.get("notes") or []]
        data["notifications_log"] = [{**n, "at": _iso(n.get("at"))} for n in enquiry.get("notifications_log") or []]
    return data


class EnquiryService:
    def __init__(self, db_getter, settings, email_service=None, routing=None):
        self._db = db_getter
        self.settings = settings
        self.email_service = email_service
        # services.department_routing.DepartmentRouting: admin-configured delivery addresses.
        self.routing = routing

    @property
    def collection(self):
        return self._db("enquiries")

    def migrate_legacy_statuses(self):
        """Rename statuses written by earlier versions. Idempotent; nothing is deleted.

        ``assigned`` -> ``in_progress`` (the assignee is kept) and ``answered`` -> ``resolved``.
        """
        changed = 0
        for old, new in LEGACY_STATUSES.items():
            changed += self.collection.update_many(
                {"status": old}, {"$set": {"status": new, "status_migrated_from": old}}).modified_count
        return changed

    # --- configuration ----------------------------------------------------------------
    def department_recipients(self, department):
        if self.routing is not None:
            return self.routing.delivery_emails(department)
        value = self.settings.get(f"ENQUIRY_EMAIL_{department.upper()}") or ""
        return [r.strip() for r in value.split(",") if EMAIL_RE.match(r.strip())]

    def smtp_configured(self):
        return bool(self.email_service and self.email_service.is_configured())

    def notification_config(self, departments=None):
        departments = ENQUIRY_DEPARTMENTS if departments is None else departments
        return {
            "smtp_configured": self.smtp_configured(),
            "departments": {d: bool(self.department_recipients(d)) for d in departments},
            "notify_assignee": bool(self.settings.get("ENQUIRY_NOTIFY_ASSIGNEE", True)),
            "notify_enquirer": bool(self.settings.get("ENQUIRY_NOTIFY_ENQUIRER", True)),
        }

    # --- submission -------------------------------------------------------------------
    def _validated(self, data):
        question = data.get("question")
        if not isinstance(question, str) or not question.strip():
            raise EnquiryError("Question is required")
        question = question.strip()
        if len(question) > self.settings.get("MAX_QUESTION_LENGTH", 2000):
            raise EnquiryError("Question is too long")
        if data.get("consent") is not True:
            raise EnquiryError("Please confirm that USIU staff may use your contact details to reply")
        name = data.get("name")
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > MAX_NAME:
            raise EnquiryError(f"Name is required (at most {MAX_NAME} characters)")
        email = data.get("email")
        if not isinstance(email, str) or len(email) > 254 or not EMAIL_RE.match(email.strip()):
            raise EnquiryError("A valid email address is required")
        phone = data.get("phone") or ""
        if not isinstance(phone, str) or (phone.strip() and not PHONE_RE.match(phone.strip())):
            raise EnquiryError("Phone number is not valid")
        department = data.get("department") or None
        if department is not None and department not in ENQUIRY_DEPARTMENTS:
            raise EnquiryError("Department must be one of: " + ", ".join(ENQUIRY_DEPARTMENTS))
        user_group = data.get("user_group") or None
        if user_group is not None and user_group not in USER_GROUPS:
            raise EnquiryError("Please choose who you are from the list (or leave it empty)")
        return {
            "question": question,
            "name": " ".join(name.split()),
            "email": email.strip().lower(),
            "phone": phone.strip(),
            "department": department,
            "user_group": user_group,
        }

    def suggest_department(self, question):
        department, _ = classify_department(question)
        return department

    def submit(self, data, user_id=None):
        """Save an enquiry. Returns ``(enquiry_doc, tracking_key or None, created)``.

        ``created`` is False when an open enquiry with the same question and email
        already exists; that enquiry is returned and no new tracking key is issued.
        """
        clean = self._validated(data)
        department = clean["department"]
        department_source = "user"
        if department is None:
            department = self.suggest_department(clean["question"])
            department_source = "automatic"
            if department is None:
                raise EnquiryError("Please choose the department: " + ", ".join(ENQUIRY_DEPARTMENT_LABELS.values()))

        dedupe_key = _hash_key(_normalise_question(clean["question"]) + "|" + clean["email"])
        since = utcnow() - datetime.timedelta(days=DUPLICATE_WINDOW_DAYS)
        existing = self.collection.find_one({
            "dedupe_key": dedupe_key, "status": {"$in": list(OPEN_STATUSES) + ["assigned"]},
            "created_at": {"$gte": since},
        })
        if existing:
            return existing, None, False

        tracking_key = secrets.token_urlsafe(18)
        now = utcnow()
        doc = {
            "question": clean["question"],
            "department": department,
            "department_source": department_source,
            "status": "new",
            "contact": {"name": clean["name"], "email": clean["email"], "phone": clean["phone"]},
            "user_group": clean["user_group"],
            "consent": {"given": True, "at": now, "version": CONSENT_VERSION},
            "user_id": to_object_id(user_id),
            "query_id": to_object_id(data.get("query_id")),
            "tracking_key_hash": _hash_key(tracking_key),
            "dedupe_key": dedupe_key,
            "created_at": now,
            "updated_at": now,
            "history": [{"status": "new", "at": now, "by": "user", "note": ""}],
            "notes": [],
            "notifications_log": [],
            "notification": {"status": "pending"},
        }
        for _ in range(5):
            doc["reference"] = new_reference()
            try:
                result = self.collection.insert_one(doc)
                break
            except DuplicateKeyError:
                doc.pop("_id", None)
        else:  # pragma: no cover - 31^8 references make this practically impossible
            raise RuntimeError("Could not allocate an enquiry reference")
        doc["_id"] = result.inserted_id
        logger.info("Enquiry %s created for %s", doc["reference"], department)
        doc["notification"] = self._notify_department(doc)
        log_entry = {"event": "new_enquiry", "status": doc["notification"]["status"], "at": utcnow(),
                     "to": "department"}
        doc["notifications_log"] = [log_entry]
        self.collection.update_one({"_id": doc["_id"]}, {"$set": {"notification": doc["notification"]},
                                                         "$push": {"notifications_log": log_entry}})
        return doc, tracking_key, True

    # --- notifications ------------------------------------------------------------------
    def _send(self, recipients, subject, body):
        """Returns sent / failed / not_configured. Never claims delivery that did not happen."""
        if not recipients:
            return "not_configured"
        if not self.smtp_configured():
            return "not_configured"
        try:
            sent = all(self.email_service.send(r, subject, body) for r in recipients)
        except Exception as e:  # noqa: BLE001
            logger.warning("Notification email failed (%s)", type(e).__name__)
            sent = False
        return "sent" if sent else "failed"

    def _notify_department(self, enquiry):
        recipients = self.department_recipients(enquiry["department"])
        if not recipients:
            return {"status": "not_configured",
                    "detail": f"No staff address for {ENQUIRY_DEPARTMENT_LABELS[enquiry['department']]} "
                              f"(Routing tab or ENQUIRY_EMAIL_{enquiry['department'].upper()})"}
        if not self.smtp_configured():
            return {"status": "not_configured", "detail": "SMTP email is not configured"}
        contact = enquiry["contact"]
        body = (
            f"A new USIUBOT enquiry has been routed to {ENQUIRY_DEPARTMENT_LABELS[enquiry['department']]}.\n\n"
            f"Reference: {enquiry['reference']}\n"
            f"Question: {enquiry['question']}\n\n"
            f"Contact (consent given): {contact['name']} <{contact['email']}>"
            + (f", {contact['phone']}" if contact.get("phone") else "") + "\n\n"
            "Please manage it in the USIUBOT staff dashboard (Enquiries).\n"
        )
        status = self._send(recipients, f"USIUBOT enquiry {enquiry['reference']}", body)
        if status == "failed":
            logger.warning("Enquiry %s: department email could not be sent", enquiry["reference"])
        return {"status": status, "at": utcnow()}

    def _notify_assignee(self, enquiry, assignee):
        if not self.settings.get("ENQUIRY_NOTIFY_ASSIGNEE", True):
            return "disabled"
        email = (assignee or {}).get("email")
        body = (f"The USIUBOT enquiry {enquiry['reference']} "
                f"({ENQUIRY_DEPARTMENT_LABELS.get(enquiry['department'], enquiry['department'])}) "
                "has been assigned to you.\n\nOpen the USIUBOT staff dashboard to read and answer it.\n")
        return self._send([email] if email and EMAIL_RE.match(email) else [],
                          f"USIUBOT enquiry {enquiry['reference']} assigned to you", body)

    def _notify_enquirer(self, enquiry, event):
        if not self.settings.get("ENQUIRY_NOTIFY_ENQUIRER", True):
            return "disabled"
        email = (enquiry.get("contact") or {}).get("email")
        label = ENQUIRY_DEPARTMENT_LABELS.get(enquiry["department"], enquiry["department"])
        reply = enquiry.get("staff_response") or ""
        if event == "resolved":
            intro = f"Your USIU-Africa enquiry {enquiry['reference']} has been marked as resolved by {label}."
        else:
            intro = f"{label} has replied to your USIU-Africa enquiry {enquiry['reference']}."
        body = (f"{intro}\n\nYour question: {enquiry['question']}\n\n"
                + (f"Reply:\n{reply}\n\n" if reply else "")
                + "You can also check the status in USIUBOT with your reference and tracking key.\n")
        return self._send([email] if email else [], f"USIU-Africa enquiry {enquiry['reference']}", body)

    # --- tracking -----------------------------------------------------------------------
    def track(self, reference, tracking_key):
        if not isinstance(reference, str) or not isinstance(tracking_key, str):
            return None
        enquiry = self.collection.find_one({"reference": reference.strip().upper()})
        if not enquiry or not hmac.compare_digest(enquiry.get("tracking_key_hash", ""), _hash_key(tracking_key.strip())):
            return None
        return enquiry

    def for_user(self, user_id):
        oid = to_object_id(user_id)
        if oid is None:
            return []
        return list(self.collection.find({"user_id": oid}).sort("created_at", -1).limit(100))

    # --- administration -----------------------------------------------------------------
    @staticmethod
    def _filter(department=None, status=None, created_from=None, created_to=None, scope=None, search=None,
                assigned_to_id=None):
        clauses = [scope] if scope else []
        if department:
            clauses.append({"department": department})
        if status == "open":
            clauses.append({"status": {"$in": list(OPEN_STATUSES) + ["assigned"]}})
        elif status == "done":
            clauses.append({"status": {"$in": list(DONE_STATUSES) + ["answered"]}})
        elif status == "attention":
            clauses.append({"status": {"$in": list(ATTENTION_STATUSES)}})
        elif status:
            clauses.append({"status": _status_query(status)})
        if created_from or created_to:
            created = {}
            if created_from:
                created["$gte"] = created_from
            if created_to:
                created["$lte"] = created_to
            clauses.append({"created_at": created})
        if assigned_to_id == "unassigned":
            clauses.append({"assigned_to_id": {"$in": [None, ""]}})
        elif assigned_to_id:
            clauses.append({"assigned_to_id": assigned_to_id})
        if search:
            needle = {"$regex": re.escape(search.strip()), "$options": "i"}
            clauses.append({"$or": [{"reference": needle}, {"question": needle}, {"contact.name": needle},
                                    {"contact.email": needle}]})
        if not clauses:
            return {}
        return clauses[0] if len(clauses) == 1 else {"$and": clauses}

    def list(self, department=None, status=None, limit=200, created_from=None, created_to=None, scope=None,
             search=None, assigned_to_id=None):
        """Filter by department, status (or "open"/"done"/"attention"), creation time, search text,
        assignee, and the caller's access ``scope`` (a MongoDB filter from utils.permissions)."""
        query = self._filter(department, status, created_from, created_to, scope, search, assigned_to_id)
        return list(self.collection.find(query).sort("created_at", -1).limit(limit))

    def get(self, enquiry_id):
        oid = to_object_id(enquiry_id)
        return self.collection.find_one({"_id": oid}) if oid else None

    def update_status(self, enquiry_id, status=None, note="", staff_response=None, department=None, actor="admin",
                      assigned_to=None, resolution=None, assignee=None):
        """Change status, department, assignment, reply and/or resolution in one step.

        ``assignee``: a staff directory entry (``{"id", "name", "email"}``) to assign, ``{}`` to
        unassign, or ``None`` to leave the assignment unchanged. ``assigned_to`` (free text) is the
        older way of naming a desk and is kept for compatibility. ``status=None`` keeps the status.
        """
        existing = self.get(enquiry_id)
        if not existing:
            return None
        current = status_of(existing)
        status = status or current
        if status not in STATUSES:
            raise EnquiryError("Status must be one of: " + ", ".join(STATUS_LABELS.values()))
        if assigned_to is not None:
            if not isinstance(assigned_to, str) or len(assigned_to.strip()) > MAX_ASSIGNEE:
                raise EnquiryError(f"Assignee must be text of at most {MAX_ASSIGNEE} characters")
            assigned_to = " ".join(assigned_to.split())
        if staff_response is not None and not isinstance(staff_response, str):
            raise EnquiryError("Response must be text")
        if resolution is not None and not isinstance(resolution, str):
            raise EnquiryError("Resolution details must be text")
        response_text = (staff_response if staff_response is not None else existing.get("staff_response") or "")
        resolution_text = (resolution if resolution is not None else existing.get("resolution") or "")
        if status == "resolved" and not response_text.strip() and not resolution_text.strip():
            raise EnquiryError("Write the reply or the resolution details before marking the enquiry as resolved")
        if department is not None and department not in ENQUIRY_DEPARTMENTS:
            raise EnquiryError("Department must be one of: " + ", ".join(ENQUIRY_DEPARTMENTS))
        note = (note or "").strip()
        max_response = self.settings.get("MAX_RESPONSE_LENGTH", 5000)
        if len(note) > MAX_NOTE or len(response_text) > max_response or len(resolution_text) > max_response:
            raise EnquiryError("Note, response or resolution is too long")

        now = utcnow()
        changes = {"status": status, "updated_at": now}
        if status in DONE_STATUSES and current not in DONE_STATUSES:
            changes["resolved_at"] = now
        if assignee is not None:
            changes["assigned_to_id"] = assignee.get("id") or None
            changes["assigned_to"] = assignee.get("name") or assignee.get("email") or ""
        elif assigned_to is not None:
            changes["assigned_to"] = assigned_to
        response_changed = staff_response is not None and staff_response.strip() != (existing.get("staff_response") or "")
        if staff_response is not None:
            changes["staff_response"] = staff_response.strip()
            if response_changed:
                changes["responded_at"] = now
                changes["responded_by"] = actor
        if resolution is not None:
            changes["resolution"] = resolution.strip()
        if department is not None and department != existing.get("department"):
            changes["department"] = department
            changes["department_source"] = "staff"
        entry = {"status": status, "at": now, "by": actor, "note": note}
        if "department" in changes:
            entry["department"] = department
        if changes.get("assigned_to"):
            entry["assigned_to"] = changes["assigned_to"]
        if response_changed:
            entry["responded"] = True
        updated = self.collection.find_one_and_update(
            {"_id": existing["_id"]}, {"$set": changes, "$push": {"history": entry}},
            return_document=ReturnDocument.AFTER)

        # Notifications (recorded on the enquiry; never claimed unless really sent).
        events = []
        if assignee and assignee.get("id") and assignee.get("id") != existing.get("assigned_to_id"):
            events.append({"event": "assigned", "status": self._notify_assignee(updated, assignee), "to": "assignee"})
        if status == "resolved" and current != "resolved":
            events.append({"event": "resolved", "status": self._notify_enquirer(updated, "resolved"), "to": "enquirer"})
        elif response_changed and updated.get("staff_response"):
            events.append({"event": "staff_response", "status": self._notify_enquirer(updated, "staff_response"),
                           "to": "enquirer"})
        if events:
            for e in events:
                e["at"] = utcnow()
            updated = self.collection.find_one_and_update(
                {"_id": existing["_id"]}, {"$push": {"notifications_log": {"$each": events}}},
                return_document=ReturnDocument.AFTER)
        return updated

    def add_note(self, enquiry_id, text, actor_profile):
        """Internal note visible only to staff who can see the enquiry."""
        if not isinstance(text, str) or not text.strip():
            raise EnquiryError("Write the note first")
        if len(text.strip()) > MAX_NOTE:
            raise EnquiryError(f"A note can be at most {MAX_NOTE} characters")
        existing = self.get(enquiry_id)
        if not existing:
            return None
        if len(existing.get("notes") or []) >= MAX_NOTES:
            raise EnquiryError("This enquiry has reached the maximum number of notes")
        note = {"id": str(ObjectId()), "at": utcnow(), "by_id": actor_profile.get("id"),
                "by": actor_profile.get("name") or actor_profile.get("email") or "staff", "text": text.strip()}
        return self.collection.find_one_and_update(
            {"_id": existing["_id"]}, {"$push": {"notes": note}, "$set": {"updated_at": utcnow()}},
            return_document=ReturnDocument.AFTER)

    # --- statistics ---------------------------------------------------------------------
    def stats(self, scope=None, departments=None):
        """Counts by department and status, limited to ``scope`` (and the listed departments)."""
        departments = list(departments) if departments is not None else list(ENQUIRY_DEPARTMENTS)
        counts = {d: {s: 0 for s in STATUSES} for d in departments}
        by_status = {s: 0 for s in STATUSES}
        pipeline = ([{"$match": scope}] if scope else []) + [
            {"$group": {"_id": {"d": "$department", "s": "$status"}, "n": {"$sum": 1}}}]
        total = 0
        for row in self.collection.aggregate(pipeline):
            d, s = row["_id"].get("d"), LEGACY_STATUSES.get(row["_id"].get("s"), row["_id"].get("s"))
            if s in by_status:
                by_status[s] += row["n"]
                total += row["n"]
            if d in counts and s in counts[d]:
                counts[d][s] += row["n"]
        return {
            "total": total,
            "unresolved": sum(by_status[s] for s in OPEN_STATUSES),
            "awaiting_attention": sum(by_status[s] for s in ATTENTION_STATUSES),
            "by_status": by_status,
            "by_department": counts,
        }

    def trend(self, scope=None, days=30):
        """Enquiries received and resolved per day (UTC) for the last ``days`` days."""
        days = max(1, min(int(days), 366))
        today = utcnow().date()
        start_day = today - datetime.timedelta(days=days - 1)
        start = datetime.datetime.combine(start_day, datetime.time.min, tzinfo=datetime.timezone.utc)
        series = {start_day + datetime.timedelta(days=i): {"received": 0, "resolved": 0} for i in range(days)}
        received_q = {"created_at": {"$gte": start}}
        resolved_q = {"resolved_at": {"$gte": start}}
        if scope:
            received_q = {"$and": [scope, received_q]}
            resolved_q = {"$and": [scope, resolved_q]}
        for doc in self.collection.find(received_q, {"created_at": 1}):
            day = _aware(doc["created_at"]).date()
            if day in series:
                series[day]["received"] += 1
        for doc in self.collection.find(resolved_q, {"resolved_at": 1}):
            day = _aware(doc["resolved_at"]).date()
            if day in series:
                series[day]["resolved"] += 1
        return [{"date": day.isoformat(), **values} for day, values in sorted(series.items())]

    # --- reminders ------------------------------------------------------------------------
    def overdue(self, days, scope=None):
        """Open enquiries not updated for at least ``days`` days."""
        cutoff = utcnow() - datetime.timedelta(days=days)
        query = {"status": {"$in": list(OPEN_STATUSES)}, "updated_at": {"$lte": cutoff}}
        if scope:
            query = {"$and": [scope, query]}
        return list(self.collection.find(query).sort("created_at", 1).limit(1000))

    def send_reminders(self, days):
        """Email each department a list of its overdue enquiries (when email is configured).

        Returns ``{department: {"count": n, "status": sent|failed|not_configured}}``.
        """
        by_department = {}
        for enquiry in self.overdue(days):
            by_department.setdefault(enquiry["department"], []).append(enquiry)
        report = {}
        for department, items in by_department.items():
            label = ENQUIRY_DEPARTMENT_LABELS.get(department, department)
            lines = "\n".join(f"- {e['reference']} ({STATUS_LABELS.get(status_of(e), e['status'])}, received "
                              f"{_aware(e['created_at']).date().isoformat()})" for e in items[:100])
            body = (f"{len(items)} USIUBOT enquiries for {label} have had no update for {days} days or more:\n\n"
                    f"{lines}\n\nPlease review them in the USIUBOT staff dashboard.\n")
            status = self._send(self.department_recipients(department),
                                f"USIUBOT: {len(items)} enquiries awaiting {label}", body)
            entry = {"event": "reminder", "status": status, "at": utcnow(), "to": "department"}
            self.collection.update_many({"_id": {"$in": [e["_id"] for e in items]}},
                                        {"$push": {"notifications_log": entry}})
            report[department] = {"count": len(items), "status": status}
        return report
