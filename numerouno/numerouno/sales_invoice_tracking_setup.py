"""Install Sales Invoice Tracking desk page and DocType fields."""

import frappe


def after_migrate():
	_sync_page_roles()
	frappe.clear_cache()


def _sync_page_roles():
	if not frappe.db.exists("Page", "invoice-print-tracker"):
		frappe.reload_doc("numerouno", "page", "invoice_print_tracker")
	if frappe.db.exists("Page", "invoice-print-tracker"):
		_ensure_page("invoice-print-tracker")


def _ensure_page(page_name):
	page = frappe.get_doc("Page", page_name)
	page.title = "Sales Invoice Tracking"
	roles = {r.role for r in page.roles}
	for role in ("System Manager", "Sales User", "Accounts User", "Accounts Manager"):
		if role not in roles:
			page.append("roles", {"role": role})
	page.save(ignore_permissions=True)
