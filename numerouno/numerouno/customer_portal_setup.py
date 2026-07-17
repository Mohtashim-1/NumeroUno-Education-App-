# Copyright (c) 2026, NumeroUNO and contributors
# License: MIT

"""Customer Invoice Portal — custom fields + welcome email."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import cint, get_url


PORTAL_ACCESS_FIELD = "custom_invoice_portal_access"
PORTAL_WELCOME_FIELD = "custom_send_portal_welcome_email"
PORTAL_WELCOME_SENT_FIELD = "custom_invoice_portal_welcome_sent"


def get_customer_portal_custom_fields():
	return {
		"Customer": [
			{
				"fieldname": "custom_invoice_portal_section",
				"fieldtype": "Section Break",
				"label": "Invoice Portal",
				"insert_after": "portal_users_tab",
				"collapsible": 0,
			},
			{
				"fieldname": PORTAL_ACCESS_FIELD,
				"fieldtype": "Check",
				"label": "Allow Invoice Portal Access",
				"insert_after": "custom_invoice_portal_section",
				"description": "Customer can sign in at /customer-portal to view invoices and pay online.",
				"default": "0",
			},
			{
				"fieldname": PORTAL_WELCOME_FIELD,
				"fieldtype": "Check",
				"label": "Send / Resend Welcome Email",
				"insert_after": PORTAL_ACCESS_FIELD,
				"depends_on": f"eval:doc.{PORTAL_ACCESS_FIELD}",
				"description": "Sends a branded welcome email with the portal link. Cleared automatically after send.",
				"default": "0",
			},
			{
				"fieldname": PORTAL_WELCOME_SENT_FIELD,
				"fieldtype": "Check",
				"label": "Welcome Email Sent",
				"insert_after": PORTAL_WELCOME_FIELD,
				"read_only": 1,
				"default": "0",
			},
		],
		"Sales Invoice": [
			{
				"fieldname": "custom_portal_payment_section",
				"fieldtype": "Section Break",
				"label": "Portal Payment",
				"insert_after": "advances_section",
				"collapsible": 0,
			},
			{
				"fieldname": "custom_portal_payment_request",
				"fieldtype": "Link",
				"label": "Portal Payment Request",
				"options": "Portal Payment Request",
				"insert_after": "custom_portal_payment_section",
				"description": "Link paid Stripe portal charge (e.g. PPR-2026-00001). Allocates on Submit.",
			},
		],
	}


def ensure_customer_portal_fields():
	create_custom_fields(get_customer_portal_custom_fields(), update=True)


def after_migrate():
	ensure_customer_portal_fields()


def _customer_email(doc) -> str:
	email = (getattr(doc, "email_id", None) or "").strip()
	if email:
		return email.lower()
	# Fall back to primary contact
	contact = getattr(doc, "customer_primary_contact", None)
	if contact:
		email = frappe.db.get_value("Contact", contact, "email_id")
		if email:
			return email.strip().lower()
	# Any linked contact email
	links = frappe.get_all(
		"Dynamic Link",
		filters={"link_doctype": "Customer", "link_name": doc.name, "parenttype": "Contact"},
		pluck="parent",
		limit=5,
	)
	for parent in links:
		email = frappe.db.get_value("Contact", parent, "email_id")
		if email:
			return email.strip().lower()
	return ""


def on_customer_update(doc, method=None):
	"""When portal access is enabled (or welcome checkbox ticked), send welcome email."""
	if not frappe.db.has_column("Customer", PORTAL_ACCESS_FIELD):
		return

	access = cint(doc.get(PORTAL_ACCESS_FIELD))
	send_welcome = cint(doc.get(PORTAL_WELCOME_FIELD))
	welcome_sent = cint(doc.get(PORTAL_WELCOME_SENT_FIELD))
	access_just_enabled = access and (
		doc.is_new() or doc.has_value_changed(PORTAL_ACCESS_FIELD)
	)

	should_send = False
	if access and send_welcome:
		should_send = True
	elif access_just_enabled and not welcome_sent:
		# First time enabling access → auto welcome
		should_send = True

	if not should_send:
		# Clear the "send" flag if access turned off
		if send_welcome and not access:
			doc.db_set(PORTAL_WELCOME_FIELD, 0, update_modified=False)
		return

	email = _customer_email(doc)
	if not email:
		frappe.msgprint(
			_("Invoice portal access is on, but this customer has no email. Add an email to send the welcome message."),
			indicator="orange",
			alert=True,
		)
		doc.db_set(PORTAL_WELCOME_FIELD, 0, update_modified=False)
		return

	from numerouno.numerouno.api.customer_portal import send_portal_welcome_email

	try:
		send_portal_welcome_email(doc, email)
		doc.db_set(PORTAL_WELCOME_SENT_FIELD, 1, update_modified=False)
		doc.db_set(PORTAL_WELCOME_FIELD, 0, update_modified=False)
		frappe.msgprint(
			_("Welcome email sent to {0}").format(email),
			indicator="green",
			alert=True,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Customer Portal Welcome Email")
		frappe.msgprint(
			_("Could not send welcome email. Check Error Log / Email Queue."),
			indicator="red",
			alert=True,
		)
		doc.db_set(PORTAL_WELCOME_FIELD, 0, update_modified=False)


def on_sales_invoice_submit(doc, method=None):
	"""If SI is linked to a paid Portal Payment Request, allocate the Stripe advance."""
	ppr_name = doc.get("custom_portal_payment_request")
	if not ppr_name or not frappe.db.exists("Portal Payment Request", ppr_name):
		return
	ppr = frappe.get_doc("Portal Payment Request", ppr_name)
	if ppr.customer != doc.customer:
		frappe.throw(_("Portal Payment Request customer does not match this invoice."))
	if ppr.status not in ("Paid", "Allocated") or not ppr.payment_entry:
		return
	try:
		ppr.allocate_payment_to_invoice(doc.name)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Allocate Portal Payment on SI Submit")
		frappe.msgprint(
			_("Could not auto-allocate portal payment. Use Allocate on Portal Payment Request."),
			indicator="orange",
			alert=True,
		)
