# Copyright (c) 2026, NumeroUNO and contributors
# License: MIT

"""Supplier Invoice Portal — bootstrap data and invoice submission."""

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, formatdate, get_fullname, get_url, getdate, nowdate

from numerouno.numerouno.supplier_compliance_setup import ensure_supplier_compliance_fields


GATE_DOC_IDS = ("trade_license", "icv")


def _status_for_validity(valid_until, has_file: bool) -> tuple[str, str]:
	"""Return (status, meta_suffix) for a validity-gated document."""
	if not has_file or not valid_until:
		return "Missing", "Upload required · set validity date"
	valid_until = getdate(valid_until)
	today = getdate(nowdate())
	if valid_until < today:
		return "Overdue", f"Expired {formatdate(valid_until)}"
	days = date_diff(valid_until, today)
	if days <= 30:
		return "Expiring soon", f"Valid until {formatdate(valid_until)}"
	return "Valid", f"Valid until {formatdate(valid_until)}"


def _demo_compliance_cache_key() -> str:
	sid = getattr(frappe.session, "sid", None) or "guest"
	return f"supplier_portal_compliance:{sid}"


def _get_demo_compliance_store() -> dict:
	return frappe.cache().get_value(_demo_compliance_cache_key()) or {}


def _set_demo_compliance_store(store: dict):
	frappe.cache().set_value(_demo_compliance_cache_key(), store, expires_in_sec=60 * 60 * 24 * 7)


def _compliance_docs_for_supplier(supplier: str | None) -> list[dict]:
	"""Merge seed template with Supplier-stored Trade License / ICV (and other files)."""
	seed = _demo_seed()["compliance_docs"]
	if not supplier or not frappe.db.exists("Supplier", supplier):
		store = _get_demo_compliance_store()
		out = []
		for doc in seed:
			d = dict(doc)
			saved = store.get(d["id"]) or {}
			if saved:
				d.update({k: saved[k] for k in saved if k in d or k in ("file_url", "file_name", "valid_until", "status", "meta")})
				if d["id"] in GATE_DOC_IDS:
					status, meta = _status_for_validity(saved.get("valid_until"), bool(saved.get("file_url")))
					d["status"] = status
					d["valid_until"] = str(saved.get("valid_until") or "")
					d["file_url"] = saved.get("file_url") or ""
					d["file_name"] = saved.get("file_name") or ""
					d["meta"] = f"{d['file_name']} · {meta}" if d["file_name"] else meta
				else:
					d["status"] = saved.get("status") or "On file"
					d["file_url"] = saved.get("file_url") or ""
					d["file_name"] = saved.get("file_name") or ""
					d["meta"] = saved.get("meta") or d["meta"]
			out.append(d)
		return out

	ensure_supplier_compliance_fields()
	row = frappe.db.get_value(
		"Supplier",
		supplier,
		[
			"custom_trade_license_file",
			"custom_trade_license_valid_until",
			"custom_icv_certificate_file",
			"custom_icv_valid_until",
			"custom_tax_registration_certificate",
			"custom_iban_letter",
			"custom_additional_documents",
		],
		as_dict=True,
	) or {}

	out = []
	for doc in seed:
		d = dict(doc)
		if d["id"] == "trade_license":
			d["file_url"] = row.get("custom_trade_license_file") or ""
			d["file_name"] = (d["file_url"] or "").rsplit("/", 1)[-1] if d["file_url"] else ""
			d["valid_until"] = str(row.get("custom_trade_license_valid_until") or "")
			status, meta = _status_for_validity(row.get("custom_trade_license_valid_until"), bool(d["file_url"]))
			d["status"] = status
			d["meta"] = meta if not d["file_name"] else f"{d['file_name']} · {meta}"
		elif d["id"] == "icv":
			d["file_url"] = row.get("custom_icv_certificate_file") or ""
			d["file_name"] = (d["file_url"] or "").rsplit("/", 1)[-1] if d["file_url"] else ""
			d["valid_until"] = str(row.get("custom_icv_valid_until") or "")
			status, meta = _status_for_validity(row.get("custom_icv_valid_until"), bool(d["file_url"]))
			d["status"] = status
			d["meta"] = meta if not d["file_name"] else f"{d['file_name']} · {meta}"
		elif d["id"] == "tax_registration":
			url = row.get("custom_tax_registration_certificate") or ""
			if url:
				d["file_url"] = url
				d["file_name"] = url.rsplit("/", 1)[-1]
				d["status"] = "On file"
				d["meta"] = d["file_name"]
		elif d["id"] == "iban_letter":
			url = row.get("custom_iban_letter") or ""
			if url:
				d["file_url"] = url
				d["file_name"] = url.rsplit("/", 1)[-1]
				d["status"] = "On file"
				d["meta"] = d["file_name"]
		elif d["id"] == "additional":
			url = row.get("custom_additional_documents") or ""
			if url:
				d["file_url"] = url
				d["file_name"] = url.rsplit("/", 1)[-1]
				d["status"] = "On file"
				d["meta"] = d["file_name"]
		out.append(d)
	return out


