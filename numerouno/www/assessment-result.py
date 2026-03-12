import frappe

def get_context(context):
    user = frappe.session.user

    # Get customer if this user is a customer
    customer = frappe.db.get_value("Customer", {"email_id": user}, "name")
    
    filters = {"show_on_portal": 1}
    
    if customer:
        # Customer can see all results linked to them
        filters["customer"] = customer
        context.results = frappe.get_all("Assessment Result",
            filters=filters,
            fields=["name", "assessment_title", "score", "total", "student"],
        )
        for r in context.results:
            r["show_download"] = True
    else:
        # Student sees their own results
        filters["owner"] = user
        context.results = frappe.get_all("Assessment Result",
            filters=filters,
            fields=["name", "assessment_title", "score", "total"],
        )
        for r in context.results:
            r["show_download"] = True
