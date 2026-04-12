# Copyright (c) 2026, mohtashim and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.utils import nowdate


class NumeroUnoRegistration(Document):
	def validate(self):
		self._normalize_text_fields()
		if not self.signed_date:
			self.signed_date = nowdate()

	def _normalize_text_fields(self):
		for fieldname in (
			"full_name",
			"passport_emirates_id",
			"nationality",
			"contact_number",
			"email",
			"company_name",
			"company_address",
			"contact_person",
			"company_contact_number",
			"company_email",
			"course",
			"location",
			"duration",
		):
			value = self.get(fieldname)
			if isinstance(value, str):
				self.set(fieldname, " ".join(value.split()))