def get_compliance_gate(supplier: str | None = None) -> dict:
	"""Invoice creation is blocked when Trade License or ICV is missing/expired."""
	supplier = supplier if supplier is not None else _supplier_for_user()
	docs = _compliance_docs_for_supplier(supplier)
	blocking = []
	for d in docs:
		if d["id"] not in GATE_DOC_IDS:
			continue
		if d.get("status") in ("Missing", "Overdue"):
			blocking.append(
				{
					"id": d["id"],
					"name": d["name"],
					"status": d.get("status"),
					"valid_until": d.get("valid_until") or "",
					"meta": d.get("meta") or "",
				}
			)
	allowed = len(blocking) == 0
	message = ""
	if not allowed:
		parts = [f"{b['name']} ({b['status']})" for b in blocking]
		message = _(
			"Invoice submission is blocked until these documents are current: {0}. "
			"Upload renewed files under Compliance."
		).format(", ".join(parts))
	return {
		"allowed": allowed,
		"blocking": blocking,
		"message": message,
	}


def assert_supplier_can_invoice(supplier: str | None = None):
	"""Throw if Trade License or ICV Certificate is missing or expired."""
	gate = get_compliance_gate(supplier)
	if not gate["allowed"]:
		frappe.throw(gate["message"])


def _persist_compliance_on_supplier(supplier: str, doc_id: str, file_url: str, valid_until=None):
	ensure_supplier_compliance_fields()
	field_map = {
		"trade_license": ("custom_trade_license_file", "custom_trade_license_valid_until"),
		"icv": ("custom_icv_certificate_file", "custom_icv_valid_until"),
		"tax_registration": ("custom_tax_registration_certificate", None),
		"iban_letter": ("custom_iban_letter", None),
		"additional": ("custom_additional_documents", None),
	}
	file_field, date_field = field_map.get(doc_id, (None, None))
	if not file_field:
		return
	updates = {file_field: file_url}
	if date_field and valid_until:
		updates[date_field] = getdate(valid_until)
	frappe.db.set_value("Supplier", supplier, updates, update_modified=True)


