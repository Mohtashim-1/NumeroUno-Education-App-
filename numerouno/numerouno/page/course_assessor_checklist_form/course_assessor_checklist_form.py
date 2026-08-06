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

LEARNER_RESULT_FIELDS = tuple(f"result_{idx}" for idx in range(1, 41))


def _serialize_child_rows(rows, fields):
	return [{field: row.get(field) for field in fields} for row in (rows or [])]


def _ensure_learner_rows(doc):
	while len(doc.learners or []) < 16:
		doc.append("learners", {"row_no": len(doc.learners or []) + 1, "learner_name": ""})


def _serialize_doc(doc):
	_ensure_learner_rows(doc)
	learner_fields = ("row_no", "learner_name", "ebs_no", "module_group", *LEARNER_RESULT_FIELDS)
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


def _checklist_outcome_key(outcome_code, module_group, has_fire_lo1):
	"""Normalize keys for older docs that mis-tagged sea-survival columns as OIS-04."""
	code = (outcome_code or "").strip()
	module = (module_group or "").strip()
	if (
		not has_fire_lo1
		and module == "OIS - 04"
		and (code.startswith("4.") or code.startswith("5."))
	):
		module = "OIS - 03"
	return (module, code)


def _normalize_checklist_layout(doc):
	"""Sync official Excel layouts for supported assessor checklist types.

	Returns True when the document layout was updated.
	"""
	checklist_type = (doc.checklist_type or "").strip()
	if checklist_type not in ("TBOSIET", "BOSIET EBS", "FOET EBS", "AGT", "Gas Monitor"):
		return False

	template = get_template_for_checklist_type(checklist_type)
	expected_outcomes = template.get("outcomes") or []
	expected_modules = template.get("module_groups") or []
	expected_assessors = template.get("assessors") or []

	current = [
		{
			"outcome_code": (row.outcome_code or "").strip(),
			"assessment_method": (row.assessment_method or "").strip(),
			"module_group": (row.module_group or "").strip(),
		}
		for row in (doc.outcomes or [])
	]
	expected = [
		{
			"outcome_code": (row.get("outcome_code") or "").strip(),
			"assessment_method": (row.get("assessment_method") or "").strip(),
			"module_group": (row.get("module_group") or "").strip(),
		}
		for row in expected_outcomes
	]
	modules_ok = [
		{"module_code": (row.module_code or "").strip(), "module_title": (row.module_title or "").strip()}
		for row in (doc.module_groups or [])
	] == [
		{
			"module_code": (row.get("module_code") or "").strip(),
			"module_title": (row.get("module_title") or "").strip(),
		}
		for row in expected_modules
	]
	assessors_ok = [
		{"module": (row.module or "").strip(), "description": (row.description or "").strip()}
		for row in (doc.assessors or [])
	] == [
		{
			"module": (row.get("module") or "").strip(),
			"description": (row.get("description") or "").strip(),
		}
		for row in expected_assessors
	]
	if current == expected and modules_ok and assessors_ok:
		return False

	has_fire_lo1 = any(
		(row.outcome_code or "").strip() == "1" and (row.module_group or "").strip() == "OIS - 04"
		for row in (doc.outcomes or [])
	)

	# Preserve learner marks keyed by corrected (module, outcome_code).
	saved_by_key = {}
	for idx, row in enumerate(doc.outcomes or [], start=1):
		key = _checklist_outcome_key(row.outcome_code, row.module_group, has_fire_lo1)
		if key not in saved_by_key:
			saved_by_key[key] = idx

	learner_marks = []
	for learner in doc.learners or []:
		marks = {}
		for key, old_idx in saved_by_key.items():
			marks[key] = learner.get(f"result_{old_idx}") or ""
		learner_marks.append(marks)

	doc.module_groups = []
	for row in expected_modules:
		doc.append(
			"module_groups",
			{
				"module_code": row.get("module_code"),
				"module_title": row.get("module_title"),
			},
		)

	doc.outcomes = []
	for row in expected_outcomes:
		doc.append(
			"outcomes",
			{
				"outcome_code": row.get("outcome_code"),
				"assessment_method": row.get("assessment_method"),
				"module_group": row.get("module_group"),
			},
		)

	# Keep assessor rows aligned with template; preserve filled signature fields.
	if expected_assessors:
		existing_by_sr = {
			cint(row.sr_no): row for row in (doc.assessors or []) if cint(getattr(row, "sr_no", 0))
		}
		existing_by_module = {
			((row.module or "").strip(), (row.description or "").strip()): row
			for row in (doc.assessors or [])
		}
		doc.assessors = []
		for row in expected_assessors:
			prev = existing_by_sr.get(cint(row.get("sr_no"))) or existing_by_module.get(
				((row.get("module") or "").strip(), (row.get("description") or "").strip()),
				{},
			)
			doc.append(
				"assessors",
				{
					"sr_no": row.get("sr_no"),
					"module": row.get("module"),
					"description": row.get("description"),
					"assessor_name": getattr(prev, "assessor_name", None)
					if not isinstance(prev, dict)
					else prev.get("assessor_name"),
					"signature": getattr(prev, "signature", None)
					if not isinstance(prev, dict)
					else prev.get("signature"),
					"assessor_date": getattr(prev, "assessor_date", None)
					if not isinstance(prev, dict)
					else prev.get("assessor_date"),
					"day": getattr(prev, "day", None) if not isinstance(prev, dict) else prev.get("day"),
					"time_ampm": getattr(prev, "time_ampm", None)
					if not isinstance(prev, dict)
					else prev.get("time_ampm"),
				},
			)

	if template.get("footer_notes"):
		doc.footer_notes = "\n".join(template.get("footer_notes") or [])
	if template.get("unit_description"):
		doc.unit_description = (template.get("unit_description") or "").replace("\n", "<br>")

	for learner, marks in zip(doc.learners or [], learner_marks):
		for field in LEARNER_RESULT_FIELDS:
			learner.set(field, "")
		for new_idx, outcome in enumerate(doc.outcomes, start=1):
			key = (
				(outcome.module_group or "").strip(),
				(outcome.outcome_code or "").strip(),
			)
			if key in marks:
				learner.set(f"result_{new_idx}", marks[key])

	return True


def _normalize_tbosiet_layout(doc):
	"""Backward-compatible alias."""
	return _normalize_checklist_layout(doc)

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
			"ebs_no": row.get("ebs_no"),
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
		if _normalize_tbosiet_layout(doc) and cint(doc.docstatus) == 0:
			doc.save(ignore_permissions=True)
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
	_normalize_tbosiet_layout(doc)
	doc.save()
	return _serialize_doc(doc)


@frappe.whitelist()
def submit_form(docname):
	doc = frappe.get_doc("Assessor Checklist", docname)
	if doc.docstatus == 0:
		doc.submit()
	return {"name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist()
def cancel_form(docname):
	doc = frappe.get_doc("Assessor Checklist", docname)
	if doc.docstatus == 1:
		doc.cancel()
	return {"name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist()
def amend_form(docname):
	doc = frappe.get_doc("Assessor Checklist", docname)
	if doc.docstatus != 2:
		frappe.throw("Only cancelled Assessor Checklists can be amended")
	amended = frappe.copy_doc(doc)
	amended.amended_from = doc.name
	amended.insert()
	return _serialize_doc(amended)


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
