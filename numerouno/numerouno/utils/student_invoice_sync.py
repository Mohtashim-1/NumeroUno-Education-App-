"""Keep Student Group Student invoice flags aligned with Sales Invoices."""

import frappe

# Latest submitted/draft invoice per (student, student_group) for report queries.
SUBMITTED_INVOICE_JOIN_SQL = """
LEFT JOIN (
	SELECT
		sis.student,
		sis.student_group,
		SUBSTRING_INDEX(
			GROUP_CONCAT(
				CASE WHEN si.docstatus = 1 THEN si.name END
				ORDER BY si.posting_date DESC, si.creation DESC
			),
			',',
			1
		) AS submitted_invoice_no,
		SUBSTRING_INDEX(
			GROUP_CONCAT(
				CASE WHEN si.docstatus = 0 THEN si.name END
				ORDER BY si.posting_date DESC, si.creation DESC
			),
			',',
			1
		) AS draft_invoice_no
	FROM `tabSales Invoice Student` sis
	INNER JOIN `tabSales Invoice` si
		ON si.name = sis.parent
		AND si.docstatus IN (0, 1)
	WHERE sis.student IS NOT NULL
		AND sis.student_group IS NOT NULL
		AND sis.student_group != ''
	GROUP BY sis.student, sis.student_group
) AS inv
	ON inv.student = sgs.student
	AND inv.student_group = sgs.student_group
"""

INVOICE_NO_SQL = """
COALESCE(
	inv.submitted_invoice_no,
	NULLIF(sgs.sales_invoice, ''),
	NULLIF(sgs.custom_sales_invoice, ''),
	inv.draft_invoice_no
)
"""

INVOICE_STATUS_SQL = """
CASE
	WHEN inv.submitted_invoice_no IS NOT NULL THEN 'Invoiced'
	WHEN sgs.paid = 1 THEN 'Invoiced'
	WHEN sgs.custom_invoiced = 1 THEN 'Invoiced'
	WHEN inv.draft_invoice_no IS NOT NULL THEN 'In Process'
	ELSE 'Pending'
END
"""

NOT_INVOICED_CONDITION_SQL = """
(
	inv.submitted_invoice_no IS NULL
	AND inv.draft_invoice_no IS NULL
	AND (sgs.paid = 0 OR sgs.paid IS NULL)
	AND (sgs.custom_invoiced = 0 OR sgs.custom_invoiced IS NULL)
)
"""


def sync_student_group_student_from_sales_invoice(doc, method=None):
	"""Mark students on a submitted Sales Invoice as invoiced on their Student Group row."""
	if doc.doctype != "Sales Invoice" or doc.docstatus != 1:
		return

	for row in doc.get("student") or []:
		if not row.student or not row.student_group:
			continue
		_mark_student_invoiced(row.student, row.student_group, doc.name)


def clear_student_group_student_on_invoice_cancel(doc, method=None):
	"""Clear invoice flags when cancelled, unless another submitted invoice exists."""
	if doc.doctype != "Sales Invoice":
		return

	for row in doc.get("student") or []:
		if not row.student or not row.student_group:
			continue
		if _has_other_submitted_invoice(row.student, row.student_group, doc.name):
			other_invoice = _get_latest_submitted_invoice(row.student, row.student_group)
			_mark_student_invoiced(row.student, row.student_group, other_invoice)
		else:
			_clear_student_invoice(row.student, row.student_group)


def backfill_invoiced_students_from_sales_invoices():
	"""One-time sync: update Student Group Student rows from submitted Sales Invoices."""
	frappe.db.sql(
		"""
		UPDATE `tabStudent Group Student` sgs
		INNER JOIN (
			SELECT
				sis.student,
				sis.student_group,
				SUBSTRING_INDEX(
					GROUP_CONCAT(si.name ORDER BY si.posting_date DESC, si.creation DESC),
					',',
					1
				) AS sales_invoice
			FROM `tabSales Invoice Student` sis
			INNER JOIN `tabSales Invoice` si
				ON si.name = sis.parent
				AND si.docstatus = 1
			WHERE sis.student IS NOT NULL
				AND sis.student_group IS NOT NULL
				AND sis.student_group != ''
			GROUP BY sis.student, sis.student_group
		) inv
			ON inv.student = sgs.student
			AND inv.student_group = sgs.parent
		SET
			sgs.paid = 1,
			sgs.sales_invoice = inv.sales_invoice,
			sgs.custom_invoiced = 1,
			sgs.custom_sales_invoice = inv.sales_invoice
		"""
	)
	frappe.db.commit()
	updated = frappe.db.sql("SELECT ROW_COUNT()")[0][0]
	return {"student_rows_updated": updated}


def _mark_student_invoiced(student, student_group, sales_invoice):
	frappe.db.sql(
		"""
		UPDATE `tabStudent Group Student`
		SET
			paid = 1,
			sales_invoice = %(sales_invoice)s,
			custom_invoiced = 1,
			custom_sales_invoice = %(sales_invoice)s
		WHERE parent = %(student_group)s
			AND student = %(student)s
		""",
		{
			"student": student,
			"student_group": student_group,
			"sales_invoice": sales_invoice,
		},
	)


def _clear_student_invoice(student, student_group):
	frappe.db.sql(
		"""
		UPDATE `tabStudent Group Student`
		SET
			paid = 0,
			sales_invoice = NULL,
			custom_invoiced = 0,
			custom_sales_invoice = ''
		WHERE parent = %(student_group)s
			AND student = %(student)s
		""",
		{"student": student, "student_group": student_group},
	)


def _has_other_submitted_invoice(student, student_group, exclude_invoice):
	return bool(
		frappe.db.sql(
			"""
			SELECT 1
			FROM `tabSales Invoice Student` sis
			INNER JOIN `tabSales Invoice` si
				ON si.name = sis.parent
				AND si.docstatus = 1
			WHERE sis.student = %(student)s
				AND sis.student_group = %(student_group)s
				AND si.name != %(exclude_invoice)s
			LIMIT 1
			""",
			{
				"student": student,
				"student_group": student_group,
				"exclude_invoice": exclude_invoice,
			},
		)
	)


def _get_latest_submitted_invoice(student, student_group):
	return frappe.db.sql(
		"""
		SELECT si.name
		FROM `tabSales Invoice Student` sis
		INNER JOIN `tabSales Invoice` si
			ON si.name = sis.parent
			AND si.docstatus = 1
		WHERE sis.student = %(student)s
			AND sis.student_group = %(student_group)s
		ORDER BY si.posting_date DESC, si.creation DESC
		LIMIT 1
		""",
		{"student": student, "student_group": student_group},
	)[0][0]
