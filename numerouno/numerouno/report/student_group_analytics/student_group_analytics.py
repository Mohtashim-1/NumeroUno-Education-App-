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
			"label": _("Student Group"),
			"fieldname": "student_group",
			"fieldtype": "Link",
			"options": "Student Group",
			"width": 170,
		},
		{
			"label": _("Course"),
			"fieldname": "course",
			"fieldtype": "Link",
			"options": "Course",
			"width": 220,
		},
		{
			"label": _("Course Creation Date"),
			"fieldname": "course_creation_date",
			"fieldtype": "Date",
			"width": 140,
		},
		{
			"label": _("Name of Instructor"),
			"fieldname": "instructor_name",
			"fieldtype": "Data",
			"width": 220,
		},
		{
			"label": _("From Date"),
			"fieldname": "from_date",
			"fieldtype": "Date",
			"width": 120,
		},
		{
			"label": _("To Date"),
			"fieldname": "to_date",
			"fieldtype": "Date",
			"width": 120,
		},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 180,
		},
		{
			"label": _("Students"),
			"fieldname": "student_count",
			"fieldtype": "Int",
			"width": 90,
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 120,
		},
	]


def get_data(filters):
	conditions = ["sg.disabled = 0"]
	values = {}

	if filters.get("student_group"):
		conditions.append("sg.name = %(student_group)s")
		values["student_group"] = filters.get("student_group")

	if filters.get("course"):
		conditions.append("sg.course = %(course)s")
		values["course"] = filters.get("course")

	if filters.get("customer"):
		conditions.append("sg.custom_customer = %(customer)s")
		values["customer"] = filters.get("customer")

	if filters.get("instructor"):
		conditions.append("sgi.instructor = %(instructor)s")
		values["instructor"] = filters.get("instructor")

	if filters.get("from_date"):
		conditions.append("DATE(sg.creation) >= %(from_date)s")
		values["from_date"] = filters.get("from_date")

	if filters.get("to_date"):
		conditions.append("DATE(sg.creation) <= %(to_date)s")
		values["to_date"] = filters.get("to_date")

	where_clause = " AND ".join(conditions)

	return frappe.db.sql(
		f"""
		SELECT
			sg.name AS student_group,
			sg.course AS course,
			DATE(sg.creation) AS course_creation_date,
			GROUP_CONCAT(DISTINCT sgi.instructor_name ORDER BY sgi.idx SEPARATOR ', ') AS instructor_name,
			sg.from_date AS from_date,
			sg.to_date AS to_date,
			sg.custom_customer AS customer,
			COUNT(DISTINCT sgs.name) AS student_count,
			CASE
				WHEN sg.disabled = 1 THEN 'Disabled'
				WHEN sg.to_date IS NOT NULL AND sg.to_date < CURDATE() THEN 'Completed'
				WHEN sg.from_date IS NOT NULL AND sg.from_date > CURDATE() THEN 'Upcoming'
				ELSE 'Ongoing'
			END AS status
		FROM `tabStudent Group` AS sg
		LEFT JOIN `tabStudent Group Student` AS sgs
			ON sgs.parent = sg.name
			AND sgs.parenttype = 'Student Group'
			AND sgs.parentfield = 'students'
		LEFT JOIN `tabStudent Group Instructor` AS sgi
			ON sgi.parent = sg.name
			AND sgi.parenttype = 'Student Group'
			AND sgi.parentfield = 'instructors'
		WHERE {where_clause}
		GROUP BY sg.name
		ORDER BY sg.creation DESC
		""",
		values,
		as_dict=True,
	)
