# Copyright (c) 2026, NumeroUNO and contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import formatdate, get_url, getdate, today


class TrainingDateRequest(Document):
	def validate(self):
		self._set_defaults()
		self._validate_dates()

	def after_insert(self):
		if self.status == "Open":
			_notify_coordinators_new_request(self)

	def on_update(self):
		pass

	def _set_defaults(self):
		if not self.posting_date:
			self.posting_date = today()
		if not self.company:
			self.company = frappe.db.get_single_value("Global Defaults", "default_company")
		if self.customer and not self.customer_name:
			self.customer_name = frappe.db.get_value("Customer", self.customer, "customer_name")
		if self.course and not self.course_name:
			self.course_name = (
				frappe.db.get_value("Course", self.course, "course_name") or self.course
			)

	def _validate_dates(self):
		if self.preferred_date and getdate(self.preferred_date) < getdate(today()):
			if self.is_new() or self.has_value_changed("preferred_date"):
				frappe.throw(_("Preferred date cannot be in the past."))
		if self.status == "Proposed" and not self.proposed_date:
			frappe.throw(_("Proposed date is required when status is Proposed."))
		if self.status == "Confirmed" and not self.confirmed_date:
			frappe.throw(_("Confirmed date is required when status is Confirmed."))


def _coordinator_emails():
	"""Users with Training Coordinator / Academics / Education Manager roles."""
	roles = ("Training Coordinator", "Academics User", "Education Manager")
	users = frappe.get_all(
		"Has Role",
		filters={"parenttype": "User", "role": ("in", roles)},
		pluck="parent",
	)
	emails = []
	for user in set(users or []):
		if user in ("Administrator", "Guest"):
			continue
		enabled = frappe.db.get_value("User", user, "enabled")
		email = frappe.db.get_value("User", user, "email")
		if enabled and email:
			emails.append(email)
	# fallback support inbox
	if not emails:
		fallback = frappe.db.get_value("Email Account", {"default_outgoing": 1}, "email_id")
		if fallback:
			emails.append(fallback)
	return sorted(set(emails))


def _send_mail(recipients, subject, html):
	recipients = [r for r in (recipients or []) if r]
	if not recipients:
		return
	try:
		frappe.sendmail(
			recipients=recipients,
			subject=subject,
			message=html,
			now=True,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Training Date Request Email")


def _portal_url():
	return get_url("/customer-portal")


def _desk_url(name):
	return get_url(f"/app/training-date-request/{name}")


def _notify_coordinators_new_request(doc):
	from numerouno.numerouno.api.customer_portal import _email_shell

	body = f"""
<p style="margin:0 0 14px;font-size:15px;line-height:1.5;color:#1a3644;">
  A customer requested a training date via the Customer Portal.
</p>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"
  style="border-collapse:collapse;font-size:14px;color:#1a3644;">
  <tr><td style="padding:6px 0;width:140px;color:#5d6f79;">Request</td>
      <td style="padding:6px 0;"><strong>{frappe.utils.escape_html(doc.name)}</strong></td></tr>
  <tr><td style="padding:6px 0;color:#5d6f79;">Customer</td>
      <td style="padding:6px 0;">{frappe.utils.escape_html(doc.customer_name or doc.customer)}</td></tr>
  <tr><td style="padding:6px 0;color:#5d6f79;">Course</td>
      <td style="padding:6px 0;">{frappe.utils.escape_html(doc.course_name or doc.course)}</td></tr>
  <tr><td style="padding:6px 0;color:#5d6f79;">Preferred date</td>
      <td style="padding:6px 0;"><strong>{formatdate(doc.preferred_date)}</strong></td></tr>
  <tr><td style="padding:6px 0;color:#5d6f79;">Participants</td>
      <td style="padding:6px 0;">{doc.participants or 1}</td></tr>
</table>
<p style="margin:22px 0 0;">
  <a href="{_desk_url(doc.name)}"
     style="display:inline-block;background:#1f7a72;color:#fff;text-decoration:none;
            padding:12px 18px;border-radius:10px;font-weight:600;">
    Open in Coordinator Desk
  </a>
</p>
"""
	_send_mail(
		_coordinator_emails(),
		f"Training date request — {doc.customer_name or doc.customer}",
		_email_shell("New training date request", "Please review and accept or propose a new date.", body),
	)


def notify_customer_status(doc, title: str, message: str):
	from numerouno.numerouno.api.customer_portal import _email_shell

	if not doc.contact_email:
		return
	body = f"""
<p style="margin:0 0 14px;font-size:15px;line-height:1.5;color:#1a3644;">{message}</p>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"
  style="border-collapse:collapse;font-size:14px;color:#1a3644;">
  <tr><td style="padding:6px 0;width:140px;color:#5d6f79;">Request</td>
      <td style="padding:6px 0;"><strong>{frappe.utils.escape_html(doc.name)}</strong></td></tr>
  <tr><td style="padding:6px 0;color:#5d6f79;">Course</td>
      <td style="padding:6px 0;">{frappe.utils.escape_html(doc.course_name or doc.course)}</td></tr>
  <tr><td style="padding:6px 0;color:#5d6f79;">Preferred</td>
      <td style="padding:6px 0;">{formatdate(doc.preferred_date) if doc.preferred_date else "—"}</td></tr>
  <tr><td style="padding:6px 0;color:#5d6f79;">Proposed</td>
      <td style="padding:6px 0;">{formatdate(doc.proposed_date) if doc.proposed_date else "—"}</td></tr>
  <tr><td style="padding:6px 0;color:#5d6f79;">Confirmed</td>
      <td style="padding:6px 0;"><strong>{formatdate(doc.confirmed_date) if doc.confirmed_date else "—"}</strong></td></tr>
  <tr><td style="padding:6px 0;color:#5d6f79;">Status</td>
      <td style="padding:6px 0;"><strong>{frappe.utils.escape_html(doc.status)}</strong></td></tr>
</table>
<p style="margin:22px 0 0;">
  <a href="{_portal_url()}"
     style="display:inline-block;background:#1f7a72;color:#fff;text-decoration:none;
            padding:12px 18px;border-radius:10px;font-weight:600;">
    Open Customer Portal
  </a>
</p>
"""
	_send_mail(
		[doc.contact_email],
		title,
		_email_shell(title, message, body),
	)
