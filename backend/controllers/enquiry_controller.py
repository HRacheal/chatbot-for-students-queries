from flask import g, jsonify, request

import datetime

from services.enquiry_service import (CONSENT_TEXT, STATUS_LABELS, STATUSES, USER_GROUPS, EnquiryError, admin_view,
                                      delivery_message, public_view)
from services.routing import ENQUIRY_DEPARTMENT_LABELS, ENQUIRY_DEPARTMENTS
from utils.auth import get_optional_user_id, staff_actor
from utils.permissions import (can_assign, can_move_department, can_view_enquiry, enquiry_scope_filter, is_super,
                               visible_departments)
from utils.validation import ValidationError, get_json_object, validate_object_id

MAX_SEARCH = 200


class EnquiryController:
    """Unresolved enquiries: submission and tracking (users) and management (staff, by role and department)."""

    def __init__(self, enquiry_service, staff_service=None, audit=None, db_getter=None):
        self.service = enquiry_service
        self.staff_service = staff_service
        self.audit = audit
        self._db = db_getter

    def _audit(self, action, enquiry, details=None):
        if self.audit is not None:
            self.audit.record(action, getattr(g, "staff", None), "enquiry", enquiry.get("reference") if enquiry else None,
                              details)

    # --- users ------------------------------------------------------------------------
    def options(self):
        return jsonify({
            "departments": ENQUIRY_DEPARTMENT_LABELS,
            "statuses": STATUS_LABELS,
            "user_groups": USER_GROUPS,
            "consent_text": CONSENT_TEXT,
        }), 200

    def submit(self):
        try:
            data = get_json_object()
            enquiry, tracking_key, created = self.service.submit(data, get_optional_user_id())
        except (ValidationError, EnquiryError) as e:
            return jsonify({"error": str(e)}), 400
        body = {"enquiry": public_view(enquiry), "created": created}
        if created:
            body["tracking_key"] = tracking_key
            body["message"] = delivery_message(enquiry)
            body["delivery"] = (enquiry.get("notification") or {}).get("status", "not_configured")
            return jsonify(body), 201
        body["message"] = (f"You already sent this question (reference {enquiry['reference']}); it is still "
                           "open, so it was not sent again.")
        return jsonify(body), 200

    def track(self):
        try:
            data = get_json_object()
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400
        enquiry = self.service.track(data.get("reference"), data.get("tracking_key"))
        if not enquiry:
            return jsonify({"error": "No enquiry matches that reference and tracking key"}), 404
        return jsonify({"enquiry": public_view(enquiry)}), 200

    def mine(self):
        return jsonify({"enquiries": [public_view(e) for e in self.service.for_user(g.user_id)]}), 200

    # --- staff ---------------------------------------------------------------------------
    def _departments(self):
        visible = visible_departments(g.staff)
        return list(ENQUIRY_DEPARTMENTS) if visible is None else [d for d in ENQUIRY_DEPARTMENTS if d in visible]

    def admin_list(self):
        department = request.args.get("department") or None
        status = request.args.get("status") or None
        search = (request.args.get("q") or "").strip() or None
        assigned = request.args.get("assigned") or None
        if department and department not in ENQUIRY_DEPARTMENTS:
            return jsonify({"error": "Unknown department"}), 400
        if department and not is_super(g.staff) and department not in g.staff["departments"]:
            return jsonify({"error": "You do not have access to that department"}), 403
        if status and status not in STATUSES + ("open", "done", "attention"):
            return jsonify({"error": "Unknown status"}), 400
        if search and len(search) > MAX_SEARCH:
            return jsonify({"error": f"Search text must be at most {MAX_SEARCH} characters"}), 400
        assigned_to_id = g.staff["id"] if assigned == "me" else assigned
        try:
            created_from = _parse_day(request.args.get("from"), "from")
            created_to = _parse_day(request.args.get("to"), "to", end_of_day=True)
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400
        scope = enquiry_scope_filter(g.staff)
        enquiries = self.service.list(department, status, created_from=created_from, created_to=created_to,
                                      scope=scope, search=search, assigned_to_id=assigned_to_id)
        departments = self._departments()
        return jsonify({
            "enquiries": [admin_view(e) for e in enquiries],
            "stats": self.service.stats(scope, departments),
            "notifications": self.service.notification_config(departments),
            "departments": {d: ENQUIRY_DEPARTMENT_LABELS[d] for d in departments},
        }), 200

    def _visible(self, enquiry_id):
        validate_object_id(enquiry_id, "enquiry id")
        enquiry = self.service.get(enquiry_id)
        # Enquiries of other departments look exactly like missing ones.
        return enquiry if enquiry and can_view_enquiry(g.staff, enquiry) else None

    def admin_get(self, enquiry_id):
        try:
            enquiry = self._visible(enquiry_id)
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400
        if not enquiry:
            return jsonify({"error": "Enquiry not found"}), 404
        return jsonify({"enquiry": admin_view(enquiry, include_history=True)}), 200

    def _assignee(self, enquiry, data):
        """Resolve ``assigned_to_id`` into a directory entry, checking permissions. ``None`` = unchanged."""
        if "assigned_to_id" not in data:
            return None
        value = data.get("assigned_to_id")
        if value in (None, ""):
            if not can_assign(g.staff, enquiry, None):
                raise PermissionError("You cannot remove the assignment of this enquiry")
            return {}
        if value == "me":
            value = g.staff["id"]
        if value == g.staff["id"] and g.staff.get("bootstrap"):
            return {"id": g.staff["id"], "name": g.staff["name"], "email": g.staff["email"]}
        doc = self.staff_service.get(value) if self.staff_service and isinstance(value, str) else None
        if not doc or not doc.get("active"):
            raise EnquiryError("Choose an active staff member")
        assignee = {"id": str(doc["_id"]), "name": doc.get("name"), "email": doc.get("email"),
                    "role": doc.get("role"), "departments": doc.get("departments") or []}
        if not can_assign(g.staff, enquiry, assignee):
            raise PermissionError("You cannot assign this enquiry to that person (they must belong to "
                                  "the enquiry's department)")
        return assignee

    def admin_update(self, enquiry_id):
        try:
            enquiry = self._visible(enquiry_id)
            if not enquiry:
                return jsonify({"error": "Enquiry not found"}), 404
            data = get_json_object()
            response = data.get("staff_response")
            if response is not None and not isinstance(response, str):
                raise ValidationError("Response must be text")
            department = data.get("department") or None
            if department and department != enquiry.get("department") and not can_move_department(g.staff, enquiry):
                raise PermissionError("Only a Super Administrator or the department's administrator can move "
                                      "an enquiry to another department")
            assigned_to = data.get("assigned_to")
            if assigned_to is not None and not (is_super(g.staff) or g.staff["role"] == "department_admin"):
                raise PermissionError("You cannot change the assignment of this enquiry")
            assignee = self._assignee(enquiry, data)
            updated = self.service.update_status(
                enquiry_id, data.get("status") or None, data.get("note") or "", response, department,
                actor=staff_actor(), assigned_to=assigned_to, resolution=data.get("resolution"), assignee=assignee,
            )
        except PermissionError as e:
            return jsonify({"error": str(e)}), 403
        except (ValidationError, EnquiryError) as e:
            return jsonify({"error": str(e)}), 400
        if not updated:
            return jsonify({"error": "Enquiry not found"}), 404
        details = {"status": updated.get("status")}
        if updated.get("department") != enquiry.get("department"):
            details["moved_to"] = updated.get("department")
        if assignee is not None:
            details["assigned_to_id"] = assignee.get("id") or "unassigned"
        if response is not None:
            details["response_recorded"] = True
        self._audit("enquiry.update", updated, details)
        still_visible = can_view_enquiry(g.staff, updated)
        return jsonify({"enquiry": admin_view(updated, include_history=True), "visible": still_visible}), 200

    def admin_add_note(self, enquiry_id):
        try:
            enquiry = self._visible(enquiry_id)
            if not enquiry:
                return jsonify({"error": "Enquiry not found"}), 404
            data = get_json_object()
            updated = self.service.add_note(enquiry_id, data.get("text"), g.staff)
        except (ValidationError, EnquiryError) as e:
            return jsonify({"error": str(e)}), 400
        self._audit("enquiry.note", updated)
        return jsonify({"enquiry": admin_view(updated, include_history=True)}), 201

    def dashboard(self):
        """Overview numbers for the signed-in staff member's departments (real database counts)."""
        try:
            days = int(request.args.get("days") or 30)
        except ValueError:
            return jsonify({"error": "days must be a number"}), 400
        days = max(7, min(days, 365))
        scope = enquiry_scope_filter(g.staff)
        departments = self._departments()
        stats = self.service.stats(scope, departments)
        unresolved_questions = 0
        unresolved_by_department = {}
        if self._db is not None:
            query = {"answered": False}
            if not is_super(g.staff):
                query["department"] = {"$in": departments}
            col = self._db("queries")
            unresolved_questions = col.count_documents(query)
            for row in col.aggregate([{"$match": query}, {"$group": {"_id": "$department", "n": {"$sum": 1}}}]):
                unresolved_by_department[row["_id"] or "unclassified"] = row["n"]
        attention = self.service.list(status="attention", scope=scope, limit=8)
        return jsonify({
            "stats": stats,
            "trend": self.service.trend(scope, days),
            "days": days,
            "unresolved_chatbot_questions": unresolved_questions,
            "unresolved_questions_by_department": unresolved_by_department,
            "assigned_to_me_open": len(self.service.list(status="open", scope=scope, assigned_to_id=g.staff["id"],
                                                         limit=1000)),
            "awaiting_attention": [admin_view(e) for e in attention],
            "departments": {d: ENQUIRY_DEPARTMENT_LABELS[d] for d in departments},
            "statuses": STATUS_LABELS,
        }), 200


def _parse_day(value, label, end_of_day=False):
    """'YYYY-MM-DD' -> UTC datetime at the start (or end) of that day; None if empty."""
    if not value:
        return None
    try:
        day = datetime.date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValidationError(f"'{label}' must be a date (YYYY-MM-DD)") from None
    moment = datetime.datetime.combine(day, datetime.time.max if end_of_day else datetime.time.min)
    return moment.replace(tzinfo=datetime.timezone.utc)
