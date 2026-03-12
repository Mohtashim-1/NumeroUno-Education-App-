import frappe
from frappe import _

def get_context(context):
    """Redirect to quiz attempt page"""
    context.no_cache = 1
    context.no_breadcrumbs = 1
    
    # Redirect to the quiz selection page
    frappe.local.flags.redirect_location = "/quiz-attempt"
    raise frappe.Redirect
