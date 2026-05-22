# Copyright (c) 2026, mohtashim and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from numerouno.numerouno.utils.student_invoice_sync import (
	INVOICE_NO_SQL,
	INVOICE_STATUS_SQL,
)


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


def _build_invoice_join_sql(has_date_filter):
	# When a date range is set, restrict the invoice subquery to only the
	# student+group pairs that fall in that range — avoids a full table scan
	# of tabSales Invoice Student (~150K+ rows) on every report run.
	date_scope = (
		"AND sis.student_group IN ("
		"  SELECT DISTINCT student_group FROM `tabStudent Group Student`"
		"  WHERE start_date BETWEEN %(from_date)s AND %(to_date)s"
		")"
		if has_date_filter
		else ""
	)
	return f"""
LEFT JOIN (
	SELECT
		sis.student,
		sis.student_group,
		SUBSTRING_INDEX(
			GROUP_CONCAT(si.name ORDER BY si.posting_date DESC, si.creation DESC),
			',',
			1
		) AS invoice_no
	FROM `tabSales Invoice Student` sis
	INNER JOIN `tabSales Invoice` si
		ON si.name = sis.parent
		AND si.docstatus = 1
	WHERE sis.student IS NOT NULL
		AND sis.student_group IS NOT NULL
		AND sis.student_group != ''
		{date_scope}
	GROUP BY sis.student, sis.student_group
) AS inv
	ON inv.student = sgs.student
	AND inv.student_group = sgs.student_group
"""


def get_data(filters):
	conditions = ["sgs.student_group != ''"]
	values = {}

	if filters.get("customer"):
		conditions.append("sgs.customer_name = %(customer)s")
		values["customer"] = filters.get("customer")

	if filters.get("student_group"):
		conditions.append("sgs.student_group = %(student_group)s")
		values["student_group"] = filters.get("student_group")

	has_date_filter = bool(filters.get("from_date") and filters.get("to_date"))
	if has_date_filter:
		conditions.append("sgs.start_date BETWEEN %(from_date)s AND %(to_date)s")
		values["from_date"] = filters.get("from_date")
		values["to_date"] = filters.get("to_date")

	where_clause = " AND ".join(conditions)
	invoice_join_sql = _build_invoice_join_sql(has_date_filter)

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
			{INVOICE_NO_SQL} AS invoice_no,
			sgs.customer_purchase_order AS customer_lpo,
			{INVOICE_STATUS_SQL} AS invoice_status
		FROM `tabStudent Group Student` AS sgs
		{invoice_join_sql}
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
