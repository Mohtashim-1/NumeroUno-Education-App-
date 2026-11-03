import frappe
from frappe.sessions import get_csrf_token

no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.show_sidebar = False
	context.no_header = True
	context.no_footer = True
	# Force a real session CSRF so <!-- csrf_token --> / login POSTs match
	token = get_csrf_token()
	if not token:
		frappe.local.session.data.csrf_token = frappe.generate_hash()
		token = frappe.local.session.data.csrf_token
		try:
			frappe.local.session_obj.update(force=True)
		except Exception:
			pass
	context.csrf_token = token
