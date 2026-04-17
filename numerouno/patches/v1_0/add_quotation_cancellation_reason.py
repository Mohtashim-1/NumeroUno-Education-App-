import frappe


def execute():
	if not frappe.db.exists("DocType", "Quotation"):
		return

	field_name = "custom_cancellation_reason"
	if frappe.db.exists("Custom Field", {"dt": "Quotation", "fieldname": field_name}):
		return

	frappe.get_doc(
		{
			"doctype": "Custom Field",
			"dt": "Quotation",
			"fieldname": field_name,
			"label": "Cancellation Reason",
			"fieldtype": "Small Text",
			"insert_after": "status",
			"allow_on_submit": 1,
		}
	).insert(ignore_permissions=True)
