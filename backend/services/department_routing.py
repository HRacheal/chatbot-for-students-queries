"""Administrator-configurable department routing (collection ``department_routing``).

Per department an administrator can set:

* ``delivery_emails`` – staff addresses notified of new enquiries. Never filled automatically;
  when empty, the ``ENQUIRY_EMAIL_<DEPARTMENT>`` setting is used, and when that is empty the
  enquiry is only visible in the admin dashboard.
* ``public_contacts`` – contact details printed by USIU-Africa (imported from the dataset as
  *unverified*, or entered by an administrator). They are shown to students only after an
  administrator ticks ``publish_contacts`` for that department, i.e. after the university has
  confirmed them.
* ``notes`` – e.g. what the department handles, or what is still awaiting confirmation.

Nothing here invents addresses or numbers: imported contacts are copied as printed, with their
source and any conflict/warning ids.
"""

import csv
import datetime
from pathlib import Path

from services.sources import DEPARTMENT_LABELS, DEPARTMENTS
from utils.validation import EMAIL_RE

CONTACT_TYPES = ("email", "telephone", "whatsapp", "location", "website", "other")
MAX_CONTACTS = 40
MAX_VALUE = 200
MAX_NOTES = 2000
CONTACTS_FILE = "06_department_contacts_and_query_routing/official/web_department_contacts.csv"


class RoutingError(ValueError):
    """Invalid routing data. Messages are safe to show to admins."""


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def _clean(value, name, limit, required=False):
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise RoutingError(f"{name} must be text")
    value = value.strip()
    if required and not value:
        raise RoutingError(f"{name} is required")
    if len(value) > limit:
        raise RoutingError(f"{name} must be at most {limit} characters")
    return value


