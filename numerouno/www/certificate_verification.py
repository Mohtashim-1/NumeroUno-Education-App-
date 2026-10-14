no_cache = 1
no_header = 1
no_footer = 1
show_sidebar = 0
safe_render = False


def get_context(context):
	"""Public certificate / driving-card verification page (guest-accessible)."""
	import frappe
	from frappe.sessions import get_csrf_token

	context.no_cache = 1
	context.show_sidebar = False
	context.no_header = True
	context.no_footer = True
	context.safe_render = False
	token = get_csrf_token()
	if not token:
		frappe.local.session.data.csrf_token = frappe.generate_hash()[:20]
		token = frappe.local.session.data.csrf_token
		frappe.db.commit()
	context.csrf_token = token
