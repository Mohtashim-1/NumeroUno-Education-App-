import json
from pathlib import Path

import frappe
from frappe.model.document import Document
from frappe.utils import today


class AssessorChecklist(Document):
	def validate(self):
		if not self.learners:
			self._ensure_learner_rows()

	def _ensure_learner_rows(self):
		for idx in range(1, 17):
			self.append("learners", {"row_no": idx, "learner_name": ""})





def _load_templates():
	path = Path(__file__).parent / "assessor_checklist_templates.json"
	return json.loads(path.read_text())


def get_template_for_checklist_type(checklist_type):
	templates = _load_templates()
	if checklist_type not in templates:
		frappe.throw(f"No template found for checklist type: {checklist_type}")
	return templates[checklist_type]


def apply_template(doc, template, clear_existing=False):
	if clear_existing:
		doc.module_groups = []
		doc.outcomes = []
		doc.assessors = []
		doc.learners = []

	doc.form_code = template["form_code"]
	doc.title = template["title"]
	doc.course_code = template.get("course_code") or ""
	doc.footer_notes = "\n".join(template.get("footer_notes") or [])
	doc.unit_description = (template.get("unit_description") or "").replace("\n", "<br>")

	if not doc.module_groups:
		for row in template.get("module_groups") or []:
			doc.append(
				"module_groups",
				{"module_code": row.get("module_code"), "module_title": row.get("module_title")},
			)

	if not doc.outcomes:
		for row in template.get("outcomes") or []:
			doc.append(
				"outcomes",
				{
					"outcome_code": row.get("outcome_code"),
					"assessment_method": row.get("assessment_method"),
					"module_group": row.get("module_group"),
				},
			)

	if not doc.assessors:
		for row in template.get("assessors") or []:
			doc.append(
				"assessors",
				{
					"sr_no": row.get("sr_no"),
					"module": row.get("module"),
					"description": row.get("description"),
				},
			)

	if not doc.learners:
		for idx in range(1, 17):
			doc.append("learners", {"row_no": idx, "learner_name": ""})


def _child_row(row, *fields):
	return {field: row.get(field) for field in fields}


@frappe.whitelist()
def load_template(checklist_type, docname=None, clear_existing=0):
	template = get_template_for_checklist_type(checklist_type)
	clear_existing = frappe.utils.cint(clear_existing)
	docname = (docname or "").strip()
	is_saved_doc = docname and not docname.startswith("new-")

	if is_saved_doc:
		doc = frappe.get_doc("Assessor Checklist", docname)
	else:
		doc = frappe.new_doc("Assessor Checklist")

	doc.checklist_type = checklist_type
	apply_template(doc, template, clear_existing=clear_existing)

	if not doc.assessment_date:
		doc.assessment_date = today()

	if is_saved_doc:
		doc.save()
		return doc.name

	return {
		"checklist_type": checklist_type,
		"form_code": doc.form_code,
		"title": doc.title,
		"course_code": doc.course_code,
		"footer_notes": doc.footer_notes,
		"unit_description": doc.unit_description,
		"module_groups": [
			_child_row(row, "module_code", "module_title") for row in doc.module_groups
		],
		"outcomes": [
			_child_row(row, "outcome_code", "assessment_method", "module_group")
			for row in doc.outcomes
		],
		"assessors": [
			_child_row(row, "sr_no", "module", "description", "assessor_name")
			for row in doc.assessors
		],
		"learners": [_child_row(row, "row_no", "learner_name", "module_group") for row in doc.learners],
	}


def get_students_for_group(student_group, limit=16):
	if not student_group:
		return []

	students = frappe.get_all(
		"Student Group Student",
		filters={"parent": student_group},
		fields=["student", "student_name", "customer_name"],
		order_by="idx",
		limit=limit,
	)

	learners = []
	for idx, row in enumerate(students, start=1):
		learners.append(
			{
				"row_no": idx,
				"learner_name": row.student_name or row.student,
				"module_group": row.customer_name or "",
			}
		)

	while len(learners) < 16:
		learners.append({"row_no": len(learners) + 1, "learner_name": "", "module_group": ""})

	return learners


@frappe.whitelist()
def get_learners_for_student_group(student_group):
	return get_students_for_group(student_group)


@frappe.whitelist()
def populate_learners_from_student_group(docname, student_group):
	docname = (docname or "").strip()
	if not docname or docname.startswith("new-"):
		frappe.throw("Please save the Assessor Checklist before populating learners.")
	if not student_group:
		frappe.throw("Student Group is required")

	doc = frappe.get_doc("Assessor Checklist", docname)
	existing_results = {row.row_no: row.as_dict() for row in doc.learners}
	doc.learners = []

	for row in get_students_for_group(student_group):
		prev = existing_results.get(row["row_no"], {})
		doc.append(
			"learners",
			{
				"row_no": row["row_no"],
				"learner_name": row["learner_name"],
				"module_group": row.get("module_group") or prev.get("module_group") or "",
				**{f"result_{i}": prev.get(f"result_{i}") or "" for i in range(1, 21)},
			},
		)

	doc.student_group = student_group
	doc.save()
	return doc.name
