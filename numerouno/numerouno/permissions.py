import frappe


ADNOC_CERTIFICATE_VIEW_ROLE = "ADNOC Certificate View"


def has_adnoc_certificate_view_role(user=None):
    user = user or frappe.session.user
    return ADNOC_CERTIFICATE_VIEW_ROLE in frappe.get_roles(user)


def get_instructor_permission_query_conditions(user=None):
    user = user or frappe.session.user
    roles = set(frappe.get_roles(user))

    if user == "Administrator" or "System Manager" in roles:
        return None

    if ADNOC_CERTIFICATE_VIEW_ROLE in roles:
        return "`tabInstructor`.`custom_is_adnoc_instructor` = 1"

    return None


def has_instructor_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    roles = set(frappe.get_roles(user))

    if user == "Administrator" or "System Manager" in roles:
        return True

    if ADNOC_CERTIFICATE_VIEW_ROLE not in roles:
        return None

    if permission_type and permission_type not in ("read", "select", "print", "email", "export", "report"):
        return False

    return bool(getattr(doc, "custom_is_adnoc_instructor", 0))


def get_attendance_staff_permission_query_conditions(user=None):
    # Keep Attendance Staff globally visible to any role that already has
    # DocType read/select permission through role permissions.
    return None


def has_attendance_staff_permission(doc, user=None, permission_type=None):
    # Defer to standard role-based DocType permissions.
    return None


# Roles that may only view Assessment Result (never create/edit/submit/cancel)
ASSESSMENT_RESULT_VIEW_ONLY_ROLES = frozenset({"Customer"})
ASSESSMENT_RESULT_VIEW_PERM_TYPES = frozenset(
    {"read", "select", "print", "email", "export", "report", "share"}
)


def has_assessment_result_permission(doc, user=None, permission_type=None):
    """Customers can view Assessment Result only — no edits."""
    user = user or frappe.session.user
    if user in ("Administrator", "Guest"):
        return None

    roles = set(frappe.get_roles(user))
    if "System Manager" in roles or "Academics User" in roles or "Trainer" in roles:
        return None

    if not (roles & ASSESSMENT_RESULT_VIEW_ONLY_ROLES):
        return None

    # Customer (and similar): allow view-type perms only
    if not permission_type:
        return True
    if permission_type in ASSESSMENT_RESULT_VIEW_PERM_TYPES:
        return True
    return False


def assert_assessment_result_not_customer_write(doc, method=None):
    """Hard block save/update/cancel for Customer role even if UI or API bypasses checks."""
    user = frappe.session.user
    if user in ("Administrator",):
        return
    roles = set(frappe.get_roles(user))
    if "System Manager" in roles or "Academics User" in roles or "Trainer" in roles:
        return
    if roles & ASSESSMENT_RESULT_VIEW_ONLY_ROLES:
        frappe.throw(
            "Customers can only view Assessment Result. Editing is not allowed.",
            frappe.PermissionError,
        )
