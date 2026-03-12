import calendar
from datetime import date, datetime, timedelta

import frappe
from frappe.utils import add_days, flt, getdate, nowdate


def _coerce_date(value, fallback):
	return getdate(value or fallback)


def _normalize_filters(filters=None):
	filters = frappe.parse_json(filters) if filters else {}
	to_date = _coerce_date(filters.get("to_date"), nowdate())
	from_date = _coerce_date(filters.get("from_date"), add_days(to_date, -179))
	if from_date > to_date:
		from_date, to_date = to_date, from_date

	period = (filters.get("period") or "Monthly").title()
	if period not in {"Daily", "Weekly", "Monthly", "Quarterly"}:
		period = "Monthly"

	return {
		"from_date": from_date,
		"to_date": to_date,
		"period": period,
		"company": filters.get("company"),
		"customer": filters.get("customer"),
		"program": filters.get("program"),
		"course": filters.get("course"),
	}


def _previous_window(filters):
	span = (filters["to_date"] - filters["from_date"]).days
	prev_to = filters["from_date"] - timedelta(days=1)
	prev_from = prev_to - timedelta(days=span)
	return prev_from, prev_to


def _bucket_key(period, current_date):
	if isinstance(current_date, datetime):
		current_date = current_date.date()

	if period == "Daily":
		return current_date.strftime("%Y-%m-%d")
	if period == "Weekly":
		year, week, _ = current_date.isocalendar()
		return f"{year}-W{week:02d}"
	if period == "Quarterly":
		quarter = ((current_date.month - 1) // 3) + 1
		return f"{current_date.year}-Q{quarter}"
	return current_date.strftime("%Y-%m")


def _bucket_label(period, bucket):
	if period == "Daily":
		return datetime.strptime(bucket, "%Y-%m-%d").strftime("%d %b")
	if period == "Weekly":
		year, week = bucket.split("-W")
		return f"W{week} {year}"
	if period == "Quarterly":
		year, quarter = bucket.split("-Q")
		return f"Q{quarter} {year}"

	year, month = bucket.split("-")
	return f"{calendar.month_abbr[int(month)]} {year}"


def _build_bucket_map(period, from_date, to_date):
	buckets = {}
	cursor = from_date

	while cursor <= to_date:
		key = _bucket_key(period, cursor)
		buckets.setdefault(key, 0.0)

		if period == "Daily":
			cursor += timedelta(days=1)
		elif period == "Weekly":
			cursor += timedelta(days=7)
		elif period == "Monthly":
			if cursor.month == 12:
				cursor = date(cursor.year + 1, 1, 1)
			else:
				cursor = date(cursor.year, cursor.month + 1, 1)
		else:
			next_month = cursor.month + 3
			next_year = cursor.year + ((next_month - 1) // 12)
			next_month = ((next_month - 1) % 12) + 1
			cursor = date(next_year, next_month, 1)

	return buckets


def _sum_rows(rows, fieldname):
	return sum(flt(row.get(fieldname)) for row in rows)


def _avg_rows(rows, fieldname):
	return flt(_sum_rows(rows, fieldname) / len(rows), 2) if rows else 0


def _pct_change(current, previous):
	if not previous:
		return 100.0 if current else 0.0
	return flt(((current - previous) / previous) * 100, 2)


def _finance_filters(filters, alias, party_field="customer"):
	conditions = [f"{alias}.docstatus = 1", f"{alias}.posting_date BETWEEN %(from_date)s AND %(to_date)s"]
	values = {"from_date": filters["from_date"], "to_date": filters["to_date"]}

	if filters.get("company"):
		conditions.append(f"{alias}.company = %(company)s")
		values["company"] = filters["company"]

	if filters.get("customer"):
		conditions.append(f"{alias}.{party_field} = %(customer)s")
		values["customer"] = filters["customer"]

	return conditions, values


def _sales_rows(filters):
	conditions, values = _finance_filters(filters, "si")
	return frappe.db.sql(
		f"""
		SELECT si.posting_date, si.customer, si.name, si.base_grand_total as amount
		FROM `tabSales Invoice` si
		WHERE {' AND '.join(conditions)}
		ORDER BY si.posting_date
		""",
		values,
		as_dict=True,
	)


def _collection_rows(filters):
	conditions, values = _finance_filters(filters, "pe")
	conditions.append("pe.payment_type = 'Receive'")
	return frappe.db.sql(
		f"""
		SELECT pe.posting_date, pe.party as customer, pe.name, pe.base_received_amount as amount
		FROM `tabPayment Entry` pe
		WHERE {' AND '.join(conditions)}
		ORDER BY pe.posting_date
		""",
		values,
		as_dict=True,
	)


def _expense_rows(filters):
	conditions, values = _finance_filters(filters, "pi", party_field="supplier")
	return frappe.db.sql(
		f"""
		SELECT pi.posting_date, pi.supplier, pi.name, pi.base_grand_total as amount
		FROM `tabPurchase Invoice` pi
		WHERE {' AND '.join(conditions)}
		ORDER BY pi.posting_date
		""",
		values,
		as_dict=True,
	)


def _training_conditions(filters):
	conditions = ["sg.docstatus < 2", "sg.from_date BETWEEN %(from_date)s AND %(to_date)s"]
	values = {"from_date": filters["from_date"], "to_date": filters["to_date"]}

	if filters.get("customer"):
		conditions.append("sg.custom_customer = %(customer)s")
		values["customer"] = filters["customer"]

	if filters.get("program"):
		conditions.append("sg.program = %(program)s")
		values["program"] = filters["program"]

	if filters.get("course"):
		conditions.append("sg.course = %(course)s")
		values["course"] = filters["course"]

	return conditions, values


def _training_summary(filters):
	conditions, values = _training_conditions(filters)
	rows = frappe.db.sql(
		f"""
		SELECT
			COUNT(DISTINCT sg.name) as groups_count,
			COUNT(DISTINCT sgs.student) as candidates_count,
			COUNT(DISTINCT sgi.instructor) as instructors_count,
			COUNT(DISTINCT sg.custom_customer) as companies_count
		FROM `tabStudent Group` sg
		LEFT JOIN `tabStudent Group Student` sgs
			ON sgs.parent = sg.name AND sgs.parentfield = 'students'
		LEFT JOIN `tabStudent Group Instructor` sgi
			ON sgi.parent = sg.name AND sgi.parentfield = 'instructors'
		WHERE {' AND '.join(conditions)}
		""",
		values,
		as_dict=True,
	)
	return rows[0] if rows else {}


def _training_breakdown(filters):
	conditions, values = _training_conditions(filters)
	base_where = " AND ".join(conditions)

	instructors = frappe.db.sql(
		f"""
		SELECT
			COALESCE(sgi.instructor_name, sgi.instructor, 'Unassigned') as label,
			COUNT(DISTINCT sg.name) as groups_count,
			COUNT(DISTINCT sgs.student) as candidates_count
		FROM `tabStudent Group` sg
		LEFT JOIN `tabStudent Group Instructor` sgi
			ON sgi.parent = sg.name AND sgi.parentfield = 'instructors'
		LEFT JOIN `tabStudent Group Student` sgs
			ON sgs.parent = sg.name AND sgs.parentfield = 'students'
		WHERE {base_where}
		GROUP BY label
		ORDER BY candidates_count DESC, groups_count DESC
		LIMIT 8
		""",
		values,
		as_dict=True,
	)

	companies = frappe.db.sql(
		f"""
		SELECT
			COALESCE(sg.custom_customer, 'Walk-in / Direct') as label,
			COUNT(DISTINCT sg.name) as groups_count,
			COUNT(DISTINCT sgs.student) as candidates_count
		FROM `tabStudent Group` sg
		LEFT JOIN `tabStudent Group Student` sgs
			ON sgs.parent = sg.name AND sgs.parentfield = 'students'
		WHERE {base_where}
		GROUP BY label
		ORDER BY candidates_count DESC, groups_count DESC
		LIMIT 8
		""",
		values,
		as_dict=True,
	)

	courses = frappe.db.sql(
		f"""
		SELECT
			COALESCE(sg.course, 'Unmapped Course') as label,
			COUNT(DISTINCT sg.name) as groups_count,
			COUNT(DISTINCT sgs.student) as candidates_count
		FROM `tabStudent Group` sg
		LEFT JOIN `tabStudent Group Student` sgs
			ON sgs.parent = sg.name AND sgs.parentfield = 'students'
		WHERE {base_where}
		GROUP BY label
		ORDER BY candidates_count DESC, groups_count DESC
		LIMIT 8
		""",
		values,
		as_dict=True,
	)

	return {"instructors": instructors, "companies": companies, "courses": courses}


def _training_timeline(filters):
	conditions, values = _training_conditions(filters)
	return frappe.db.sql(
		f"""
		SELECT sg.from_date, COUNT(DISTINCT sgs.student) as candidates
		FROM `tabStudent Group` sg
		LEFT JOIN `tabStudent Group Student` sgs
			ON sgs.parent = sg.name AND sgs.parentfield = 'students'
		WHERE {' AND '.join(conditions)}
		GROUP BY sg.name, sg.from_date
		ORDER BY sg.from_date
		""",
		values,
		as_dict=True,
	)


def _series_from_rows(rows, period, from_date, to_date, date_field="posting_date", value_field="amount"):
	buckets = _build_bucket_map(period, from_date, to_date)
	for row in rows:
		bucket = _bucket_key(period, row.get(date_field))
		if bucket in buckets:
			buckets[bucket] += flt(row.get(value_field))

	return {
		"labels": [_bucket_label(period, key) for key in buckets.keys()],
		"values": [flt(value, 2) for value in buckets.values()],
	}


def _count_series_from_rows(rows, period, from_date, to_date, date_field="posting_date"):
	buckets = _build_bucket_map(period, from_date, to_date)
	for row in rows:
		bucket = _bucket_key(period, row.get(date_field))
		if bucket in buckets:
			buckets[bucket] += 1

	return {
		"labels": [_bucket_label(period, key) for key in buckets.keys()],
		"values": [int(value) for value in buckets.values()],
	}


def _top_counterparty(rows, fieldname, fallback_label):
	counter = {}
	for row in rows:
		label = row.get(fieldname) or fallback_label
		counter[label] = counter.get(label, 0.0) + flt(row.get("amount"))

	ordered = sorted(counter.items(), key=lambda item: item[1], reverse=True)[:8]
	return {
		"labels": [item[0] for item in ordered],
		"values": [flt(item[1], 2) for item in ordered],
	}


def _group_rankings(rows, fieldname, fallback_label):
	grouped = {}
	for row in rows:
		label = row.get(fieldname) or fallback_label
		entry = grouped.setdefault(label, {"label": label, "count": 0, "amount": 0.0})
		entry["count"] += 1
		entry["amount"] += flt(row.get("amount"))

	return sorted(grouped.values(), key=lambda row: row["amount"], reverse=True)[:10]


def _recent_transactions(sales_rows, collection_rows, expense_rows):
	transactions = []

	for row in sales_rows:
		transactions.append(
			{
				"date": row.get("posting_date"),
				"type": "Sales Invoice",
				"party": row.get("customer") or "Direct",
				"amount": flt(row.get("amount")),
				"reference": row.get("name"),
			}
		)

	for row in collection_rows:
		transactions.append(
			{
				"date": row.get("posting_date"),
				"type": "Payment Entry",
				"party": row.get("customer") or "Unknown",
				"amount": flt(row.get("amount")),
				"reference": row.get("name"),
			}
		)

	for row in expense_rows:
		transactions.append(
			{
				"date": row.get("posting_date"),
				"type": "Purchase Invoice",
				"party": row.get("supplier") or "Unknown",
				"amount": flt(row.get("amount")),
				"reference": row.get("name"),
			}
		)

	return sorted(transactions, key=lambda row: row["date"], reverse=True)[:12]


def _recent_training_groups(filters):
	conditions, values = _training_conditions(filters)
	return frappe.db.sql(
		f"""
		SELECT
			sg.name,
			sg.from_date,
			sg.course,
			sg.program,
			COALESCE(sg.custom_customer, 'Walk-in / Direct') as company,
			COUNT(DISTINCT sgs.student) as candidates,
			GROUP_CONCAT(DISTINCT COALESCE(sgi.instructor_name, sgi.instructor) SEPARATOR ', ') as instructors
		FROM `tabStudent Group` sg
		LEFT JOIN `tabStudent Group Student` sgs
			ON sgs.parent = sg.name AND sgs.parentfield = 'students'
		LEFT JOIN `tabStudent Group Instructor` sgi
			ON sgi.parent = sg.name AND sgi.parentfield = 'instructors'
		WHERE {' AND '.join(conditions)}
		GROUP BY sg.name, sg.from_date, sg.course, sg.program, sg.custom_customer
		ORDER BY sg.from_date DESC, sg.modified DESC
		LIMIT 10
		""",
		values,
		as_dict=True,
	)


def _best_label(labels, values):
	if not labels or not values:
		return None
	best_index = max(range(len(values)), key=lambda idx: values[idx])
	return {"label": labels[best_index], "value": flt(values[best_index], 2)}


def _build_summary(filters, sales_total, collections_total, expenses_total, training_summary, sales_series):
	top_period = _best_label(sales_series["labels"], sales_series["values"])
	return {
		"range": f"{filters['from_date'].isoformat()} to {filters['to_date'].isoformat()}",
		"top_period": top_period,
		"net_position": flt(collections_total - expenses_total, 2),
		"candidate_per_group": flt(
			(training_summary.get("candidates_count") or 0) / (training_summary.get("groups_count") or 1), 2
		)
		if training_summary.get("groups_count")
		else 0,
	}


@frappe.whitelist()
def get_management_dashboard_data(filters=None):
	filters = _normalize_filters(filters)
	prev_from, prev_to = _previous_window(filters)

	sales_rows = _sales_rows(filters)
	collection_rows = _collection_rows(filters)
	expense_rows = _expense_rows(filters)
	training_summary = _training_summary(filters)
	training_breakdown = _training_breakdown(filters)
	training_timeline = _training_timeline(filters)
	recent_training_groups = _recent_training_groups(filters)

	prev_filters = dict(filters)
	prev_filters["from_date"] = prev_from
	prev_filters["to_date"] = prev_to

	prev_sales_total = _sum_rows(_sales_rows(prev_filters), "amount")
	prev_collection_total = _sum_rows(_collection_rows(prev_filters), "amount")
	prev_expense_total = _sum_rows(_expense_rows(prev_filters), "amount")
	prev_training_summary = _training_summary(prev_filters)

	sales_total = _sum_rows(sales_rows, "amount")
	collections_total = _sum_rows(collection_rows, "amount")
	expenses_total = _sum_rows(expense_rows, "amount")
	gross_surplus = flt(sales_total - expenses_total, 2)
	collection_gap = flt(sales_total - collections_total, 2)
	collection_efficiency = flt((collections_total / sales_total) * 100, 2) if sales_total else 0
	expense_ratio = flt((expenses_total / sales_total) * 100, 2) if sales_total else 0

	sales_series = _series_from_rows(
		sales_rows, filters["period"], filters["from_date"], filters["to_date"]
	)
	collections_series = _series_from_rows(
		collection_rows, filters["period"], filters["from_date"], filters["to_date"]
	)
	expenses_series = _series_from_rows(
		expense_rows, filters["period"], filters["from_date"], filters["to_date"]
	)
	training_series = _series_from_rows(
		training_timeline,
		filters["period"],
		filters["from_date"],
		filters["to_date"],
		date_field="from_date",
		value_field="candidates",
	)
	training_group_series = _count_series_from_rows(
		training_timeline,
		filters["period"],
		filters["from_date"],
		filters["to_date"],
		date_field="from_date",
	)
	surplus_series = [
		flt(sales_series["values"][idx] - expenses_series["values"][idx], 2)
		for idx in range(len(sales_series["values"]))
	]
	cash_position_series = [
		flt(collections_series["values"][idx] - expenses_series["values"][idx], 2)
		for idx in range(len(collections_series["values"]))
	]
	customer_rankings = _group_rankings(sales_rows, "customer", "Direct")
	supplier_rankings = _group_rankings(expense_rows, "supplier", "Unknown")
	summary = _build_summary(
		filters, sales_total, collections_total, expenses_total, training_summary, sales_series
	)

	return {
		"filters": {
			"from_date": filters["from_date"].isoformat(),
			"to_date": filters["to_date"].isoformat(),
			"period": filters["period"],
		},
		"kpis": [
			{
				"label": "Sales",
				"value": flt(sales_total, 2),
				"change": _pct_change(sales_total, prev_sales_total),
				"subtitle": "Submitted sales invoices",
			},
			{
				"label": "Collections",
				"value": flt(collections_total, 2),
				"change": _pct_change(collections_total, prev_collection_total),
				"subtitle": "Received payment entries",
			},
			{
				"label": "Expenses",
				"value": flt(expenses_total, 2),
				"change": _pct_change(expenses_total, prev_expense_total),
				"subtitle": "Submitted purchase invoices",
			},
			{
				"label": "Training Candidates",
				"value": int(training_summary.get("candidates_count") or 0),
				"change": _pct_change(
					int(training_summary.get("candidates_count") or 0),
					int(prev_training_summary.get("candidates_count") or 0),
				),
				"subtitle": "Candidates in student groups",
			},
		],
		"highlights": {
			"gross_surplus": gross_surplus,
			"collection_gap": collection_gap,
			"collection_efficiency": collection_efficiency,
			"expense_ratio": expense_ratio,
			"avg_invoice_value": _avg_rows(sales_rows, "amount"),
			"avg_receipt_value": _avg_rows(collection_rows, "amount"),
			"training_groups": int(training_summary.get("groups_count") or 0),
			"instructors": int(training_summary.get("instructors_count") or 0),
			"companies": int(training_summary.get("companies_count") or 0),
			"sales_docs": len(sales_rows),
			"receipt_docs": len(collection_rows),
			"expense_docs": len(expense_rows),
		},
		"summary": summary,
		"charts": {
			"financial_trend": {
				"labels": sales_series["labels"],
				"sales": sales_series["values"],
				"collections": collections_series["values"],
				"expenses": expenses_series["values"],
				"surplus": surplus_series,
			},
			"revenue_mix": {
				"labels": ["Sales", "Collections", "Expenses"],
				"values": [flt(sales_total, 2), flt(collections_total, 2), flt(expenses_total, 2)],
			},
			"top_customers": _top_counterparty(sales_rows, "customer", "Direct"),
			"top_suppliers": _top_counterparty(expense_rows, "supplier", "Unknown"),
			"customer_share": {
				"labels": [row.get("label") for row in customer_rankings[:6]],
				"values": [flt(row.get("amount"), 2) for row in customer_rankings[:6]],
			},
			"training_by_course": {
				"labels": [row.get("label") for row in training_breakdown["courses"]],
				"groups": [int(row.get("groups_count") or 0) for row in training_breakdown["courses"]],
				"candidates": [int(row.get("candidates_count") or 0) for row in training_breakdown["courses"]],
			},
			"training_by_instructor": {
				"labels": [row.get("label") for row in training_breakdown["instructors"]],
				"groups": [int(row.get("groups_count") or 0) for row in training_breakdown["instructors"]],
				"candidates": [
					int(row.get("candidates_count") or 0) for row in training_breakdown["instructors"]
				],
			},
			"training_by_company": {
				"labels": [row.get("label") for row in training_breakdown["companies"]],
				"groups": [int(row.get("groups_count") or 0) for row in training_breakdown["companies"]],
				"candidates": [int(row.get("candidates_count") or 0) for row in training_breakdown["companies"]],
			},
			"training_candidate_trend": training_series,
			"training_group_trend": training_group_series,
			"cash_position_trend": {
				"labels": collections_series["labels"],
				"collections": collections_series["values"],
				"expenses": expenses_series["values"],
				"net": cash_position_series,
			},
			"document_volume": {
				"labels": ["Sales Invoices", "Payment Entries", "Purchase Invoices", "Training Groups"],
				"values": [
					len(sales_rows),
					len(collection_rows),
					len(expense_rows),
					int(training_summary.get("groups_count") or 0),
				],
			},
		},
		"tables": {
			"course_breakdown": training_breakdown["courses"],
			"customer_breakdown": customer_rankings,
			"supplier_breakdown": supplier_rankings,
			"instructor_breakdown": training_breakdown["instructors"],
			"company_breakdown": training_breakdown["companies"],
			"recent_transactions": _recent_transactions(sales_rows, collection_rows, expense_rows),
			"recent_training_groups": recent_training_groups,
		},
		"report_links": [
			{"label": "Student Payment Summary", "route": "/app/query-report/Student%20Payment%20Summary"},
			{"label": "Unpaid Students Dashboard", "route": "/app/query-report/Unpaid%20Students%20Dashboard"},
			{"label": "Pending Invoices", "route": "/app/query-report/Pending%20Invoices"},
		],
	}
