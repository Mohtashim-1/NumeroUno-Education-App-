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
		"portal_name": "NumeroUNO",
		"company_name": "Numero Uno Training and Consulting LLC",
		"tagline": "Supplier Registration",
		"logo": "/assets/numerouno/images/numero-logo.png",
		"currencies": ["AED", "GBP", "USD"],
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
	from frappe.utils import getdate, nowdate
	from frappe.utils.file_manager import save_file

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

	trade_valid = (payload.get("trade_license_valid_until") or "").strip() or None
	icv_valid = (payload.get("icv_valid_until") or "").strip() or None
	if trade_valid:
		trade_valid = getdate(trade_valid)
	if icv_valid:
		icv_valid = getdate(icv_valid)

	files = getattr(frappe.request, "files", None) or {}
	required_files = {
		"trade_license_attachment": _("Trade License"),
		"tax_registration_certificate": _("Tax Registration Certificate"),
		"iban_letter": _("IBAN Letter"),
	}
	for key, label in required_files.items():
		upload = files.get(key)
		if not upload or not getattr(upload, "filename", None):
			frappe.throw(_("{0} attachment is required.").format(label))

	icv_upload = files.get("icv_certificate")
	has_icv = bool(icv_upload and getattr(icv_upload, "filename", None))

	if not trade_valid:
		frappe.throw(_("Trade License validity date is required."))
	if trade_valid < getdate(nowdate()):
		frappe.throw(_("Trade License validity cannot be in the past."))
	if has_icv and not icv_valid:
		frappe.throw(_("ICV Certificate validity date is required when uploading an ICV Certificate."))
	if icv_valid and icv_valid < getdate(nowdate()):
		frappe.throw(_("ICV Certificate validity cannot be in the past."))

	currency = (data.get("currency") or payload.get("currency") or "AED").upper()
	if currency not in ("AED", "GBP", "USD"):
		frappe.throw(_("Currency must be AED, GBP, or USD."))
	data["currency"] = currency

	doc = frappe.new_doc("Supplier Registration")
	doc.update(data)
	doc.status = "Pending Approval"
	doc.country = data.get("country") or "United Arab Emirates"
	doc.trade_license_valid_until = trade_valid
	if icv_valid:
		doc.icv_valid_until = icv_valid
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)

	attach_map = {
		"trade_license_attachment": "trade_license_attachment",
		"tax_registration_certificate": "tax_registration_certificate",
		"icv_certificate": "icv_certificate",
		"iban_letter": "iban_letter",
		"additional_documents": "additional_documents",
	}
	for form_key, fieldname in attach_map.items():
		upload = files.get(form_key)
		if not upload or not getattr(upload, "filename", None):
			continue
		content = upload.read()
		if not content:
			continue
		if len(content) > 10 * 1024 * 1024:
			frappe.throw(_("{0} must be smaller than 10 MB.").format(form_key.replace("_", " ").title()))
		file_doc = save_file(
			upload.filename,
			content,
			doc.doctype,
			doc.name,
			is_private=1,
			df=fieldname,
		)
		doc.db_set(fieldname, file_doc.file_url, update_modified=False)

	frappe.db.commit()
	doc.reload()
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
		"currency",
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
	if not out.get("currency"):
		out["currency"] = "AED"
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
