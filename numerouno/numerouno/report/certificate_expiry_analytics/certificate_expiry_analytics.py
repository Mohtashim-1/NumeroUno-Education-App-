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
		{"label": "Certificate Validity Date", "fieldname": "expiry_date", "fieldtype": "Date", "width": 160},
		{"label": "Days Until Expiry", "fieldname": "days_until_expiry", "fieldtype": "Int", "width": 130},
		{"label": "Expiry Status", "fieldname": "expiry_status", "fieldtype": "Data", "width": 130},
	]

	conditions = []
	values = {}

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
			ar.creation,
			ar.certificate_validity_date,
			ar.validity_period,
			ar.course_start_date
		FROM `tabAssessment Result` ar
		{where_clause}
		ORDER BY ar.creation DESC
		""",
		values=values,
		as_dict=True,
	)

	data = []
	status_counts = {"Expired": 0, "Expiring Soon": 0, "Valid": 0, "Missing Validity Date": 0}

	from_date = getdate(filters.get("from_date")) if filters.get("from_date") else None
	to_date = getdate(filters.get("to_date")) if filters.get("to_date") else None

	for row in rows:
		expiry_date = None
		if row.certificate_validity_date:
			expiry_date = getdate(row.certificate_validity_date)
		elif row.validity_period and row.validity_period != "NA" and row.course_start_date:
			try:
				expiry_date = add_days(getdate(row.course_start_date), int(row.validity_period))
			except Exception:
				expiry_date = None

		if expiry_date and from_date and expiry_date < from_date:
			continue
		if expiry_date and to_date and expiry_date > to_date:
			continue
		if not expiry_date and (from_date or to_date):
			continue

		if expiry_date:
			days_until_expiry = (expiry_date - today).days
			if days_until_expiry < 0:
				expiry_status = "Expired"
			elif days_until_expiry <= 30:
				expiry_status = "Expiring Soon"
			else:
				expiry_status = "Valid"
		else:
			days_until_expiry = None
			expiry_status = "Missing Validity Date"

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
