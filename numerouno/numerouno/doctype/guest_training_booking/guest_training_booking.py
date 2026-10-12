# Copyright (c) 2026, NumeroUNO and contributors
# License: MIT

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class GuestTrainingBooking(Document):
	def validate(self):
		if self.account and not self.company_name:
			self.company_name = frappe.db.get_value(
				"Guest Training Account", self.account, "company_name"
			)
		if self.account and not self.contact_email:
			self.contact_email = frappe.db.get_value("Guest Training Account", self.account, "email")
		if self.status == "Confirmed" and not self.confirmed_on:
			self.confirmed_by = frappe.session.user
			self.confirmed_on = now_datetime()
