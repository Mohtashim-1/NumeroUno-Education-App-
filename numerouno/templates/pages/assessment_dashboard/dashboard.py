
import frappe

def get_assessments():
    user = frappe.session.user

    customer = frappe.db.get_value("Customer", {"email_id": user}, "name")

    from numerouno.numerouno.utils.trainer_confirmation import is_ready_for_client_portal

    filters = {"custom_show_on_portal": 1, "docstatus": 1}

    if customer:
        filters["customer_name"] = customer
        results = frappe.get_all(
            "Assessment Result",
            filters=filters,
            fields=["name", "assessment_title", "score", "total", "student", "creation", "custom_trainer_confirmed"],
        )
    else:
        filters["owner"] = user
        results = frappe.get_all(
            "Assessment Result",
            filters=filters,
            fields=["name", "assessment_title", "score", "total", "creation", "custom_trainer_confirmed"],
        )

    return [r for r in results if is_ready_for_client_portal(r)]
