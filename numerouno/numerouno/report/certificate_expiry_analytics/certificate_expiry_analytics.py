# Copyright (c) 2026, mohtashim and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, getdate, get_first_day


def execute(filters=None):
	filters = filters or {}
	today = getdate()

	if not filters.get("from_date"):
		filters["from_date"] = get_first_day(today)
	if not filters.get("to_date"):
		filters["to_date"] = today

	customer_field = None
	customer_fieldtype = "Data"
	if frappe.db.has_column("Assessment Result", "custom_customer"):
		customer_field = "custom_customer"
		customer_fieldtype = "Link"
	elif frappe.db.has_column("Assessment Result", "customer_name"):
		customer_field = "customer_name"
		customer_fieldtype = "Data"

	columns = [
		{"label": "Certificate", "fieldname": "name", "fieldtype": "Link", "options": "Assessment Result", "width": 180},
		{"label": "Student", "fieldname": "student", "fieldtype": "Link", "options": "Student", "width": 140},
		{"label": "Student Name", "fieldname": "student_name", "fieldtype": "Data", "width": 180},
		{"label": "Course", "fieldname": "course", "fieldtype": "Link", "options": "Course", "width": 160},
		{
			"label": "Customer",
			"fieldname": "customer",
			"fieldtype": customer_fieldtype,
			"options": "Customer" if customer_fieldtype == "Link" else None,
			"width": 160,
		},
		{"label": "Created On", "fieldname": "creation", "fieldtype": "Datetime", "width": 160},
		{"label": "Expiry Date", "fieldname": "expiry_date", "fieldtype": "Date", "width": 120},
		{"label": "Days Until Expiry", "fieldname": "days_until_expiry", "fieldtype": "Int", "width": 130},
		{"label": "Expiry Status", "fieldname": "expiry_status", "fieldtype": "Data", "width": 130},
	]

	conditions = []
	values = {}

	if filters.get("from_date"):
		conditions.append("ar.creation >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		# Make "to date" inclusive by using < next day
		conditions.append("ar.creation < %(to_date_exclusive)s")
		values["to_date_exclusive"] = add_days(filters["to_date"], 1)
	if filters.get("student"):
		conditions.append("ar.student = %(student)s")
		values["student"] = filters["student"]
	if filters.get("course"):
		conditions.append("ar.course = %(course)s")
		values["course"] = filters["course"]
	if customer_field and filters.get("customer"):
		conditions.append(f"ar.{customer_field} = %(customer)s")
		values["customer"] = filters["customer"]

	where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

	rows = frappe.db.sql(
		f"""
		SELECT
			ar.name,
			ar.student,
			ar.student_name,
			ar.course,
			{f"ar.{customer_field} as customer" if customer_field else "NULL as customer"},
			ar.creation
		FROM `tabAssessment Result` ar
		{where_clause}
		ORDER BY ar.creation DESC
		""",
		values=values,
		as_dict=True,
	)

	data = []
	status_counts = {"Expired": 0, "Expiring Soon": 0, "Valid": 0}

	for row in rows:
		creation_date = getdate(row.creation) if row.creation else today
		expiry_date = add_days(creation_date, 365)
		days_until_expiry = (expiry_date - today).days
		if days_until_expiry < 0:
			expiry_status = "Expired"
		elif days_until_expiry <= 30:
			expiry_status = "Expiring Soon"
		else:
			expiry_status = "Valid"

		if expiry_status in status_counts:
			status_counts[expiry_status] += 1

		row.update(
			{
				"expiry_date": expiry_date,
				"days_until_expiry": days_until_expiry,
				"expiry_status": expiry_status,
			}
		)
		data.append(row)

	chart = {
		"data": {
			"labels": list(status_counts.keys()),
			"datasets": [
				{"name": "Certificates", "values": list(status_counts.values())}
			],
		},
		"type": "donut",
	}

	return columns, data, None, chart
