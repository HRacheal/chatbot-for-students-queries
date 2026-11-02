"""Role- and department-based authorisation rules for the staff dashboard.

All checks run on the server with the profile set by ``utils.auth.staff_required``
(``g.staff``). The frontend only hides what the API would refuse anyway.

* Super Administrator: every department and every enquiry.
* Department Administrator: enquiries of their departments; assigns them to staff of
  that department; may move an enquiry to another department (it then leaves their view).
* Department Staff: enquiries of their departments (scope "department") or only those
  assigned to them (scope "assigned"); may take an unassigned enquiry themselves.
  Every staff member also sees enquiries assigned to them personally.
"""

from utils.auth import ROLE_DEPARTMENT_ADMIN, ROLE_DEPARTMENT_STAFF, ROLE_SUPER_ADMIN


def is_super(staff):
    return bool(staff) and staff.get("role") == ROLE_SUPER_ADMIN


def visible_departments(staff):
    """``None`` means every department."""
    return None if is_super(staff) else list(staff.get("departments") or [])


def enquiry_scope_filter(staff):
    """MongoDB filter limiting enquiries to those the staff member may see."""
    if is_super(staff):
        return {}
    mine = {"assigned_to_id": staff["id"]}
    departments = list(staff.get("departments") or [])
    if staff.get("role") == ROLE_DEPARTMENT_STAFF and staff.get("scope") == "assigned":
        return mine
    return {"$or": [{"department": {"$in": departments}}, mine]}


def can_view_enquiry(staff, enquiry):
    if not enquiry:
        return False
    if is_super(staff) or enquiry.get("assigned_to_id") == staff.get("id"):
        return True
    if staff.get("role") == ROLE_DEPARTMENT_STAFF and staff.get("scope") == "assigned":
        return False
    return enquiry.get("department") in (staff.get("departments") or [])


def can_move_department(staff, enquiry):
    return is_super(staff) or (staff.get("role") == ROLE_DEPARTMENT_ADMIN
                               and enquiry.get("department") in (staff.get("departments") or []))


def can_assign(staff, enquiry, assignee):
    """``assignee`` is a staff profile/directory entry, or ``None`` to unassign."""
    department = enquiry.get("department")
    if assignee is None:
        return is_super(staff) or (staff.get("role") == ROLE_DEPARTMENT_ADMIN
                                   and department in (staff.get("departments") or []))
    in_department = department in (assignee.get("departments") or []) or assignee.get("role") == ROLE_SUPER_ADMIN
    if is_super(staff):
        return in_department
    if staff.get("role") == ROLE_DEPARTMENT_ADMIN:
        return department in (staff.get("departments") or []) and in_department
    # Department staff may only take an enquiry themselves.
    return assignee.get("id") == staff.get("id") and in_department


def can_manage_department_settings(staff, department):
    return is_super(staff) or (staff.get("role") == ROLE_DEPARTMENT_ADMIN
                               and department in (staff.get("departments") or []))


# Departments whose administrators may maintain verified programme requirements (degree guidance).
PROGRAMME_DEPARTMENTS = ("admissions", "academic_programmes")


def can_manage_programmes(staff):
    return is_super(staff) or (staff.get("role") == ROLE_DEPARTMENT_ADMIN
                               and bool(set(staff.get("departments") or []) & set(PROGRAMME_DEPARTMENTS)))


def permissions_summary(staff):
    """What the dashboard should offer this person (the API enforces the same rules)."""
    sup = is_super(staff)
    return {
        "view_all_departments": sup,
        "manage_staff": sup,
        "view_staff_directory": sup or staff.get("role") == ROLE_DEPARTMENT_ADMIN,
        "manage_sources": sup,
        "manage_routing": sup,
        "manage_department_settings": sup or staff.get("role") == ROLE_DEPARTMENT_ADMIN,
        "manage_programmes": can_manage_programmes(staff),
        "view_audit_log": sup,
        "view_chat_history": sup,
        "assign_enquiries": sup or staff.get("role") == ROLE_DEPARTMENT_ADMIN,
        "move_enquiries": sup or staff.get("role") == ROLE_DEPARTMENT_ADMIN,
    }
