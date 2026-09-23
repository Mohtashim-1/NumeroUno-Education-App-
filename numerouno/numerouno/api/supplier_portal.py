# Copyright (c) 2026, NumeroUNO and contributors
# License: MIT

"""Supplier Invoice Portal — bootstrap data and invoice submission."""

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import flt, formatdate, get_url, getdate, nowdate


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
			{"id": "PO-100251", "label": "PO-100251 · Machined brackets · $22,400.00", "amount": 22400},
			{"id": "PO-100248", "label": "PO-100248 · Hydraulic fittings · $8,915.00", "amount": 8915},
			{"id": "PO-100245", "label": "PO-100245 · Steel sheet stock · $18,420.50", "amount": 18420.5},
		],
		"orders": [
			{"id": "PO-100251", "desc": "Machined brackets, 6061-T6 (400 pcs)", "issued": "Sep 15, 2026", "value": 22400, "status": "Open"},
			{"id": "PO-100248", "desc": "Hydraulic fittings, assorted", "issued": "Sep 09, 2026", "value": 8915, "status": "Open"},
			{"id": "PO-100245", "desc": "Steel sheet stock, 12 ga", "issued": "Aug 28, 2026", "value": 18420.5, "status": "Invoiced"},
		],
		"submissions": [
			{"num": "INV-2026-0412", "po": "PO-100245", "date": "Sep 18, 2026", "due": "Oct 18, 2026", "amount": 18420.5, "currency": "USD", "status": "Pending review"},
			{"num": "INV-2026-0397", "po": "PO-100243", "date": "Sep 02, 2026", "due": "Oct 02, 2026", "amount": 6210, "currency": "USD", "status": "Approved"},
			{"num": "INV-2026-0381", "po": "PO-100231", "date": "Aug 21, 2026", "due": "Sep 20, 2026", "amount": 2875.75, "currency": "USD", "status": "Needs info"},
		],
		"inventory": [
			{"sku": "AC-BRK-0612", "name": "Machined bracket, 6\"", "loc": "Dayton DC", "qty": 1240, "reorder": 500},
			{"sku": "AC-FIT-3308", "name": "Hydraulic elbow fitting", "loc": "Dayton DC", "qty": 310, "reorder": 400},
			{"sku": "AC-SHT-12GA", "name": "Steel sheet, 12 ga 4×8", "loc": "Columbus", "qty": 86, "reorder": 60},
			{"sku": "AC-FST-M8Z", "name": "M8 fastener kit", "loc": "Columbus", "qty": 0, "reorder": 200},
			{"sku": "AC-FRM-2200", "name": "Welded frame assembly", "loc": "Dayton DC", "qty": 42, "reorder": 20},
		],
		"compliance_docs": [
			{"id": "w9", "name": "W-9 Tax Form", "meta": "On file since Jan 2024", "status": "Valid"},
			{"id": "coi", "name": "Certificate of Insurance", "meta": "Expires Oct 05, 2026", "status": "Expiring soon"},
			{"id": "iso", "name": "ISO 9001:2015 Certificate", "meta": "Expires Mar 2028", "status": "Valid"},
			{"id": "cmr", "name": "Conflict Minerals Report (CMRT)", "meta": "Annual filing due Aug 31, 2026", "status": "Overdue"},
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
				"subject": "Certificate of insurance renewal",
				"when": "Sep 10",
				"unread": True,
				"msgs": [
					{
						"me": False,
						"text": "Your COI expires Oct 5. Please upload the renewed certificate under Compliance to avoid a payment hold.",
						"meta": "Compliance Team · Sep 10, 9:00 AM",
					}
				],
			},
		],
		"help_articles": [
			{
				"title": "How do I submit an invoice?",
				"body": "Go to Submit Invoice, upload your PDF, select the PO, enter dates and amount, then complete payment details and review.",
			},
			{
				"title": "What is 3-way match?",
				"body": "AP compares your invoice to the purchase order and goods receipt. Line totals must align before approval.",
			},
			{
				"title": "When will I get paid?",
				"body": "Approved invoices pay per your terms (e.g. Net 30) from the approval date. Track status under Past Submissions.",
			},
			{
				"title": "Why was my invoice returned?",
				"body": "Common reasons: missing PO, wrong amount, or unclear line items. Check Messages for AP notes.",
			},
		],
		"profile": {
			"email": "jessica.chen@acmemfg.com",
			"phone": "+1 (937) 555-0142",
			"address": "1200 Industrial Pkwy, Dayton, OH 45404",
			"payment_method": "ACH",
			"bank_account": "Chase Business ····4417",
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
		out.append({"id": po.name, "label": label, "amount": flt(po.grand_total), "currency": po.currency or "USD"})
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
				"currency": inv.currency or "USD",
				"status": st,
				"pi_name": inv.name,
			}
		)
	return out


