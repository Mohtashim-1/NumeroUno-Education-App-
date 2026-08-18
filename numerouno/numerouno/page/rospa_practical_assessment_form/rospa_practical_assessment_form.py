import frappe
from frappe.utils import cint, today

from numerouno.numerouno.doctype.rospa_practical_assessment.rospa_practical_assessment import (
	apply_template,
)
from numerouno.numerouno.utils.signatures import resolve_learner_signature


def _serialize_criteria(rows):
	return [
		{
			"sr_no": row.get("sr_no"),
			"section": row.get("section") or "",
			"outcome": row.get("outcome") or "",
			"criterion": row.get("criterion") or "",
			"achieved": cint(row.get("achieved")),
			"source_of_evidence": row.get("source_of_evidence") or "",
		}
		for row in (rows or [])
	]


def _serialize_doc(doc):
	return {
		"name": doc.name,
		"docstatus": doc.docstatus,
		"naming_series": doc.naming_series or "RPA-.YYYY.-",
		"form_title": doc.form_title,
		"form_subtitle": doc.form_subtitle,
		"assessment_date": doc.assessment_date,
		"student_group": doc.student_group,
		"student": doc.student,
		"candidate_name": doc.candidate_name,
		"learner_signature": resolve_learner_signature(
			doc.student, doc.student_group, doc.learner_signature
		),
		"employing_company": doc.employing_company,
		"mobile_number": doc.mobile_number,
		"criteria": _serialize_criteria(doc.criteria),
		"remarks": doc.remarks,
		"training_development_needs": doc.training_development_needs,
		"achievement_status": doc.achievement_status,
		"requires_further_training": cint(doc.requires_further_training),
		"assessor_name": doc.assessor_name,
		"assessor_date": doc.assessor_date,
		"assessor_signature": doc.assessor_signature,
	}


def _apply_payload(doc, data):
	for field in (
		"naming_series",
		"form_title",
		"form_subtitle",
		"assessment_date",
		"student_group",
		"student",
		"candidate_name",
		"learner_signature",
		"employing_company",
		"mobile_number",
		"remarks",
		"training_development_needs",
		"achievement_status",
		"requires_further_training",
		"assessor_name",
		"assessor_date",
		"assessor_signature",
	):
		if field in data:
			doc.set(field, data.get(field))

	doc.criteria = []
	for row in data.get("criteria") or []:
		doc.append(
			"criteria",
			{
				"sr_no": row.get("sr_no"),
				"section": row.get("section") or "",
				"outcome": row.get("outcome") or "",
				"criterion": row.get("criterion") or "",
				"achieved": cint(row.get("achieved")),
				"source_of_evidence": row.get("source_of_evidence") or "",
			},
		)


def _get_or_create_doc(student_group, student, assessment_date=None):
	student_group = (student_group or "").strip()
	student = (student or "").strip()
	if not student_group or not student:
		frappe.throw("Student Group and Student are required")

	existing = frappe.db.get_value(
		"ROSPA Practical Assessment",
		{
			"student_group": student_group,
			"student": student,
			"docstatus": ["<", 2],
		},
		"name",
	)
	if existing:
		return frappe.get_doc("ROSPA Practical Assessment", existing)

	student_name = frappe.db.get_value("Student", student, "student_name") or student
	group_row = frappe.db.get_value(
		"Student Group Student",
		{"parent": student_group, "student": student},
		["student_name", "customer_name"],
		as_dict=True,
	)

	doc = frappe.new_doc("ROSPA Practical Assessment")
	doc.student_group = student_group
	doc.student = student
	doc.candidate_name = (group_row and group_row.student_name) or student_name
	doc.employing_company = (
		(group_row and group_row.customer_name)
		or frappe.db.get_value("Student", student, "custom_student_company_name")
		or ""
	)
	doc.mobile_number = frappe.db.get_value("Student", student, "student_mobile_number") or ""
	doc.assessment_date = assessment_date or today()
	doc.assessor_date = doc.assessment_date
	apply_template(doc)
	doc.insert(ignore_permissions=True)
	return doc


@frappe.whitelist()
def get_group_students(student_group):
	student_group = (student_group or "").strip()
	if not student_group:
		frappe.throw("Student Group is required")

	students = frappe.get_all(
		"Student Group Student",
		filters={"parent": student_group},
		fields=["student", "student_name", "customer_name"],
		order_by="idx",
	)
	records = []
	for row in students:
		existing = frappe.db.get_value(
			"ROSPA Practical Assessment",
			{
				"student_group": student_group,
				"student": row.student,
				"docstatus": ["<", 2],
			},
			["name", "docstatus"],
			as_dict=True,
		)
		records.append(
			{
				"student": row.student,
				"student_name": row.student_name or row.student,
				"employing_company": row.customer_name or "",
				"form_name": existing.name if existing else "",
				"docstatus": existing.docstatus if existing else None,
			}
		)

	course = frappe.db.get_value("Student Group", student_group, "course") or ""
	done = sum(1 for r in records if r.get("form_name"))
	return {
		"student_group": student_group,
		"course": course,
		"total": len(records),
		"started": done,
		"records": records,
	}


@frappe.whitelist()
def prepare_group(student_group, assessment_date=None):
	"""Create missing draft forms quietly — one background step before assessors open forms."""
	from numerouno.numerouno.doctype.rospa_practical_assessment.rospa_practical_assessment import (
		bulk_create_for_student_group,
	)

	return bulk_create_for_student_group(
		student_group=student_group,
		assessment_date=assessment_date or today(),
		skip_existing=1,
	)


@frappe.whitelist()
def get_form_data(docname=None, student_group=None, student=None):
	docname = (docname or "").strip()
	student_group = (student_group or "").strip() or None
	student = (student or "").strip() or None

	if docname:
		doc = frappe.get_doc("ROSPA Practical Assessment", docname)
	elif student_group and student:
		doc = _get_or_create_doc(student_group, student)
	else:
		frappe.throw("Open a learner from your student group list.")

	if not doc.criteria:
		apply_template(doc)
		doc.save()

	return _serialize_doc(doc)


@frappe.whitelist()
def save_form_data(data):
	data = frappe.parse_json(data)
	docname = (data.get("name") or "").strip()

	if docname:
		doc = frappe.get_doc("ROSPA Practical Assessment", docname)
		if doc.docstatus == 1:
			frappe.throw("Submitted assessment cannot be edited")
	else:
		doc = frappe.new_doc("ROSPA Practical Assessment")

	_apply_payload(doc, data)
	doc.save()
	return _serialize_doc(doc)


@frappe.whitelist()
def submit_form(docname):
	doc = frappe.get_doc("ROSPA Practical Assessment", docname)
	if doc.docstatus == 0:
		doc.submit()
	return {"name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist()
def cancel_form(docname):
	doc = frappe.get_doc("ROSPA Practical Assessment", docname)
	if doc.docstatus == 1:
		doc.cancel()
	return {"name": doc.name, "docstatus": doc.docstatus}
