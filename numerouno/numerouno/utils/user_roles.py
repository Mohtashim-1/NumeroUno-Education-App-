import frappe


ROLE_NAME = "Vehicle User"
EXCLUDED_USERS = {"Administrator", "Guest"}


def assign_vehicle_user_role(doc, method=None):
    if not doc or doc.name in EXCLUDED_USERS:
        return

    if ROLE_NAME in {row.role for row in doc.get("roles") if row.role}:
        return

    doc.add_roles(ROLE_NAME)


def assign_vehicle_user_role_to_all_users():
    if not frappe.db.exists("Role", ROLE_NAME):
        frappe.throw(f"Role '{ROLE_NAME}' does not exist.")

    users = frappe.get_all(
        "User",
        filters={"enabled": 1, "name": ["not in", list(EXCLUDED_USERS)]},
        pluck="name",
    )

    for user_name in users:
        user_doc = frappe.get_doc("User", user_name)
        assign_vehicle_user_role(user_doc)