class DepartmentRouting:
    def __init__(self, db_getter, settings):
        self._db = db_getter
        self.settings = settings

    @property
    def col(self):
        return self._db("department_routing")

    def _doc(self, department):
        return self.col.find_one({"department": department}) or {}

    def get(self, department):
        if department not in DEPARTMENTS:
            raise RoutingError("Unknown department")
        doc = self._doc(department)
        env = self.settings.get(f"ENQUIRY_EMAIL_{department.upper()}") or ""
        return {
            "department": department,
            "label": DEPARTMENT_LABELS[department],
            "delivery_emails": doc.get("delivery_emails", []),
            "env_delivery_configured": bool([e for e in env.split(",") if EMAIL_RE.match(e.strip())]),
            "public_contacts": doc.get("public_contacts", []),
            "publish_contacts": bool(doc.get("publish_contacts")),
            "notes": doc.get("notes", ""),
            "updated_at": doc.get("updated_at").isoformat() if doc.get("updated_at") else None,
            "updated_by": doc.get("updated_by"),
        }

    def all(self):
        return [self.get(d) for d in DEPARTMENTS]

    def delivery_emails(self, department):
        """Configured staff addresses (admin setting first, then the environment). Validated."""
        emails = self._doc(department).get("delivery_emails") or []
        if not emails:
            value = self.settings.get(f"ENQUIRY_EMAIL_{department.upper()}") or ""
            emails = [e.strip() for e in value.split(",")]
        return [e for e in emails if EMAIL_RE.match(e)]

    def staff_review_available(self, department):
        """Whether anyone will see an unanswered question or enquiry for ``department``: an active
        Super Administrator or staff member of that department, a configured administrator login, or a
        delivery address for the department. Read-only."""
        if self.settings.get("ADMIN_EMAIL") and self.settings.get("ADMIN_PASSWORD"):
            return True
        who = [{"role": "super_admin"}]
        if department:
            who.append({"departments": department})
        if self._db("staff").count_documents({"active": True, "$or": who}, limit=1):
            return True
        return bool(department and department in DEPARTMENTS and self.delivery_emails(department))

    def published_contacts(self, department):
        """Contacts students may see: only when an administrator has published them."""
        doc = self._doc(department)
        if not doc.get("publish_contacts"):
            return []
        return [{k: c.get(k) for k in ("type", "value", "office", "source_url")}
                for c in doc.get("public_contacts", []) if c.get("value")]

    def update(self, department, data, actor="admin"):
        if department not in DEPARTMENTS:
            raise RoutingError("Unknown department")
        if not isinstance(data, dict):
            raise RoutingError("Expected a JSON object")
        fields = {}
        if "delivery_emails" in data:
            emails = data["delivery_emails"]
            if isinstance(emails, str):
                emails = [e for e in emails.replace(";", ",").split(",")]
            if not isinstance(emails, list) or len(emails) > 10:
                raise RoutingError("Delivery emails must be a list of at most 10 addresses")
            cleaned = []
            for e in emails:
                e = _clean(e, "Email", 254)
                if not e:
                    continue
                if not EMAIL_RE.match(e):
                    raise RoutingError(f"Not a valid email address: {e}")
                cleaned.append(e)
            fields["delivery_emails"] = list(dict.fromkeys(cleaned))
        if "public_contacts" in data:
            contacts = data["public_contacts"]
            if not isinstance(contacts, list) or len(contacts) > MAX_CONTACTS:
                raise RoutingError(f"Contacts must be a list of at most {MAX_CONTACTS} entries")
            cleaned = []
            for c in contacts:
                if not isinstance(c, dict):
                    raise RoutingError("Each contact must be an object")
                ctype = c.get("type") if c.get("type") in CONTACT_TYPES else "other"
                cleaned.append({
                    "type": ctype,
                    "value": _clean(c.get("value"), "Contact value", MAX_VALUE, required=True),
                    "office": _clean(c.get("office"), "Office", MAX_VALUE),
                    "source": _clean(c.get("source"), "Source", MAX_VALUE) or "entered by an administrator",
                    "source_url": _clean(c.get("source_url"), "Source URL", 500),
                    "issue_ids": _clean(c.get("issue_ids"), "Issue ids", MAX_VALUE),
                    "record_id": _clean(c.get("record_id"), "Record id", 50),
                })
            fields["public_contacts"] = cleaned
        if "publish_contacts" in data:
            if not isinstance(data["publish_contacts"], bool):
                raise RoutingError("publish_contacts must be true or false")
            fields["publish_contacts"] = data["publish_contacts"]
        if "notes" in data:
            fields["notes"] = _clean(data["notes"], "Notes", MAX_NOTES)
        if not fields:
            raise RoutingError("Nothing to update")
        fields.update({"updated_at": utcnow(), "updated_by": actor})
        self.col.update_one({"department": department}, {"$set": fields, "$setOnInsert": {"department": department}},
                            upsert=True)
        return self.get(department)

    def import_dataset_contacts(self, dataset_dir, actor="dataset-import"):
        """Copy the contacts printed on official pages/PDFs into ``public_contacts`` (unpublished).

        Only fills departments that have no contacts yet, so administrator edits are never
        overwritten. Delivery emails are never touched.
        """
        path = Path(dataset_dir or "") / CONTACTS_FILE
        if not path.exists():
            raise RoutingError("The dataset contact file was not found (check DATASET_DIR)")
        by_dept = {}
        with open(path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                # The dataset's own department (e.g. finance, library) when the app has it, otherwise the
                # app department it maps to (careers, alumni, security -> general_university).
                dept = row.get("routing_department")
                if dept not in DEPARTMENTS:
                    dept = row.get("app_department") if row.get("app_department") in DEPARTMENTS else None
                if not dept or not row.get("value_as_printed"):
                    continue
                by_dept.setdefault(dept, []).append({
                    "type": row.get("contact_type") if row.get("contact_type") in CONTACT_TYPES else "other",
                    "value": row["value_as_printed"][:MAX_VALUE],
                    "office": (row.get("office_as_printed") or "")[:MAX_VALUE],
                    "source": (row.get("source_title") or "USIU-Africa")[:MAX_VALUE],
                    "source_url": (row.get("source_url") or "")[:500],
                    "issue_ids": (row.get("issue_ids") or "")[:MAX_VALUE],
                    "record_id": (row.get("record_id") or "")[:50],
                })
        filled, skipped = [], []
        for dept, contacts in by_dept.items():
            if self._doc(dept).get("public_contacts"):
                skipped.append(dept)
                continue
            self.col.update_one(
                {"department": dept},
                {"$set": {"public_contacts": contacts[:MAX_CONTACTS], "updated_at": utcnow(), "updated_by": actor},
                 "$setOnInsert": {"department": dept, "publish_contacts": False,
                                  "notes": "Contacts imported from the dataset as printed; not yet confirmed "
                                           "by the university, so not shown to students."}},
                upsert=True)
            filled.append(dept)
        return {"filled": sorted(filled), "skipped_existing": sorted(skipped),
                "contacts": sum(len(v) for k, v in by_dept.items() if k in filled)}