@frappe.whitelist(allow_guest=True)
def get_bootstrap():
	"""Portal shell: vendor context, open POs, recent supplier invoices."""
	seed = _demo_seed()
	supplier = _supplier_for_user()
	if supplier:
		supplier_doc = frappe.get_doc("Supplier", supplier)
		seed["vendor"] = {
			"display_name": supplier_doc.supplier_name or supplier,
			"contact_name": frappe.session.user_fullname or frappe.session.user,
			"vendor_id": supplier,
			"ap_email": seed["vendor"]["ap_email"],
			"supplier": supplier,
		}
		open_pos = _open_pos_for_supplier(supplier)
		if open_pos:
			seed["open_pos"] = open_pos
		subs = _submissions_for_supplier(supplier)
		if subs:
			seed["submissions"] = subs
	seed["require_po"] = True
	seed["demo_mode"] = not bool(supplier)
	seed["portal"] = {
		"name": "NUMEROUNO",
		"tagline": "SUPPLIER PORTAL",
		"site_name": "numerouno",
		"url": get_url("/supplier-invoice-portal"),
	}
	return seed


@frappe.whitelist(allow_guest=True)
def submit_invoice(payload=None):
	"""Create a draft Purchase Invoice for the logged-in supplier (or demo ack)."""
	if isinstance(payload, str):
		payload = json.loads(payload)
	payload = payload or {}

	supplier = _supplier_for_user()
	invoice_number = (payload.get("invoice_number") or "").strip()
	if not invoice_number:
		frappe.throw(_("Invoice number is required"))

	amount = flt(payload.get("amount"))
	if amount <= 0:
		frappe.throw(_("Total amount must be greater than zero"))

	if not supplier:
		from frappe.utils import random_string

		ref = "VS-" + random_string(6).upper()
		return {
			"status": "demo",
			"reference": ref,
			"message": _("Invoice recorded in demo mode. Sign in as a linked Supplier user to create ERP documents."),
		}

	company = frappe.defaults.get_global_default("company") or frappe.db.get_single_value(
		"Global Defaults", "default_company"
	)
	if not company:
		frappe.throw(_("Default company is not configured."))

	pi = frappe.new_doc("Purchase Invoice")
	pi.supplier = supplier
	pi.company = company
	pi.bill_no = invoice_number
	pi.bill_date = getdate(payload.get("invoice_date") or nowdate())
	pi.posting_date = pi.bill_date
	if payload.get("due_date"):
		pi.due_date = getdate(payload.get("due_date"))
	pi.currency = payload.get("currency") or frappe.db.get_value("Supplier", supplier, "default_currency") or "USD"

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
	if payload.get("note"):
		pi.remarks = payload.get("note")

	pi.flags.ignore_permissions = True
	pi.insert()
	frappe.db.commit()

	return {
		"status": "success",
		"reference": pi.name,
		"purchase_invoice": pi.name,
		"message": _("Invoice submitted for AP review."),
	}
