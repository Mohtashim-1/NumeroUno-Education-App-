
import frappe

def get_assessments():
    user = frappe.session.user

    customer = frappe.db.get_value("Customer", {"email_id": user}, "name")

    filters = {"show_on_portal": 1}

    if customer:
        filters["customer"] = customer
        results = frappe.get_all("Assessment Result", filters=filters, fields=["name", "assessment_title", "score", "total", "student"])
    else:
        filters["owner"] = user
        results = frappe.get_all("Assessment Result", filters=filters, fields=["name", "assessment_title", "score", "total"])

    return results
