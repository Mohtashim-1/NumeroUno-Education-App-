no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.show_sidebar = False
	context.no_header = True
	context.no_footer = True
	from frappe.sessions import get_csrf_token

	context.csrf_token = get_csrf_token()
