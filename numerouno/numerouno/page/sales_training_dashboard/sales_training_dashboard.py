import json
from datetime import timedelta

import frappe
from frappe.utils import add_days, flt, getdate, nowdate


def _normalize_filters(filters=None):
	filters = json.loads(filters) if isinstance(filters, str) else (filters or {})
	to_date = getdate(filters.get("to_date") or nowdate())
	from_date = getdate(filters.get("from_date") or add_days(to_date, -29))

	if from_date > to_date:
		from_date, to_date = to_date, from_date

	return frappe._dict(
		{
			"from_date": from_date,
			"to_date": to_date,
			"customer": filters.get("customer"),
			"course": filters.get("course"),
			"program": filters.get("program"),
		}
	)


def _sales_invoice_conditions(filters):
	conditions = ["si.docstatus = 1", "si.posting_date BETWEEN %(from_date)s AND %(to_date)s"]
	values = {"from_date": filters.from_date, "to_date": filters.to_date}

	if filters.customer:
		conditions.append("si.customer = %(customer)s")
		values["customer"] = filters.customer

	if filters.course:
		conditions.append(
			"""
			EXISTS (
				SELECT 1
				FROM `tabSales Invoice Student` sis
				WHERE sis.parent = si.name
					AND sis.course = %(course)s
			)
			"""
		)
		values["course"] = filters.course

	return conditions, values


def _student_group_conditions(filters, date_field="COALESCE(sgs.start_date, sg.from_date)"):
	conditions = [
		"sg.docstatus < 2",
		"sgs.student IS NOT NULL",
		f"{date_field} BETWEEN %(from_date)s AND %(to_date)s",
	]
	values = {"from_date": filters.from_date, "to_date": filters.to_date}

	if filters.customer:
		conditions.append("COALESCE(sgs.customer_name, sg.custom_customer) = %(customer)s")
		values["customer"] = filters.customer

	if filters.course:
		conditions.append("sg.course = %(course)s")
		values["course"] = filters.course

	if filters.program:
		conditions.append("sg.program = %(program)s")
		values["program"] = filters.program

	return conditions, values


def _pending_condition():
	return """
		NOT EXISTS (
			SELECT 1
			FROM `tabSales Invoice Student` sis
			INNER JOIN `tabSales Invoice` si
				ON si.name = sis.parent
				AND si.docstatus IN (0, 1)
			WHERE sis.student = sgs.student
				AND sis.student_group = sgs.student_group
		)
		AND (sgs.paid = 0 OR sgs.paid IS NULL)
		AND (sgs.custom_invoiced = 0 OR sgs.custom_invoiced IS NULL)
	"""


def _total_sales(filters):
	conditions, values = _sales_invoice_conditions(filters)
	row = frappe.db.sql(
		f"""
		SELECT
			SUM(si.base_grand_total) AS total_sales,
			SUM(si.total_qty) AS sales_volume
		FROM `tabSales Invoice` si
		WHERE {' AND '.join(conditions)}
		""",
		values,
		as_dict=True,
	)[0]

	return {
		"total_sales": flt(row.total_sales, 2),
		"sales_volume": flt(row.sales_volume, 0),
	}


def _training_summary(filters):
	conditions, values = _student_group_conditions(filters)
	row = frappe.db.sql(
		f"""
		SELECT
			COUNT(DISTINCT sg.name) AS groups_count,
			COUNT(sgs.name) AS candidates_count,
			COUNT(DISTINCT sgs.student) AS unique_candidates
		FROM `tabStudent Group` sg
		INNER JOIN `tabStudent Group Student` sgs
			ON sgs.parent = sg.name
			AND sgs.parentfield = 'students'
		WHERE {' AND '.join(conditions)}
		""",
		values,
		as_dict=True,
	)[0]

	return {
		"groups_count": row.groups_count or 0,
		"candidates_count": row.candidates_count or 0,
		"unique_candidates": row.unique_candidates or 0,
	}


def _candidate_invoice_values():
	return frappe.db.sql(
		"""
		SELECT
			COALESCE(sg.custom_customer, si.customer, 'No Customer') AS customer,
			COALESCE(sg.course, 'No Course') AS course,
			AVG(si.base_grand_total / invoice_candidates.candidate_count) AS avg_candidate_value
		FROM `tabSales Invoice` si
		INNER JOIN (
			SELECT parent, COUNT(*) AS candidate_count
			FROM `tabSales Invoice Student`
			WHERE student IS NOT NULL
				AND student_group IS NOT NULL
				AND student_group != ''
			GROUP BY parent
		) invoice_candidates
			ON invoice_candidates.parent = si.name
		INNER JOIN `tabSales Invoice Student` sis
			ON sis.parent = si.name
		LEFT JOIN `tabStudent Group` sg
			ON sg.name = sis.student_group
		WHERE si.docstatus = 1
			AND si.base_grand_total IS NOT NULL
			AND invoice_candidates.candidate_count > 0
		GROUP BY customer, course
		""",
		as_dict=True,
	)


