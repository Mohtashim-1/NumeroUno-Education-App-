import frappe
from frappe.model.document import Document


class TrainingCandidate(Document):
	def validate(self):
		self.candidate_name = (self.candidate_name or "").strip()
		self.po_number = (self.po_number or "").strip()
		if self.customer and not self.customer_name:
			self.customer_name = frappe.db.get_value("Customer", self.customer, "customer_name")
		if self.student:
			self.status = "Student Created"
		elif not self.status:
			self.status = "Invited"
