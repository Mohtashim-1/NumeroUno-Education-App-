# Copyright (c) 2026, NumeroUNO and contributors
# License: MIT

import frappe
from frappe.model.document import Document
from frappe.utils import get_url, now_datetime


class GuestTrainingAccount(Document):
	def validate(self):
		self.email = (self.email or "").strip().lower()
		self.company_name = (self.company_name or "").strip()
		if self.status in ("Approved", "Rejected") and not self.reviewed_on:
			self.reviewed_by = frappe.session.user
			self.reviewed_on = now_datetime()

	def on_update(self):
		if self.has_value_changed("status") and self.status == "Approved" and self.email:
			try:
				frappe.sendmail(
					recipients=[self.email],
					subject="Your NumeroUNO training portal account is approved",
					message=(
						f"<p>Hi {frappe.utils.escape_html(self.contact_name or '')},</p>"
						f"<p>Your guest training account for "
						f"<strong>{frappe.utils.escape_html(self.company_name or '')}</strong> is approved.</p>"
						f"<p><a href=\"{get_url('/book-training')}\">Sign in to book training</a></p>"
					),
					now=True,
				)
			except Exception:
				frappe.log_error(frappe.get_traceback(), "Guest Training Account Approve Email")