def _demo_seed():
	return {
		"vendor": {
			"display_name": "ACME Manufacturing",
			"contact_name": "Jessica Chen",
			"vendor_id": "V-004812",
			"ap_email": "ap@buyerco.com",
			"supplier": None,
		},
		"open_pos": [
			{"id": "PO-100251", "label": "PO-100251 · Machined brackets · AED 22,400.00", "amount": 22400, "currency": "AED"},
			{"id": "PO-100248", "label": "PO-100248 · Hydraulic fittings · AED 8,915.00", "amount": 8915, "currency": "AED"},
			{"id": "PO-100245", "label": "PO-100245 · Steel sheet stock · AED 18,420.50", "amount": 18420.5, "currency": "AED"},
		],
		"orders": [
			{"id": "PO-100251", "desc": "Machined brackets, 6061-T6 (400 pcs)", "issued": "Sep 15, 2026", "value": 22400, "status": "Open"},
			{"id": "PO-100248", "desc": "Hydraulic fittings, assorted", "issued": "Sep 09, 2026", "value": 8915, "status": "Open"},
			{"id": "PO-100245", "desc": "Steel sheet stock, 12 ga", "issued": "Aug 28, 2026", "value": 18420.5, "status": "Invoiced"},
		],
		"submissions": [
			{"num": "INV-2026-0412", "po": "PO-100245", "date": "Sep 18, 2026", "due": "Oct 18, 2026", "amount": 18420.5, "currency": "AED", "status": "Pending review"},
			{"num": "INV-2026-0397", "po": "PO-100243", "date": "Sep 02, 2026", "due": "Oct 02, 2026", "amount": 6210, "currency": "AED", "status": "Approved"},
			{"num": "INV-2026-0381", "po": "PO-100231", "date": "Aug 21, 2026", "due": "Sep 20, 2026", "amount": 2875.75, "currency": "AED", "status": "Needs info"},
		],
		"inventory": [
			{"sku": "AC-BRK-0612", "name": "Machined bracket, 6\"", "loc": "Dayton DC", "qty": 1240, "reorder": 500},
			{"sku": "AC-FIT-3308", "name": "Hydraulic elbow fitting", "loc": "Dayton DC", "qty": 310, "reorder": 400},
			{"sku": "AC-SHT-12GA", "name": "Steel sheet, 12 ga 4×8", "loc": "Columbus", "qty": 86, "reorder": 60},
			{"sku": "AC-FST-M8Z", "name": "M8 fastener kit", "loc": "Columbus", "qty": 0, "reorder": 200},
			{"sku": "AC-FRM-2200", "name": "Welded frame assembly", "loc": "Dayton DC", "qty": 42, "reorder": 20},
		],
		"compliance_docs": [
			{
				"id": "trade_license",
				"name": "Trade License",
				"meta": "Upload license · set validity date",
				"status": "Missing",
				"requires_validity": True,
				"valid_until": "",
				"file_name": "",
			},
			{
				"id": "tax_registration",
				"name": "Tax Registration Certificate",
				"meta": "VAT / Tax registration certificate",
				"status": "Missing",
				"requires_validity": False,
				"valid_until": "",
				"file_name": "",
			},
			{
				"id": "icv",
				"name": "ICV Certificate",
				"meta": "In-Country Value certificate · set validity date",
				"status": "Missing",
				"requires_validity": True,
				"valid_until": "",
				"file_name": "",
			},
			{
				"id": "iban_letter",
				"name": "IBAN Letter",
				"meta": "Bank IBAN confirmation letter",
				"status": "Missing",
				"requires_validity": False,
				"valid_until": "",
				"file_name": "",
			},
			{
				"id": "additional",
				"name": "Additional Documents",
				"meta": "Any other supporting compliance files",
				"status": "Optional",
				"requires_validity": False,
				"valid_until": "",
				"file_name": "",
			},
		],
		"message_threads": [
			{
				"id": 1,
				"from": "BuyerCo Accounts Payable",
				"subject": "INV-2026-0381 — line-item breakdown needed",
				"when": "Sep 21",
				"unread": True,
				"msgs": [
					{
						"me": False,
						"text": "Hi Jessica — for INV-2026-0381 we need unit pricing per line to complete the 3-way match. Could you resubmit with a breakdown?",
						"meta": "Maria Lopez · Sep 21, 10:14 AM",
					}
				],
			},
			{
				"id": 2,
				"from": "Procurement — R. Patel",
				"subject": "PO-100251 delivery window",
				"when": "Sep 16",
				"unread": True,
				"msgs": [
					{
						"me": False,
						"text": "Confirming delivery for PO-100251 is expected the week of Oct 5. Let us know if that changes.",
						"meta": "Raj Patel · Sep 16, 3:02 PM",
					},
					{"me": True, "text": "Confirmed — we are on track to ship Oct 2.", "meta": "You · Sep 16, 4:40 PM"},
				],
			},
			{
				"id": 3,
				"from": "Supplier Compliance",
				"subject": "Compliance documents required",
				"when": "Sep 10",
				"unread": True,
				"msgs": [
					{
						"me": False,
						"text": "Please upload your Trade License, Tax Registration Certificate, ICV Certificate, and IBAN Letter under Compliance (with validity dates where required) to stay eligible for payment.",
						"meta": "Compliance Team · Sep 10, 9:00 AM",
					}
				],
			},
		],
		"help_articles": [
			{
				"title": "How do I submit an invoice?",
				"body": "Go to Submit Invoice, upload the invoice PDF, select the PO, enter an invoice date (today or up to 7 days back, AED only), then add the delivery note signed by a Numero employee and review.",
			},
			{
				"title": "What invoice dates are allowed?",
				"body": "Future invoice dates are blocked. Back-dated invoices are allowed only within the last 7 days.",
			},
			{
				"title": "Do delivery notes need a Numero signature?",
				"body": "Yes. Provide the DN number, confirm it was signed by a Numero employee, enter the signed date, and upload the signed DN document. Unsigned delivery notes are rejected.",
			},
			{
				"title": "When will I get paid?",
				"body": "After submit, NumeroUNO AP reviews the invoice (typically 2–3 business days). Approved invoices pay per your terms (e.g. Net 30) in AED.",
			},
			{
				"title": "Which compliance documents are required?",
				"body": "Trade License and ICV Certificate must be uploaded with a future validity date. If either is missing or expired, you cannot submit invoices. Tax Registration Certificate, IBAN Letter, and Additional Documents are also collected but do not block invoicing.",
			},
			{
				"title": "Why can't I submit an invoice?",
				"body": "Invoice submission is blocked when your Trade License or ICV Certificate is missing or expired. Go to Compliance, enter the new validity date, upload the renewed file, then try again.",
			},
		],
		"profile": {
			"email": "jessica.chen@acmemfg.com",
			"phone": "+971 50 555 0142",
			"address": "Industrial Area, Abu Dhabi, UAE",
			"payment_method": "Bank transfer",
			"bank_account": "Emirates NBD ····4417",
			"notify_email": True,
			"notify_status": True,
		},
	}