def _pending_candidates(filters):
	conditions, values = _student_group_conditions(filters)
	pending_condition = _pending_condition()
	return frappe.db.sql(
		f"""
		SELECT
			COALESCE(sgs.customer_name, sg.custom_customer, 'No Customer') AS customer,
			COALESCE(sg.course, 'No Course') AS course,
			COUNT(sgs.name) AS pending_candidates
		FROM `tabStudent Group` sg
		INNER JOIN `tabStudent Group Student` sgs
			ON sgs.parent = sg.name
			AND sgs.parentfield = 'students'
		WHERE {' AND '.join(conditions)}
			AND {pending_condition}
		GROUP BY customer, course
		ORDER BY pending_candidates DESC, customer, course
		""",
		values,
		as_dict=True,
	)


def _pending_invoice_summary(filters):
	pending_rows = _pending_candidates(filters)
	value_rows = _candidate_invoice_values()
	value_by_customer_course = {
		(row.customer, row.course): flt(row.avg_candidate_value, 2) for row in value_rows
	}
	value_by_course = {}
	all_values = []

	for row in value_rows:
		value = flt(row.avg_candidate_value, 2)
		value_by_course.setdefault(row.course, []).append(value)
		all_values.append(value)

	for course, values in value_by_course.items():
		value_by_course[course] = flt(sum(values) / len(values), 2)

	default_value = flt(sum(all_values) / len(all_values), 2) if all_values else 0

	total_pending = 0
	tentative_value = 0
	breakdown = []

	for row in pending_rows:
		pending = row.pending_candidates or 0
		avg_value = (
			value_by_customer_course.get((row.customer, row.course))
			or value_by_course.get(row.course)
			or default_value
		)
		row_value = flt(pending * avg_value, 2)
		total_pending += pending
		tentative_value += row_value
		breakdown.append(
			{
				"customer": row.customer,
				"course": row.course,
				"pending_candidates": pending,
				"avg_candidate_value": flt(avg_value, 2),
				"tentative_value": row_value,
			}
		)

	return {
		"pending_candidates": total_pending,
		"tentative_value": flt(tentative_value, 2),
		"avg_candidate_value": flt(tentative_value / total_pending, 2) if total_pending else default_value,
		"breakdown": breakdown[:10],
	}


def _course_breakdown(filters):
	conditions, values = _student_group_conditions(filters)
	return frappe.db.sql(
		f"""
		SELECT
			COALESCE(sg.course, 'No Course') AS course,
			COUNT(sgs.name) AS candidates
		FROM `tabStudent Group` sg
		INNER JOIN `tabStudent Group Student` sgs
			ON sgs.parent = sg.name
			AND sgs.parentfield = 'students'
		WHERE {' AND '.join(conditions)}
		GROUP BY course
		ORDER BY candidates DESC, course
		LIMIT 8
		""",
		values,
		as_dict=True,
	)


def _sales_by_customer(filters):
	conditions, values = _sales_invoice_conditions(filters)
	return frappe.db.sql(
		f"""
		SELECT
			COALESCE(si.customer, 'No Customer') AS customer,
			SUM(si.base_grand_total) AS amount
		FROM `tabSales Invoice` si
		WHERE {' AND '.join(conditions)}
		GROUP BY customer
		ORDER BY amount DESC
		LIMIT 8
		""",
		values,
		as_dict=True,
	)


def _pending_by_customer(filters):
	conditions, values = _student_group_conditions(filters)
	pending_condition = _pending_condition()
	return frappe.db.sql(
		f"""
		SELECT
			COALESCE(sgs.customer_name, sg.custom_customer, 'No Customer') AS customer,
			COUNT(sgs.name) AS pending_candidates
		FROM `tabStudent Group` sg
		INNER JOIN `tabStudent Group Student` sgs
			ON sgs.parent = sg.name
			AND sgs.parentfield = 'students'
		WHERE {' AND '.join(conditions)}
			AND {pending_condition}
		GROUP BY customer
		ORDER BY pending_candidates DESC, customer
		LIMIT 8
		""",
		values,
		as_dict=True,
	)


