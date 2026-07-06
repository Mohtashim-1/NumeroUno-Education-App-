import frappe
from frappe.model.document import Document
from frappe.utils import nowdate


class InvoiceDeliveryAcknowledgement(Document):
	def validate(self):
		if self.sales_invoice and frappe.db.get_value("Sales Invoice", self.sales_invoice, "docstatus") != 1:
			frappe.throw("Only submitted Sales Invoices can be acknowledged.")

	def on_submit(self):
		self._sync_sales_invoice(link_only=False)

	def on_cancel(self):
		frappe.db.set_value(
			"Sales Invoice",
			self.sales_invoice,
			{"custom_delivery_acknowledged": 0, "custom_delivery_acknowledgement": ""},
			update_modified=False,
		)

	def _sync_sales_invoice(self, link_only=False):
		if not self.sales_invoice:
			return
		values = {"custom_delivery_acknowledgement": self.name}
		if not link_only:
			values["custom_delivery_acknowledged"] = 1
		frappe.db.set_value("Sales Invoice", self.sales_invoice, values, update_modified=True)


@frappe.whitelist()
def get_invoice_context(sales_invoice):
	"""Load invoice summary for the driver acknowledgement form."""
	frappe.has_permission("Sales Invoice", "read", sales_invoice, throw=True)
	doc = frappe.get_doc("Sales Invoice", sales_invoice)
	if doc.docstatus != 1:
		frappe.throw("Invoice must be submitted before acknowledgement.")

	lines = []
	for row in doc.items:
		parts = [row.item_name or row.item_code]
		if row.description:
			parts.append(row.description)
		lines.append(" ".join(p for p in parts if p))

	student_lines = []
	for row in getattr(doc, "student", []) or []:
		label = row.student_name or row.student
		if row.student_group:
			label += f" ({row.student_group})"
		student_lines.append(label)

	return {
		"sales_invoice": doc.name,
		"customer": doc.customer,
		"customer_name": doc.customer_name,
		"posting_date": doc.posting_date,
		"grand_total": doc.grand_total,
		"currency": doc.currency,
		"items_text": "\n".join(lines),
		"students_text": "\n".join(student_lines),
		"already_acknowledged": bool(doc.get("custom_delivery_acknowledged")),
		"acknowledgement": doc.get("custom_delivery_acknowledgement"),
		"delivery_driver": doc.get("custom_delivery_driver"),
		"delivery_driver_name": frappe.utils.get_fullname(doc.get("custom_delivery_driver"))
		if doc.get("custom_delivery_driver")
		else "",
	}
