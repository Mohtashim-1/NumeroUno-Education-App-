import frappe
from frappe.utils import cint

from numerouno.numerouno.page.course_assessor_checklist_form.course_assessor_checklist_form import (
	CHECKLIST_TYPES,
	get_form_data,
	save_form_data,
	submit_form,
)


def _doc_for_template(data):
	doc = frappe._dict(data)
	for table in ("module_groups", "outcomes", "learners", "assessors"):
		doc[table] = [frappe._dict(row) for row in doc.get(table) or []]
	return doc


def _render_form_html(doc_data):
	doc = _doc_for_template(doc_data)
	return frappe.render_template(
		"numerouno/numerouno/print_format/assessor_checklist/assessor_checklist.html",
		{"doc": doc},
	)


@frappe.whitelist()
def get_form_html(docname=None, checklist_type=None, student_group=None):
	doc_data = get_form_data(
		docname=docname, checklist_type=checklist_type, student_group=student_group
	)
	return {"doc": doc_data, "html": _render_form_html(doc_data)}


@frappe.whitelist()
def save_form(data):
	return save_form_data(data)


@frappe.whitelist()
def submit(docname):
	return submit_form(docname)


@frappe.whitelist()
def get_checklist_types():
	return CHECKLIST_TYPES


@frappe.whitelist()
def get_checklist_list(checklist_type=None, limit=50, offset=0):
	"""Portal list for Course Assessor Checklist, optionally filtered by type/course."""
	checklist_type = (checklist_type or "").strip()
	limit = cint(limit) or 50
	offset = cint(offset) or 0

	filters = {}
	if checklist_type and checklist_type.lower() != "all":
		filters["checklist_type"] = checklist_type

	fields = [
		"name",
		"checklist_type",
		"form_code",
		"student_group",
		"assessment_date",
		"docstatus",
		"modified",
		"title",
	]
	records = frappe.get_list(
		"Assessor Checklist",
		filters=filters,
		fields=fields,
		order_by="modified desc",
		limit_page_length=limit,
		limit_start=offset,
		ignore_permissions=False,
	)

	type_counts = {t: 0 for t in CHECKLIST_TYPES}
	for row in frappe.get_all(
		"Assessor Checklist",
		fields=["checklist_type", "count(name) as cnt"],
		group_by="checklist_type",
	):
		if row.checklist_type in type_counts:
			type_counts[row.checklist_type] = cint(row.cnt)

	total = sum(type_counts.values())
	return {
		"records": records,
		"checklist_types": CHECKLIST_TYPES,
		"type_counts": type_counts,
		"total": total,
		"has_more": len(records) >= limit,
	}