def _supplier_for_user(user: str | None = None) -> str | None:
	user = user or frappe.session.user
	if not user or user == "Guest":
		return None
	if frappe.db.exists("Supplier", {"supplier_name": user}):
		return user
	if frappe.db.table_exists("Portal User"):
		links = frappe.get_all(
			"Portal User",
			filters={"parenttype": "Supplier", "user": user},
			fields=["parent"],
			limit=1,
		)
		if links:
			return links[0].parent
	contact = frappe.db.get_value("Contact", {"email_id": user}, "name")
	if contact:
		for row in frappe.get_all(
			"Dynamic Link",
			filters={"link_doctype": "Supplier", "parenttype": "Contact", "parent": contact},
			fields=["link_name"],
			limit=1,
		):
			return row.link_name
	return None


def _open_pos_for_supplier(supplier: str) -> list[dict]:
	if not supplier or not frappe.db.exists("Supplier", supplier):
		return []
	pos = frappe.get_all(
		"Purchase Order",
		filters={"supplier": supplier, "docstatus": 1, "status": ["not in", ["Closed", "Cancelled"]]},
		fields=["name", "transaction_date", "grand_total", "currency"],
		order_by="transaction_date desc",
		limit=50,
	)
	out = []
	for po in pos:
		label = f"{po.name} · {formatdate(po.transaction_date)} · {po.grand_total}"
		out.append({"id": po.name, "label": label, "amount": flt(po.grand_total), "currency": po.currency or "AED"})
	return out


