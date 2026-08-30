no_cache = 1


def get_context(context):
	import frappe
	from frappe.sessions import get_csrf_token

	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/training-schedule"
		raise frappe.Redirect

	from numerouno.numerouno.api.training_schedule import _can_view

	if not _can_view():
		frappe.throw("You are not allowed to open the Training Schedule.", frappe.PermissionError)

	context.no_cache = 1
	context.show_sidebar = False
	context.no_header = True
	context.no_footer = True
	context.csrf_token = get_csrf_token()
