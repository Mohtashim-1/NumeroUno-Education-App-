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