def _submissions_for_supplier(supplier: str) -> list[dict]:
	if not supplier:
		return []
	invoices = frappe.get_all(
		"Purchase Invoice",
		filters={"supplier": supplier, "docstatus": ["<", 2]},
		fields=["name", "bill_no", "posting_date", "due_date", "grand_total", "currency", "status"],
		order_by="modified desc",
		limit=50,
	)
	status_map = {0: "Pending review", 1: "Approved", 2: "Paid"}
	out = []
	for inv in invoices:
		docstatus = frappe.db.get_value("Purchase Invoice", inv.name, "docstatus")
		st = status_map.get(docstatus, inv.status or "Pending review")
		if inv.status == "Paid":
			st = "Paid"
		po = frappe.db.get_value(
			"Purchase Invoice Item",
			{"parent": inv.name, "purchase_order": ["is", "set"]},
			"purchase_order",
		)
		out.append(
			{
				"num": inv.bill_no or inv.name,
				"po": po or "—",
				"date": formatdate(inv.posting_date) if inv.posting_date else "—",
				"due": formatdate(inv.due_date) if inv.due_date else "—",
				"amount": flt(inv.grand_total),
				"currency": inv.currency or "AED",
				"status": st,
				"pi_name": inv.name,
			}
		)
	return out


@frappe.whitelist(allow_guest=True)
def login(usr=None, pwd=None):
	"""Email + password login for Supplier Invoice Portal."""
	usr = (usr or frappe.form_dict.get("usr") or "").strip().lower()
	pwd = pwd or frappe.form_dict.get("pwd") or ""
	if not usr or not pwd:
		frappe.throw(_("Email and password are required."))

	from frappe.auth import LoginManager

	frappe.local.login_manager = LoginManager()
	try:
		frappe.local.login_manager.authenticate(user=usr, pwd=pwd)
		frappe.local.login_manager.post_login()
	except frappe.AuthenticationError:
		frappe.clear_messages()
		frappe.throw(_("Invalid email or password."))

	supplier = _supplier_for_user(frappe.session.user)
	if not supplier:
		frappe.local.login_manager.logout()
		frappe.throw(
			_(
				"This account is not linked to a Supplier. "
				"Ask NumeroUNO AP to create an Invoice Portal user on the Supplier form."
			)
		)

	return {
		"ok": 1,
		"user": frappe.session.user,
		"supplier": supplier,
		"message": _("Signed in successfully."),
	}


@frappe.whitelist()
def logout():
	"""Sign out of Supplier Invoice Portal."""
	if getattr(frappe.local, "login_manager", None):
		frappe.local.login_manager.logout()
	else:
		from frappe.auth import LoginManager

		LoginManager().logout()
	return {"ok": 1}


@frappe.whitelist()
def create_supplier_portal_user(supplier, email=None, full_name=None, password=None, send_email=0):
	"""Desk action: create Website User, set password, link under Supplier → Portal Users."""
	frappe.only_for(("System Manager", "Accounts Manager", "Purchase Manager", "Purchase User"))

	if not supplier or not frappe.db.exists("Supplier", supplier):
		frappe.throw(_("Supplier not found."))

	email = (email or "").strip().lower()
	full_name = (full_name or "").strip() or frappe.db.get_value("Supplier", supplier, "supplier_name")
	password = password or ""
	if not email:
		frappe.throw(_("Login email is required."))
	if len(password) < 8:
		frappe.throw(_("Password must be at least 8 characters."))

	from frappe.utils import validate_email_address
	from frappe.utils.password import update_password

	validate_email_address(email, throw=True)

	created = False
	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
		if cint(user.enabled) == 0:
			user.enabled = 1
			user.save(ignore_permissions=True)
		if "Supplier" not in {r.role for r in user.roles}:
			user.add_roles("Supplier")
	else:
		parts = full_name.split(None, 1)
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": parts[0],
				"last_name": parts[1] if len(parts) > 1 else "",
				"send_welcome_email": 0,
				"user_type": "Website User",
			}
		)
		user.flags.ignore_permissions = True
		user.insert(ignore_permissions=True)
		user.add_roles("Supplier")
		created = True

	update_password(user.name, password)

	doc = frappe.get_doc("Supplier", supplier)
	already = any((row.user or "").lower() == email for row in (doc.portal_users or []))
	if not already:
		doc.append("portal_users", {"user": email})
		doc.flags.ignore_permissions = True
		doc.save(ignore_permissions=True)

	if cint(send_email):
		_send_portal_credentials_email(email, full_name, password, supplier)

	return {
		"ok": 1,
		"user": email,
		"created": created,
		"supplier": supplier,
		"portal_url": get_url("/supplier-invoice-portal"),
		"message": _("Portal user ready. Supplier can sign in at {0}.").format(
			get_url("/supplier-invoice-portal")
		),
	}


