
import frappe

def get_assessments():
    user = frappe.session.user

    customer = frappe.db.get_value("Customer", {"email_id": user}, "name")

    filters = {"custom_show_on_portal": 1, "docstatus": 1}
    if frappe.get_meta("Assessment Result").has_field("custom_trainer_confirmed"):
        filters["custom_trainer_confirmed"] = 1

    if customer:
        filters["customer_name"] = customer
        results = frappe.get_all("Assessment Result", filters=filters, fields=["name", "assessment_title", "score", "total", "student"])
    else:
        filters["owner"] = user
        results = frappe.get_all("Assessment Result", filters=filters, fields=["name", "assessment_title", "score", "total"])

    return results
