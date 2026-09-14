import json

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime

PRINT_FORMAT = "Sales Invoice NUTC"


def _filters_sql(filters):
	conditions = ["si.docstatus = 1"]
	values = {}

	if filters.get("customer"):
		conditions.append("si.customer = %(customer)s")
		values["customer"] = filters.get("customer")

	if filters.get("from_date"):
		conditions.append("si.posting_date >= %(from_date)s")
		values["from_date"] = getdate(filters.get("from_date"))

	if filters.get("to_date"):
		conditions.append("si.posting_date <= %(to_date)s")
		values["to_date"] = getdate(filters.get("to_date"))

	if filters.get("search"):
		conditions.append("(si.name LIKE %(search)s OR si.customer_name LIKE %(search)s)")
		values["search"] = f"%{filters.get('search').strip()}%"

	view = (filters.get("view") or "needs_print").strip()
	if view == "needs_print":
		conditions.append("(sit.name IS NULL OR IFNULL(sit.printed, 0) = 0)")
	elif view == "done":
		conditions.append("IFNULL(sit.printed, 0) = 1")

	return " AND ".join(conditions), values


@frappe.whitelist()
def get_invoices(filters=None):
	filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else (filters or {}))
	where, values = _filters_sql(filters)

	rows = frappe.db.sql(
		f"""
		SELECT
			si.name AS invoice_number,
			si.customer,
			si.customer_name,
			si.posting_date AS invoice_date,
			si.grand_total,
			si.currency,
			sit.name AS tracking_name,
			IFNULL(sit.printed, 0) AS printed,
			sit.printed_on,
			sit.printed_by,
			IFNULL(sit.email_sent, 0) AS email_sent,
			IFNULL(sit.original_sent, 0) AS original_sent,
			sit.remarks
		FROM `tabSales Invoice` si
		LEFT JOIN `tabSales Invoice Tracking` sit
			ON sit.invoice_number = si.name
			AND sit.docstatus < 2
		WHERE {where}
		ORDER BY si.posting_date DESC, si.name DESC
		LIMIT 500
		""",
		values,
		as_dict=True,
	)

	needs = sum(1 for r in rows if not r.printed)
	return {
		"rows": rows,
		"count": len(rows),
		"needs_print_in_result": needs,
		"print_format": PRINT_FORMAT,
	}


def _get_or_create_tracking(invoice_number: str):
	name = frappe.db.get_value(
		"Sales Invoice Tracking",
		{"invoice_number": invoice_number, "docstatus": ("<", 2)},
		"name",
	)
	if name:
		return frappe.get_doc("Sales Invoice Tracking", name)

	doc = frappe.new_doc("Sales Invoice Tracking")
	doc.invoice_number = invoice_number
	doc.insert(ignore_permissions=True)
	return doc


@frappe.whitelist()
def save_tracking_rows(rows=None):
	"""Bulk save email/original flags from the workbench."""
	rows = json.loads(rows) if isinstance(rows, str) else (rows or [])
	updated = 0
	for row in rows:
		invoice = (row.get("invoice_number") or "").strip()
		if not invoice:
			continue
		doc = _get_or_create_tracking(invoice)
		doc.email_sent = 1 if row.get("email_sent") else 0
		doc.original_sent = 1 if row.get("original_sent") else 0
		if row.get("remarks") is not None:
			doc.remarks = row.get("remarks") or ""
		if row.get("printed"):
			doc.printed = 1
			if not doc.printed_on:
				doc.printed_on = now_datetime()
				doc.printed_by = frappe.session.user
		doc.save(ignore_permissions=True)
		updated += 1
	frappe.db.commit()
	return {"updated": updated}


@frappe.whitelist()
def mark_printed(invoice_numbers=None, open_print=0):
	invoices = json.loads(invoice_numbers) if isinstance(invoice_numbers, str) else invoice_numbers
	if not invoices:
		frappe.throw(_("Select at least one invoice."))

	marked = []
	for invoice in invoices:
		invoice = (invoice or "").strip()
		if not invoice:
			continue
		doc = _get_or_create_tracking(invoice)
		doc.printed = 1
		doc.printed_on = now_datetime()
		doc.printed_by = frappe.session.user
		doc.save(ignore_permissions=True)
		marked.append(invoice)

	frappe.db.commit()
	return {
		"marked": marked,
		"print_format": PRINT_FORMAT,
		"open_print": int(open_print or 0),
	}