def _send_portal_credentials_email(email, full_name, password, supplier):
	try:
		portal_url = get_url("/supplier-invoice-portal")
		frappe.sendmail(
			recipients=[email],
			subject=_("Your NumeroUNO Supplier Invoice Portal login"),
			message=_(
				"<p>Hello {0},</p>"
				"<p>Your supplier invoice portal account for <b>{1}</b> is ready.</p>"
				"<p>Portal: <a href=\"{2}\">{2}</a><br>"
				"Email: <b>{3}</b><br>"
				"Temporary password: <b>{4}</b></p>"
				"<p>Please sign in and change your password after first login.</p>"
				"<p>— Numero Uno Training and Consulting LLC</p>"
			).format(full_name or email, supplier, portal_url, email, password),
			delayed=False,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Supplier portal credentials email failed")


def _require_supplier_session() -> str:
	"""Logged-in Website/Desk user linked to a Supplier, or throw."""
	if frappe.session.user in (None, "Guest"):
		frappe.throw(_("Please sign in to the Supplier Invoice Portal."), frappe.PermissionError)
	supplier = _supplier_for_user()
	if not supplier:
		frappe.throw(
			_("Your user is not linked to a Supplier. Contact NumeroUNO AP."),
			frappe.PermissionError,
		)
	return supplier


@frappe.whitelist(allow_guest=True)
def get_bootstrap():
	"""Portal shell. Guests get login-only payload; suppliers get full data."""
	portal = {
		"name": "NumeroUNO",
		"company_name": "Numero Uno Training and Consulting LLC",
		"tagline": "Supplier Portal",
		"site_name": "numerouno",
		"logo": "/assets/numerouno/images/numero-logo.png",
		"url": get_url("/supplier-invoice-portal"),
		"registration_url": get_url("/supplier-registration"),
	}

	if frappe.session.user in (None, "Guest"):
		return {
			"authenticated": False,
			"portal": portal,
			"message": _("Sign in with the credentials provided by NumeroUNO."),
		}

	supplier = _supplier_for_user()
	if not supplier:
		return {
			"authenticated": False,
			"portal": portal,
			"message": _(
				"Signed in as {0}, but this account is not linked to a Supplier. "
				"Ask NumeroUNO to add you under Supplier → Portal Users."
			).format(frappe.session.user),
			"user": frappe.session.user,
		}

	ensure_supplier_compliance_fields()
	supplier_doc = frappe.get_doc("Supplier", supplier)
	seed = {
		"authenticated": True,
		"demo_mode": False,
		"require_po": True,
		"portal": portal,
		"vendor": {
			"display_name": supplier_doc.supplier_name or supplier,
			"contact_name": get_fullname(frappe.session.user) or frappe.session.user,
			"vendor_id": supplier,
			"ap_email": "ap@nutc.cloud",
			"supplier": supplier,
		},
		"open_pos": _open_pos_for_supplier(supplier),
		"orders": [
			{
				"id": p["id"],
				"desc": p["label"],
				"issued": "",
				"value": p["amount"],
				"status": "Open",
			}
			for p in _open_pos_for_supplier(supplier)
		],
		"submissions": _submissions_for_supplier(supplier),
		"inventory": [],
		"compliance_docs": _compliance_docs_for_supplier(supplier),
		"compliance_gate": get_compliance_gate(supplier),
		"message_threads": [],
		"help_articles": _demo_seed()["help_articles"],
		"profile": {
			"email": frappe.session.user,
			"phone": getattr(supplier_doc, "mobile_no", None) or "",
			"address": "",
			"payment_method": "Bank transfer",
			"bank_account": "",
			"notify_email": True,
			"notify_status": True,
		},
	}
	return seed


@frappe.whitelist()
def get_compliance_status():
	"""Refresh compliance docs + invoice gate for the portal."""
	supplier = _require_supplier_session()
	return {
		"compliance_docs": _compliance_docs_for_supplier(supplier),
		"compliance_gate": get_compliance_gate(supplier),
		"demo_mode": False,
	}


@frappe.whitelist()
def submit_invoice(payload=None):
	"""Create a draft Purchase Invoice for the logged-in supplier."""
	if isinstance(payload, str):
		payload = json.loads(payload)
	payload = payload or {}

	supplier = _require_supplier_session()
	invoice_number = (payload.get("invoice_number") or "").strip()
	if not invoice_number:
		frappe.throw(_("Invoice number is required"))

	amount = flt(payload.get("amount"))
	if amount <= 0:
		frappe.throw(_("Total amount must be greater than zero"))

	invoice_date = getdate(payload.get("invoice_date") or nowdate())
	today = getdate(nowdate())
	earliest = add_days(today, -7)
	if invoice_date > today:
		frappe.throw(_("Future invoice dates are not allowed."))
	if invoice_date < earliest:
		frappe.throw(_("Invoice date cannot be more than 7 days in the past."))

	dn_number = (payload.get("dn_number") or "").strip()
	if not dn_number:
		frappe.throw(_("Delivery note number is required."))
	if (payload.get("dn_signed") or "").lower() != "yes":
		frappe.throw(_("Delivery notes must be signed by a Numero employee before submission."))
	dn_signed_date = payload.get("dn_signed_date")
	if not dn_signed_date:
		frappe.throw(_("Delivery note signed date is required."))
	if getdate(dn_signed_date) > today:
		frappe.throw(_("Delivery note signed date cannot be in the future."))
	if not (payload.get("dn_document_name") or "").strip():
		frappe.throw(_("Upload the signed delivery note document."))

	# Trade License + ICV must be on file and not expired (other docs do not block invoices)
	assert_supplier_can_invoice(supplier)

	company = frappe.defaults.get_global_default("company") or frappe.db.get_single_value(
		"Global Defaults", "default_company"
	)
	if not company:
		frappe.throw(_("Default company is not configured."))

	pi = frappe.new_doc("Purchase Invoice")
	pi.supplier = supplier
	pi.company = company
	pi.bill_no = invoice_number
	pi.bill_date = invoice_date
	pi.posting_date = invoice_date
	if payload.get("due_date"):
		pi.due_date = getdate(payload.get("due_date"))
	pi.currency = "AED"

	po_name = (payload.get("po") or "").strip()
	item_row = {"qty": 1, "rate": amount, "amount": amount}
	if po_name and frappe.db.exists("Purchase Order", po_name):
		po = frappe.get_doc("Purchase Order", po_name)
		if po.supplier != supplier:
			frappe.throw(_("This purchase order does not belong to your supplier account."))
		item_row["purchase_order"] = po_name
		if po.items:
			item_row["item_code"] = po.items[0].item_code
			item_row["description"] = po.items[0].item_name or po.items[0].description
	else:
		item_row["item_code"] = frappe.db.get_value("Item", {"is_stock_item": 0}, "name") or "Services"
		item_row["description"] = _("Supplier portal invoice") + f" {invoice_number}"

	pi.append("items", item_row)

	remarks = []
	if payload.get("note"):
		remarks.append(payload.get("note"))
	remarks.append(
		_("Delivery Note {0} · signed by Numero employee on {1} · file: {2}").format(
			dn_number,
			formatdate(getdate(dn_signed_date)),
			payload.get("dn_document_name") or "—",
		)
	)
	if payload.get("invoice_document_name"):
		remarks.append(_("Invoice file: {0}").format(payload.get("invoice_document_name")))
	pi.remarks = "\n".join(remarks)

	pi.flags.ignore_permissions = True
	pi.insert()
	frappe.db.commit()

	return {
		"status": "success",
		"reference": pi.name,
		"purchase_invoice": pi.name,
		"message": _("Invoice submitted to NumeroUNO AP for review."),
	}


COMPLIANCE_DOC_LABELS = {
	"trade_license": "Trade License",
	"tax_registration": "Tax Registration Certificate",
	"icv": "ICV Certificate",
	"iban_letter": "IBAN Letter",
	"additional": "Additional Documents",
}

COMPLIANCE_REQUIRES_VALIDITY = {"trade_license", "icv"}


@frappe.whitelist(methods=["POST"])
def upload_compliance_document():
	"""Upload a compliance attachment from the supplier portal (optional validity date)."""
	from frappe.utils.file_manager import save_file

	supplier = _require_supplier_session()
	doc_id = (frappe.form_dict.get("doc_id") or "").strip()
	valid_until = (frappe.form_dict.get("valid_until") or "").strip() or None

	if doc_id not in COMPLIANCE_DOC_LABELS:
		frappe.throw(_("Invalid compliance document type."))

	if doc_id in COMPLIANCE_REQUIRES_VALIDITY and not valid_until:
		frappe.throw(_("Validity date is required for {0}.").format(COMPLIANCE_DOC_LABELS[doc_id]))

	if valid_until:
		try:
			valid_until = getdate(valid_until)
		except Exception:
			frappe.throw(_("Validity date is not valid."))
		if valid_until < getdate(nowdate()):
			frappe.throw(_("Validity date cannot be in the past."))

	files = getattr(frappe.request, "files", None) or {}
	upload = files.get("file") or files.get("attachment")
	if not upload or not getattr(upload, "filename", None):
		frappe.throw(_("Please choose a file to upload."))

	content = upload.read()
	if not content:
		frappe.throw(_("Uploaded file is empty."))
	if len(content) > 10 * 1024 * 1024:
		frappe.throw(_("File must be smaller than 10 MB."))

	filename = upload.filename
	ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
	if ext and ext not in {".pdf", ".png", ".jpg", ".jpeg"}:
		frappe.throw(_("File must be PDF, PNG, or JPG."))

	file_doc = save_file(
		f"{doc_id}_{filename}",
		content,
		"Supplier",
		supplier,
		is_private=1,
	)

	label = COMPLIANCE_DOC_LABELS[doc_id]
	status = "Valid"
	meta = filename
	if valid_until:
		meta = f"{filename} · Valid until {formatdate(valid_until)}"
		days = date_diff(valid_until, nowdate())
		if days <= 30:
			status = "Expiring soon"
	elif doc_id == "additional":
		status = "On file"
		meta = f"{filename} uploaded"
	else:
		status = "On file"
		meta = f"{filename} uploaded"

	_persist_compliance_on_supplier(supplier, doc_id, file_doc.file_url, valid_until)
	frappe.get_doc("Supplier", supplier).add_comment(
		"Attachment",
		_("Compliance upload: {0} — {1}").format(label, meta),
	)

	frappe.db.commit()
	gate = get_compliance_gate(supplier)

	return {
		"status": "success",
		"doc_id": doc_id,
		"label": label,
		"file_name": filename,
		"file_url": file_doc.file_url,
		"valid_until": str(valid_until) if valid_until else "",
		"doc_status": status,
		"meta": meta,
		"compliance_gate": gate,
		"message": _("{0} uploaded successfully.").format(label),
	}
