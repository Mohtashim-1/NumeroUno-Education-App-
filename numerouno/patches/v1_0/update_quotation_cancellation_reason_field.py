import frappe


def execute():
	field_name = "custom_cancellation_reason"
	field = frappe.db.exists("Custom Field", {"dt": "Quotation", "fieldname": field_name})
	if not field:
		return

	doc = frappe.get_doc("Custom Field", field)
	changed = False

	if not doc.allow_on_submit:
		doc.allow_on_submit = 1
		changed = True

	if not doc.no_copy:
		doc.no_copy = 1
		changed = True

	if doc.insert_after != "status":
		doc.insert_after = "status"
		changed = True

	if changed:
		doc.save(ignore_permissions=True)
