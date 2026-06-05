import json

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, nowdate


def _as_list(value):
	if not value:
		return []
	if isinstance(value, list):
		return value
	if isinstance(value, str):
		try:
			parsed = json.loads(value)
			return parsed if isinstance(parsed, list) else [parsed]
		except Exception:
			return [item.strip() for item in value.split(",") if item.strip()]
	return [value]


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


def _filters_sql(filters):
	conditions = ["sgs.student_group IS NOT NULL", "sgs.student_group != ''"]
	values = {}

	if filters.get("customer"):
		conditions.append("sgs.customer_name = %(customer)s")
		values["customer"] = filters.get("customer")

	if filters.get("from_date"):
		conditions.append("sgs.start_date >= %(from_date)s")
		values["from_date"] = filters.get("from_date")

	if filters.get("to_date"):
		conditions.append("sgs.start_date <= %(to_date)s")
		values["to_date"] = filters.get("to_date")

	return " AND ".join(conditions), values


@frappe.whitelist()
def get_data(filters=None):
	filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else (filters or {}))
	where_clause, values = _filters_sql(filters)
	pending_condition = _pending_condition()

	rows = frappe.db.sql(
		f"""
		SELECT
			sgs.name AS row_name,
			sgs.customer_name AS customer,
			sgs.student_group,
			sg.student_group_name,
			sg.course,
			sgs.course_name,
			sgs.student,
			sgs.student_name,
			sgs.start_date,
			sgs.end_date,
			sgs.customer_purchase_order,
			sgs.sales_person,
			CASE WHEN {pending_condition} THEN 1 ELSE 0 END AS is_pending,
			CASE
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
			END AS invoice_status
		FROM `tabStudent Group Student` sgs
		LEFT JOIN `tabStudent Group` sg
			ON sg.name = sgs.student_group
		WHERE {where_clause}
		ORDER BY sgs.customer_name, sgs.start_date DESC, sgs.student_group DESC, sgs.student_name
		""",
		values,
		as_dict=True,
	)

	customers = {}
	for row in rows:
		customer = row.customer or _("No Customer")
		customer_doc = customers.setdefault(
			customer,
			{
				"customer": customer,
				"pending_students": 0,
				"pending_groups": set(),
				"in_process_students": 0,
				"invoiced_students": 0,
				"groups": {},
			},
		)

		if row.invoice_status == "Pending":
			customer_doc["pending_students"] += 1
			customer_doc["pending_groups"].add(row.student_group)
		elif row.invoice_status == "In Process":
			customer_doc["in_process_students"] += 1
		else:
			customer_doc["invoiced_students"] += 1

		group = customer_doc["groups"].setdefault(
			row.student_group,
			{
				"student_group": row.student_group,
				"student_group_name": row.student_group_name or row.student_group,
				"course": row.course or row.course_name,
				"pending_students": 0,
				"in_process_students": 0,
				"invoiced_students": 0,
				"students": [],
			},
		)
		if row.invoice_status == "Pending":
			group["pending_students"] += 1
		elif row.invoice_status == "In Process":
			group["in_process_students"] += 1
		else:
			group["invoiced_students"] += 1

		group["students"].append(
			{
				"row_name": row.row_name,
				"student": row.student,
				"student_name": row.student_name,
				"student_group": row.student_group,
				"course": row.course or row.course_name,
				"start_date": row.start_date,
				"end_date": row.end_date,
				"customer_purchase_order": row.customer_purchase_order,
				"sales_person": row.sales_person,
				"invoice_status": row.invoice_status,
				"is_pending": cint(row.is_pending),
			}
		)

	for customer_doc in customers.values():
		customer_doc["pending_groups"] = len(customer_doc["pending_groups"])
		customer_doc["groups"] = list(customer_doc["groups"].values())

	customer_rows = list(customers.values())
	if not filters.get("customer") and not cint(filters.get("show_all_customers")):
		customer_rows = [
			customer
			for customer in customer_rows
			if customer["pending_students"] or customer["in_process_students"]
		]

	return {"customers": customer_rows}


