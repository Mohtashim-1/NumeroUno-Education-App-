import frappe
from frappe.model.document import Document


class TrainingGuestRecord(Document):
	def before_save(self):
		if self.photo or not self.name:
			return

		file_url = frappe.db.get_value(
			"File",
			{
				"attached_to_doctype": self.doctype,
				"attached_to_name": self.name,
				"attached_to_field": "photo",
			},
			"file_url",
			order_by="creation desc",
		)
		if file_url:
			self.photo = file_url