def _invoice_status_mix(filters):
	conditions, values = _student_group_conditions(filters)
	pending_condition = _pending_condition()
	return frappe.db.sql(
		f"""
		SELECT
			CASE
				WHEN {pending_condition} THEN 'Pending'
				WHEN EXISTS (
					SELECT 1
					FROM `tabSales Invoice Student` sis
					INNER JOIN `tabSales Invoice` si
						ON si.name = sis.parent
						AND si.docstatus = 0
					WHERE sis.student = sgs.student
						AND sis.student_group = sgs.student_group
				) THEN 'In Process'
				WHEN EXISTS (
					SELECT 1
					FROM `tabSales Invoice Student` sis
					INNER JOIN `tabSales Invoice` si
						ON si.name = sis.parent
						AND si.docstatus = 1
					WHERE sis.student = sgs.student
						AND sis.student_group = sgs.student_group
				) OR sgs.paid = 1 OR sgs.custom_invoiced = 1 THEN 'Invoiced'
				ELSE 'Pending'
			END AS status,
			COUNT(sgs.name) AS candidates
		FROM `tabStudent Group` sg
		INNER JOIN `tabStudent Group Student` sgs
			ON sgs.parent = sg.name
			AND sgs.parentfield = 'students'
		WHERE {' AND '.join(conditions)}
		GROUP BY status
		ORDER BY FIELD(status, 'Pending', 'In Process', 'Invoiced')
		""",
		values,
		as_dict=True,
	)


def _training_by_customer(filters):
	conditions, values = _student_group_conditions(filters)
	return frappe.db.sql(
		f"""
		SELECT
			COALESCE(sgs.customer_name, sg.custom_customer, 'No Customer') AS customer,
			COUNT(DISTINCT sg.name) AS groups_count,
			COUNT(sgs.name) AS candidates
		FROM `tabStudent Group` sg
		INNER JOIN `tabStudent Group Student` sgs
			ON sgs.parent = sg.name
			AND sgs.parentfield = 'students'
		WHERE {' AND '.join(conditions)}
		GROUP BY customer
		ORDER BY candidates DESC, groups_count DESC
		LIMIT 8
		""",
		values,
		as_dict=True,
	)


def _sales_trend(filters):
	labels = []
	values = []
	cursor = filters.from_date

	while cursor <= filters.to_date:
		labels.append(cursor.strftime("%d %b"))
		values.append(0)
		cursor += timedelta(days=1)

	conditions, sql_values = _sales_invoice_conditions(filters)
	rows = frappe.db.sql(
		f"""
		SELECT si.posting_date, SUM(si.base_grand_total) AS amount
		FROM `tabSales Invoice` si
		WHERE {' AND '.join(conditions)}
		GROUP BY si.posting_date
		ORDER BY si.posting_date
		""",
		sql_values,
		as_dict=True,
	)
	index_by_date = {
		(filters.from_date + timedelta(days=idx)).isoformat(): idx for idx in range(len(labels))
	}

	for row in rows:
		idx = index_by_date.get(getdate(row.posting_date).isoformat())
		if idx is not None:
			values[idx] = flt(row.amount, 2)

	return {"labels": labels, "values": values}


@frappe.whitelist()
def get_dashboard_data(filters=None):
	filters = _normalize_filters(filters)
	sales = _total_sales(filters)
	training = _training_summary(filters)
	pending = _pending_invoice_summary(filters)
	courses = _course_breakdown(filters)
	sales_trend = _sales_trend(filters)
	sales_customers = _sales_by_customer(filters)
	pending_customers = _pending_by_customer(filters)
	status_mix = _invoice_status_mix(filters)
	training_customers = _training_by_customer(filters)

	return {
		"filters": {
			"from_date": filters.from_date.isoformat(),
			"to_date": filters.to_date.isoformat(),
		},
		"kpis": {
			"total_sales": sales["total_sales"],
			"sales_volume": sales["sales_volume"],
			"pending_candidates": pending["pending_candidates"],
			"tentative_invoice_value": pending["tentative_value"],
			"avg_previous_invoice_value": pending["avg_candidate_value"],
			"training_candidates": training["candidates_count"],
			"unique_candidates": training["unique_candidates"],
			"training_groups": training["groups_count"],
		},
		"charts": {
			"course_candidates": {
				"labels": [row.course for row in courses],
				"values": [row.candidates for row in courses],
			},
			"sales_trend": sales_trend,
			"sales_by_customer": {
				"labels": [row.customer for row in sales_customers],
				"values": [flt(row.amount, 2) for row in sales_customers],
			},
			"pending_by_customer": {
				"labels": [row.customer for row in pending_customers],
				"values": [row.pending_candidates for row in pending_customers],
			},
			"invoice_status_mix": {
				"labels": [row.status for row in status_mix],
				"values": [row.candidates for row in status_mix],
			},
			"training_by_customer": {
				"labels": [row.customer for row in training_customers],
				"candidates": [row.candidates for row in training_customers],
				"groups": [row.groups_count for row in training_customers],
			},
		},
		"pending_breakdown": pending["breakdown"],
	}