def _get_pending_student_rows(customer, row_names):
	row_names = _as_list(row_names)
	if not row_names:
		frappe.throw(_("Select at least one pending student."))

	rows = frappe.db.sql(
		f"""
		SELECT
			sgs.name AS row_name,
			sgs.customer_name AS customer,
			sgs.student,
			sgs.student_name,
			sgs.student_group,
			sgs.course_name,
			sgs.start_date,
			sgs.end_date,
			sgs.customer_purchase_order,
			sgs.sales_person,
			sg.course
		FROM `tabStudent Group Student` sgs
		LEFT JOIN `tabStudent Group` sg
			ON sg.name = sgs.student_group
		WHERE sgs.name IN %(row_names)s
			AND sgs.customer_name = %(customer)s
			AND {_pending_condition()}
		ORDER BY sgs.student_group, sgs.student_name
		""",
		{"row_names": tuple(row_names), "customer": customer},
		as_dict=True,
	)

	if len(rows) != len(set(row_names)):
		frappe.throw(_("Some selected students are no longer pending. Refresh and try again."))

	return rows


def _get_item_rate(item_code):
	price = frappe.db.get_value(
		"Item Price",
		{"item_code": item_code, "selling": 1, "price_list": "Standard Selling"},
		"price_list_rate",
	)
	if price is None:
		price = frappe.db.get_value("Item Price", {"item_code": item_code, "selling": 1}, "price_list_rate")
	return flt(price or 0)


def _set_missing_item_accounts(invoice):
	company = invoice.company or frappe.defaults.get_global_default("company")
	default_income_account = frappe.db.get_value("Company", company, "default_income_account") if company else None

	for item in invoice.items:
		if not item.income_account:
			item.income_account = (
				frappe.db.get_value("Item Default", {"parent": item.item_code, "company": company}, "income_account")
				or frappe.db.get_value("Item Default", {"parent": item.item_code}, "income_account")
				or default_income_account
			)


@frappe.whitelist()
def create_invoice(customer, row_names):
	if not customer:
		frappe.throw(_("Customer is required."))

	rows = _get_pending_student_rows(customer, row_names)
	groups = sorted({row.student_group for row in rows if row.student_group})
	courses = {}

	invoice = frappe.new_doc("Sales Invoice")
	invoice.customer = customer
	invoice.due_date = add_days(nowdate(), 7)
	invoice.posting_date = nowdate()

	for group in groups:
		invoice.append("select_student_group", {"student_group": group})

	for row in rows:
		course = row.course or row.course_name
		if not course:
			frappe.throw(_("Course missing for student {0}.").format(row.student_name or row.student))
		courses.setdefault(course, []).append(row)
		invoice.append(
			"student",
			{
				"student": row.student,
				"student_name": row.student_name,
				"course": course,
				"student_group": row.student_group,
				"start_date": row.start_date,
				"end_date": row.end_date,
			},
		)

	for course, course_rows in courses.items():
		if not frappe.db.exists("Item", course):
			frappe.throw(_("Course {0} is not an Item. Please create/select the invoice item first.").format(course))
		invoice.append(
			"items",
			{
				"item_code": course,
				"qty": len(course_rows),
				"rate": _get_item_rate(course),
			},
		)

	if rows[0].customer_purchase_order:
		invoice.po_no = rows[0].customer_purchase_order

	_set_missing_item_accounts(invoice)
	invoice.insert(ignore_permissions=True)

	return {
		"sales_invoice": invoice.name,
		"student_count": len(rows),
		"student_group_count": len(groups),
	}


@frappe.whitelist()
def create_invoices(row_names):
	row_names = _as_list(row_names)
	if not row_names:
		frappe.throw(_("Select at least one pending student."))

	customers = frappe.db.sql(
		"""
		SELECT customer_name AS customer, name AS row_name
		FROM `tabStudent Group Student`
		WHERE name IN %(row_names)s
			AND customer_name IS NOT NULL
			AND customer_name != ''
		""",
		{"row_names": tuple(row_names)},
		as_dict=True,
	)

	if len(customers) != len(set(row_names)):
		frappe.throw(_("Some selected rows do not have a customer. Refresh and try again."))

	rows_by_customer = {}
	for row in customers:
		rows_by_customer.setdefault(row.customer, []).append(row.row_name)

	invoices = []
	for customer, customer_rows in rows_by_customer.items():
		invoices.append(create_invoice(customer, customer_rows))

	return {
		"invoices": invoices,
		"invoice_count": len(invoices),
		"student_count": sum(invoice["student_count"] for invoice in invoices),
	}
