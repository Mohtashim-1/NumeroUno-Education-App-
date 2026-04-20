import frappe


ROLE_NAME = "sales Manager Approval"

NOTIFICATION_SPECS = {
	"Quotation Notification": {
		"subject": "Quotation {{ doc.name }} Pending Approval",
		"condition": 'doc.workflow_state == "Pending Approval"',
		"message": (
			"<p>Dear Sales Manager,</p>\n\n"
			"<p>A new quotation has been submitted for your approval.</p>\n\n"
			"<p>Details:<br>\n"
			"Quotation: {{ doc.name }}<br>\n"
			"Customer: {{ doc.customer }}<br>\n"
			"Transaction Date: {{ doc.transaction_date }}<br>\n"
			"Grand Total: {{ doc.grand_total }}</p>\n\n"
			"<p>Please review and take the necessary action.</p>\n\n"
			"<p>You can view the document here:<br>\n"
			"{{ frappe.utils.get_url() }}/app/quotation/{{ doc.name }}</p>\n\n"
			"<p>Regards,<br>\nERP System</p>\n"
		),
	},
	"Quotation Cancelled Notification": {
		"subject": "Quotation {{ doc.name }} Cancelled",
		"condition": 'doc.workflow_state == "Cancelled"',
		"message": (
			"<p>Dear Sales Manager,</p>\n\n"
			"<p>The following quotation has been cancelled.</p>\n\n"
			"<p>Details:<br>\n"
			"Quotation: {{ doc.name }}<br>\n"
			"Customer: {{ doc.customer }}<br>\n"
			"Transaction Date: {{ doc.transaction_date }}<br>\n"
			"Grand Total: {{ doc.grand_total }}<br>\n"
			"Cancellation Reason: {{ doc.custom_cancellation_reason or \"Not provided\" }}</p>\n\n"
			"<p>You can view the document here:<br>\n"
			"{{ frappe.utils.get_url() }}/app/quotation/{{ doc.name }}</p>\n\n"
			"<p>Regards,<br>\nERP System</p>\n"
		),
	},
}

LEGACY_NOTIFICATION_NAMES = [
	"Sales Order {{ doc.name }} has been Cancelled",
]


def execute():
	for name, spec in NOTIFICATION_SPECS.items():
		ensure_notification(name, spec)

	for name in LEGACY_NOTIFICATION_NAMES:
		if frappe.db.exists("Notification", name):
			frappe.db.set_value("Notification", name, "enabled", 0, update_modified=False)


def ensure_notification(name, spec):
	if frappe.db.exists("Notification", name):
		frappe.db.set_value(
			"Notification",
			name,
			{
				"enabled": 1,
				"is_standard": 1,
				"module": "Numerouno",
				"channel": "Email",
				"document_type": "Quotation",
				"event": "Value Change",
				"value_changed": "workflow_state",
				"condition": spec["condition"],
				"subject": spec["subject"],
				"message_type": "HTML",
				"message": spec["message"],
				"sender": "Notification",
				"sender_email": "erp@numerouno-me.com",
				"send_system_notification": 1,
				"send_to_all_assignees": 0,
				"attach_print": 0,
				"attach_files": "",
				"days_in_advance": 0,
			},
			update_modified=False,
		)
		frappe.db.delete("Notification Recipient", {"parent": name, "parenttype": "Notification"})
		frappe.get_doc(
			{
				"doctype": "Notification Recipient",
				"parent": name,
				"parenttype": "Notification",
				"parentfield": "recipients",
				"receiver_by_role": ROLE_NAME,
			}
		).insert(ignore_permissions=True)
	else:
		doc = frappe.new_doc("Notification")
		doc.name = name
		doc.enabled = 1
		doc.is_standard = 1
		doc.module = "Numerouno"
		doc.channel = "Email"
		doc.document_type = "Quotation"
		doc.event = "Value Change"
		doc.value_changed = "workflow_state"
		doc.condition = spec["condition"]
		doc.subject = spec["subject"]
		doc.message_type = "HTML"
		doc.message = spec["message"]
		doc.sender = "Notification"
		doc.sender_email = "erp@numerouno-me.com"
		doc.send_system_notification = 1
		doc.send_to_all_assignees = 0
		doc.attach_print = 0
		doc.attach_files = ""
		doc.days_in_advance = 0
		doc.append("recipients", {"receiver_by_role": ROLE_NAME})
		doc.insert(ignore_permissions=True)
