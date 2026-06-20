# Copyright (c) 2026, mohtashim and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import date_diff, getdate


MAX_OPEN_DATE_RANGE_DAYS = 93


def execute(filters=None):
	filters = filters or {}
	_validate_date_range(filters)
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
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "customer_lpo",
			"label": _("Customer LPO"),
			"fieldtype": "Data",
			"width": 150,
		},
	]


def _validate_date_range(filters):
	if filters.get("customer") or filters.get("student_group"):
		return

	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	if not from_date or not to_date:
		return

	if date_diff(getdate(to_date), getdate(from_date)) > MAX_OPEN_DATE_RANGE_DAYS:
		frappe.throw(
			_(
				"Please narrow the date range to {0} days or less, or filter by Customer / Student Group."
			).format(MAX_OPEN_DATE_RANGE_DAYS)
		)


def _invoice_no_sql_without_join():
	return """
COALESCE(
	NULLIF(sgs.sales_invoice, ''),
	NULLIF(sgs.custom_sales_invoice, '')
)
""".strip()


def _invoice_status_sql_without_join():
	return """
CASE
	WHEN NULLIF(sgs.sales_invoice, '') IS NOT NULL THEN 'Invoiced'
	WHEN sgs.paid = 1 THEN 'Invoiced'
	WHEN sgs.custom_invoiced = 1 THEN 'Invoiced'
	ELSE 'Pending'
END
""".strip()


def get_data(filters):
	conditions = ["sgs.student_group != ''"]
	values = {}

	if filters.get("customer"):
		conditions.append("sgs.customer_name = %(customer)s")
		values["customer"] = filters.get("customer")

	if filters.get("student_group"):
		conditions.append("sgs.student_group = %(student_group)s")
		values["student_group"] = filters.get("student_group")

	if filters.get("from_date") and filters.get("to_date"):
		conditions.append("sgs.start_date BETWEEN %(from_date)s AND %(to_date)s")
		values["from_date"] = filters.get("from_date")
		values["to_date"] = filters.get("to_date")

	where_clause = " AND ".join(conditions)

	rows = frappe.db.sql(
		f"""
		SELECT
			sgs.student_group AS attendance,
			sgs.customer_name AS customer,
			sgs.sales_person AS sales_person,
			sgs.course_name AS course_name,
			DATE(sg.creation) AS course_creation_date,
			GROUP_CONCAT(DISTINCT sgi.instructor_name ORDER BY sgi.idx SEPARATOR ', ') AS instructor_name,
			sgs.student AS student_name,
			sgs.start_date AS from_date,
			{_invoice_no_sql_without_join()} AS invoice_no,
			sgs.customer_purchase_order AS customer_lpo,
			{_invoice_status_sql_without_join()} AS invoice_status,
			sgs.student AS _student_id,
			sgs.student_group AS _student_group_id
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

	_enrich_draft_invoice_rows(rows)

	for row in rows:
		row.pop("_student_id", None)
		row.pop("_student_group_id", None)

	return rows


def _enrich_draft_invoice_rows(rows):
	"""Look up draft invoices only for rows still marked Pending without an invoice number."""
	pending_pairs = {
		(row.get("_student_id"), row.get("_student_group_id"))
		for row in rows
		if row.get("invoice_status") == "Pending" and not row.get("invoice_no")
		and row.get("_student_id") and row.get("_student_group_id")
	}
	if not pending_pairs:
		return

	draft_map = {}
	pair_list = list(pending_pairs)
	batch_size = 500
	for start in range(0, len(pair_list), batch_size):
		batch = pair_list[start : start + batch_size]
		placeholders = ", ".join(["(%s, %s)"] * len(batch))
		flat_values = [value for pair in batch for value in pair]
		batch_rows = frappe.db.sql(
			f"""
			SELECT
				sis.student,
				sis.student_group,
				SUBSTRING_INDEX(
					GROUP_CONCAT(si.name ORDER BY si.posting_date DESC, si.creation DESC),
					',',
					1
				) AS draft_invoice_no
			FROM `tabSales Invoice Student` sis
			INNER JOIN `tabSales Invoice` si
				ON si.name = sis.parent
				AND si.docstatus = 0
			WHERE (sis.student, sis.student_group) IN ({placeholders})
			GROUP BY sis.student, sis.student_group
			""",
			flat_values,
			as_dict=True,
		)
		for item in batch_rows:
			if item.draft_invoice_no:
				draft_map[(item.student, item.student_group)] = item.draft_invoice_no

	for row in rows:
		if row.get("invoice_status") != "Pending" or row.get("invoice_no"):
			continue
		draft_invoice = draft_map.get((row.get("_student_id"), row.get("_student_group_id")))
		if draft_invoice:
			row["invoice_no"] = draft_invoice
			row["invoice_status"] = "In Process"
