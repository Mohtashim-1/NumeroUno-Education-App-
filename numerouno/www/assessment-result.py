import frappe

def get_context(context):
    user = frappe.session.user

    # Get customer if this user is a customer
    customer = frappe.db.get_value("Customer", {"email_id": user}, "name")
    
    from numerouno.numerouno.utils.trainer_confirmation import is_ready_for_client_portal

    filters = {"custom_show_on_portal": 1, "docstatus": 1}

    if customer:
        # Customer can see all results linked to them
        filters["customer_name"] = customer
        context.results = frappe.get_all("Assessment Result",
            filters=filters,
            fields=["name", "assessment_title", "score", "total", "student", "creation", "custom_trainer_confirmed"],
        )
    else:
        # Student sees their own results
        filters["owner"] = user
        context.results = frappe.get_all("Assessment Result",
            filters=filters,
            fields=["name", "assessment_title", "score", "total", "creation", "custom_trainer_confirmed"],
        )

    context.results = [r for r in context.results if is_ready_for_client_portal(r)]
    for r in context.results:
        r["show_download"] = True
