# Copyright (c) 2026, mohtashim and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"fieldname": "attendance",
			"label": _("Attendence Ref No"),
			"fieldtype": "Link",
			"options": "Student Group",
			"width": 150,
		},
		{
			"fieldname": "customer",
			"label": _("Customer Name"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 200,
		},
		{
			"fieldname": "sales_person",
			"label": _("Sales Person"),
			"fieldtype": "Link",
			"options": "Sales Person",
			"width": 150,
		},
		{
			"fieldname": "course_name",
			"label": _("Course Name"),
			"fieldtype": "Link",
			"options": "Course",
			"width": 150,
		},
		{
			"fieldname": "course_creation_date",
			"label": _("Course Creation Date"),
			"fieldtype": "Date",
			"width": 150,
		},
		{
			"fieldname": "instructor_name",
			"label": _("Name of Instructor"),
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"fieldname": "student_name",
			"label": _("Student Name"),
			"fieldtype": "Link",
			"options": "Student",
			"width": 150,
		},
		{
			"fieldname": "from_date",
			"label": _("Course Date"),
			"fieldtype": "Date",
			"width": 150,
		},
		{
			"fieldname": "invoice_status",
			"label": _("Invoice Status"),
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "invoice_no",
			"label": _("Invoice No"),
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 150,
		},
		{
			"fieldname": "customer_lpo",
			"label": _("Customer LPO"),
			"fieldtype": "Data",
			"width": 150,
		},
	]


def get_data(filters):
	conditions = ["sgs.student_group != ''"]
	values = {}

	if filters.get("student_group"):
		conditions.append("sgs.student_group = %(student_group)s")
		values["student_group"] = filters.get("student_group")

	if filters.get("customer"):
		conditions.append("sgs.customer_name = %(customer)s")
		values["customer"] = filters.get("customer")

	if filters.get("from_date") and filters.get("to_date"):
		conditions.append("sgs.start_date BETWEEN %(from_date)s AND %(to_date)s")
		values["from_date"] = filters.get("from_date")
		values["to_date"] = filters.get("to_date")

	where_clause = " AND ".join(conditions)

	return frappe.db.sql(
		f"""
		SELECT
			sgs.student_group AS attendance,
			sgs.customer_name AS customer,
			sgs.sales_person AS sales_person,
			sgs.course_name AS course_name,
			DATE(sg.creation) AS course_creation_date,
			GROUP_CONCAT(DISTINCT sgi.instructor_name ORDER BY sgi.idx SEPARATOR ', ') AS instructor_name,
			sgs.student_name AS student_name,
			sgs.start_date AS from_date,
			sgs.sales_invoice AS invoice_no,
			sgs.customer_purchase_order AS customer_lpo,
			CASE WHEN sgs.paid = 1 THEN 'Invoiced' ELSE 'Pending' END AS invoice_status
		FROM `tabStudent Group Student` AS sgs
		LEFT JOIN `tabStudent Group` AS sg
			ON sg.name = sgs.student_group
		LEFT JOIN `tabStudent Group Instructor` AS sgi
			ON sgi.parent = sgs.student_group
			AND sgi.parenttype = 'Student Group'
			AND sgi.parentfield = 'instructors'
		WHERE {where_clause}
		GROUP BY sgs.name
		ORDER BY sgs.start_date DESC, sgs.student_group DESC
		""",
		values,
		as_dict=True,
	)
