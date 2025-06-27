# Copyright (c) 2025, mohtashim and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"label": "Sales Order", "fieldname": "name", "fieldtype": "Link", "options": "Sales Order", "width": 180},
		{"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 220},
		{"label": "Customer Name", "fieldname": "customer_name", "fieldtype": "Data", "width": 180},
		{"label": "Transaction Date", "fieldname": "transaction_date", "fieldtype": "Date", "width": 120},
		{"label": "Owner", "fieldname": "owner", "fieldtype": "Data", "width": 180},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 150},
	]

	so_filters = {"po_no": ["is", "not set"], "docstatus": ["<", 2]}
	if filters.get("customer"):
		so_filters["customer"] = filters["customer"]
	if filters.get("from_date"):
		so_filters["transaction_date"] = [">=", filters["from_date"]]
	if filters.get("to_date"):
		if "transaction_date" in so_filters:
			# If from_date already set, make it a range
			so_filters["transaction_date"] = ["between", [filters["from_date"], filters["to_date"]]]
		else:
			so_filters["transaction_date"] = ["<=", filters["to_date"]]

	data = frappe.db.get_all(
		"Sales Order",
		filters=so_filters,
		fields=["name", "customer", "customer_name", "transaction_date", "owner", "status"],
		order_by="transaction_date desc"
	)

	# Summary
	total_missing = len(data)
	summary = f"<b>Total Sales Orders missing PO Number: {total_missing}</b>"
	if filters.get("customer"):
		summary += f"<br>Customer: {filters['customer']}"
	if filters.get("from_date"):
		summary += f"<br>From: {filters['from_date']}"
	if filters.get("to_date"):
		summary += f"<br>To: {filters['to_date']}"

	# Donut chart by status
	status_count = {}
	for d in data:
		status = d["status"] or "Unknown"
		status_count[status] = status_count.get(status, 0) + 1
	chart = {
		"data": {
			"labels": list(status_count.keys()),
			"datasets": [{"name": "Count", "values": list(status_count.values())}]
		},
		"type": "donut",
		"height": 200
	}

	return columns, data, summary, chart
