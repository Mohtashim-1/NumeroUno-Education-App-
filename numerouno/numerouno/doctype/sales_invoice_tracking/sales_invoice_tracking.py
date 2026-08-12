import frappe
from frappe.model.document import Document


class SalesInvoiceTracking(Document):
	def validate(self):
		if not self.invoice_number:
			return

		docstatus = frappe.db.get_value("Sales Invoice", self.invoice_number, "docstatus")
		if docstatus != 1:
			frappe.throw("Only submitted Sales Invoices can be tracked.")

		self._sync_invoice_snapshot()

	def _sync_invoice_snapshot(self):
		if not self.invoice_number:
			return
		inv = frappe.db.get_value(
			"Sales Invoice",
			self.invoice_number,
			["customer", "customer_name", "posting_date", "grand_total", "currency"],
			as_dict=True,
		)
		if not inv:
			return
		self.customer = inv.customer
		self.customer_name = inv.customer_name
		self.invoice_date = inv.posting_date
		self.grand_total = inv.grand_total
		self.currency = inv.currency
