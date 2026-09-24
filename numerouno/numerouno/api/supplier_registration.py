# Copyright (c) 2026, NumeroUNO and contributors
# License: MIT

"""Public supplier self-registration API."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, validate_email_address


@frappe.whitelist(allow_guest=True)
def get_registration_context():
	return {
		"portal_name": "NUMEROUNO",
		"tagline": "Supplier Registration",
		"invoice_portal_url": "/supplier-invoice-portal",
		"countries": ["United Arab Emirates"],
		"emirates": [
			"Abu Dhabi",
			"Dubai",
			"Sharjah",
			"Ajman",
			"Umm Al Quwain",
			"Ras Al Khaimah",
			"Fujairah",
		],
	}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def submit_supplier_registration(payload=None):
	"""Create a Supplier Registration document for NumeroUNO staff to approve."""
	if isinstance(payload, str):
		import json

		payload = json.loads(payload)
	payload = payload or frappe.form_dict or {}

	# Prefer nested payload when posted as JSON body
	if payload.get("payload") and isinstance(payload.get("payload"), dict):
		payload = payload["payload"]

	data = _clean(payload)
	_validate(data)

	# Soft duplicate guard — pending or approved with same email/name
	existing = frappe.db.exists(
		"Supplier Registration",
		{
			"email": data["email"],
			"status": ["in", ["Pending Approval", "Approved"]],
		},
	)
	if existing:
		frappe.throw(
			_("A registration with this email is already {0} ({1}).").format(
				frappe.db.get_value("Supplier Registration", existing, "status"),
				existing,
			)
		)

	if frappe.db.exists("Supplier", {"supplier_name": data["supplier_name"]}):
		frappe.throw(
			_("A supplier named {0} already exists. Contact NumeroUNO AP if you need portal access.").format(
				data["supplier_name"]
			)
		)

	doc = frappe.new_doc("Supplier Registration")
	doc.update(data)
	doc.status = "Pending Approval"
	doc.country = data.get("country") or "United Arab Emirates"
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	frappe.db.commit()

	_notify_internal(doc)

	return {
		"status": "success",
		"name": doc.name,
		"message": _(
			"Registration {0} submitted. NumeroUNO will review and approve your supplier account."
		).format(doc.name),
	}


def _clean(payload):
	fields = [
		"supplier_name",
		"supplier_type",
		"trade_license",
		"tax_id",
		"country",
		"city",
		"emirate",
		"contact_person",
		"email",
		"mobile_no",
		"phone",
		"address_line1",
		"address_line2",
		"bank_name",
		"iban",
		"account_name",
		"payment_terms",
		"goods_services",
		"remarks",
	]
	out = {}
	for f in fields:
		val = payload.get(f)
		if isinstance(val, str):
			val = val.strip()
		out[f] = val or None
	if out.get("email"):
		out["email"] = out["email"].lower()
	if not out.get("supplier_type"):
		out["supplier_type"] = "Company"
	if not out.get("payment_terms"):
		out["payment_terms"] = "Net 30"
	return out


def _validate(data):
	required = [
		("supplier_name", _("Supplier / Company Name")),
		("contact_person", _("Contact Person")),
		("email", _("Email")),
		("mobile_no", _("Mobile No")),
		("address_line1", _("Address")),
		("city", _("City")),
	]
	for key, label in required:
		if not data.get(key):
			frappe.throw(_("{0} is required.").format(label))

	validate_email_address(data["email"], throw=True)

	if data.get("supplier_type") not in (None, "Company", "Individual"):
		frappe.throw(_("Invalid supplier type."))


def _notify_internal(doc):
	"""Best-effort notify Accounts Managers — never fail the public submit."""
	try:
		recipients = frappe.get_all(
			"Has Role",
			filters={"role": ["in", ["Accounts Manager", "Purchase Manager"]], "parenttype": "User"},
			pluck="parent",
		)
		recipients = [u for u in set(recipients) if u and u not in ("Guest", "Administrator")]
		# Prefer enabled users with email
		emails = []
		for user in recipients:
			if cint(frappe.db.get_value("User", user, "enabled")):
				email = frappe.db.get_value("User", user, "email")
				if email:
					emails.append(email)
		if not emails:
			return
		frappe.sendmail(
			recipients=list(set(emails))[:20],
			subject=_("New Supplier Registration: {0}").format(doc.supplier_name),
			message=_(
				"<p>A new supplier registration is waiting for approval.</p>"
				"<p><b>{0}</b> ({1})<br>Contact: {2} · {3}<br>"
				'<a href="{4}">Open registration</a></p>'
			).format(
				doc.supplier_name,
				doc.name,
				doc.contact_person,
				doc.email,
				frappe.utils.get_url_to_form("Supplier Registration", doc.name),
			),
			delayed=True,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Supplier Registration notify failed")
