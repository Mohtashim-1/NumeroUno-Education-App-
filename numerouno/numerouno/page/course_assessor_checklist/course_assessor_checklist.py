import frappe
from frappe.utils import cint, today

from numerouno.numerouno.doctype.assessor_checklist.assessor_checklist import (
	apply_template,
	get_students_for_group,
	get_template_for_checklist_type,
)


CHECKLIST_TYPES = [
	"Basic H2S",
	"BOSIET EBS",
	"TBOSIET",
	"FOET EBS",
	"T FOET",
	"HUET EBS",
	"THUET",
	"Gas Monitor",
	"AGT",
	"TSbB Initial",
	"TSbB Further",
]

LEARNER_RESULT_FIELDS = tuple(f"result_{idx}" for idx in range(1, 21))


def _serialize_child_rows(rows, fields):
	return [{field: row.get(field) for field in fields} for row in (rows or [])]


def _ensure_learner_rows(doc):
	while len(doc.learners or []) < 16:
		doc.append("learners", {"row_no": len(doc.learners or []) + 1, "learner_name": ""})


def _serialize_doc(doc):
	_ensure_learner_rows(doc)
	learner_fields = ("row_no", "learner_name", "module_group", *LEARNER_RESULT_FIELDS)
	return {
		"name": doc.name,
		"docstatus": doc.docstatus,
		"naming_series": doc.naming_series or "ACL-.YYYY.-",
		"checklist_type": doc.checklist_type,
		"form_code": doc.form_code,
		"title": doc.title,
		"course_code": doc.course_code,
		"assessment_date": doc.assessment_date,
		"student_group": doc.student_group,
		"course": doc.course,
		"variant_9014": doc.variant_9014,
		"variant_9014_a": doc.variant_9014_a,
		"variant_9014_b": doc.variant_9014_b,
		"ebs_no": doc.ebs_no,
		"demo_ebs_used_by": doc.demo_ebs_used_by,
		"remarks": doc.remarks,
		"footer_notes": doc.footer_notes,
		"unit_description": doc.unit_description,
		"module_groups": _serialize_child_rows(
			doc.module_groups, ("module_code", "module_title")
		),
		"outcomes": _serialize_child_rows(
			doc.outcomes, ("outcome_code", "assessment_method", "module_group")
		),
		"learners": _serialize_child_rows(doc.learners, learner_fields),
		"assessors": _serialize_child_rows(
			doc.assessors,
			(
				"sr_no",
				"assessor_name",
				"module",
				"description",
				"signature",
				"assessor_date",
				"day",
				"time_ampm",
			),
		),
	}


def _normalize_tbosiet_layout(doc):
	"""Backfill TBOSIET OIS-04 grouping for older saved checklists."""
	if (doc.checklist_type or "") != "TBOSIET":
		return

	module_codes = {row.module_code for row in (doc.module_groups or []) if row.module_code}
	if "OIS - 04" not in module_codes:
		doc.append(
			"module_groups",
			{
				"module_code": "OIS - 04",
				"module_title": "Fire Fighting and Self Rescue",
			},
		)

	for row in doc.outcomes or []:
		outcome_code = (row.outcome_code or "").strip()
		if outcome_code.startswith("4.") or outcome_code == "5.1":
			row.module_group = "OIS - 04"


def _apply_payload(doc, data):
	for field in (
		"naming_series",
		"checklist_type",
		"form_code",
		"title",
		"course_code",
		"assessment_date",
		"student_group",
		"course",
		"variant_9014",
		"variant_9014_a",
		"variant_9014_b",
		"ebs_no",
		"demo_ebs_used_by",
		"remarks",
		"footer_notes",
		"unit_description",
	):
		if field in data:
			doc.set(field, data.get(field))

	doc.module_groups = []
	for row in data.get("module_groups") or []:
		doc.append(
			"module_groups",
			{
				"module_code": row.get("module_code"),
				"module_title": row.get("module_title"),
			},
		)

	doc.outcomes = []
	for row in data.get("outcomes") or []:
		doc.append(
			"outcomes",
			{
				"outcome_code": row.get("outcome_code"),
				"assessment_method": row.get("assessment_method"),
				"module_group": row.get("module_group"),
			},
		)

	doc.learners = []
	for row in data.get("learners") or []:
		learner_row = {
			"row_no": row.get("row_no"),
			"learner_name": row.get("learner_name"),
			"module_group": row.get("module_group"),
		}
		for field in LEARNER_RESULT_FIELDS:
			learner_row[field] = row.get(field) or ""
		doc.append("learners", learner_row)
	_ensure_learner_rows(doc)

	doc.assessors = []
	for row in data.get("assessors") or []:
		doc.append(
			"assessors",
			{
				"sr_no": row.get("sr_no"),
				"assessor_name": row.get("assessor_name"),
				"module": row.get("module"),
				"description": row.get("description"),
				"signature": row.get("signature"),
				"assessor_date": row.get("assessor_date"),
				"day": row.get("day"),
				"time_ampm": row.get("time_ampm"),
			},
		)


@frappe.whitelist()
def get_checklist_types():
	return CHECKLIST_TYPES


@frappe.whitelist()
def get_form_data(docname=None, checklist_type=None, student_group=None):
	docname = (docname or "").strip()
	student_group = (student_group or "").strip() or None

	if docname:
		doc = frappe.get_doc("Assessor Checklist", docname)
		_normalize_tbosiet_layout(doc)
	elif checklist_type:
		doc = frappe.new_doc("Assessor Checklist")
		doc.checklist_type = checklist_type
		template = get_template_for_checklist_type(checklist_type)
		apply_template(doc, template)
		_normalize_tbosiet_layout(doc)
		doc.assessment_date = today()
		if student_group:
			doc.student_group = student_group
			doc.learners = []
			for row in get_students_for_group(student_group):
				doc.append("learners", row)
			_ensure_learner_rows(doc)
	else:
		frappe.throw("Document name or checklist type is required")

	return _serialize_doc(doc)


@frappe.whitelist()
def save_form_data(data):
	data = frappe.parse_json(data)
	docname = (data.get("name") or "").strip()

	if docname:
		doc = frappe.get_doc("Assessor Checklist", docname)
		if doc.docstatus == 1:
			frappe.throw("Submitted Course Assessor Checklist cannot be edited")
	else:
		doc = frappe.new_doc("Assessor Checklist")

	_apply_payload(doc, data)
	doc.save()
	return _serialize_doc(doc)


@frappe.whitelist()
def submit_form(docname):
	doc = frappe.get_doc("Assessor Checklist", docname)
	if doc.docstatus == 0:
		doc.submit()
	return {"name": doc.name, "docstatus": doc.docstatus}


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
