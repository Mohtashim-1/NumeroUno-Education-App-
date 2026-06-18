import json
from pathlib import Path

import frappe
from frappe.model.document import Document
from frappe.utils import today


class SafetyBriefing(Document):
	def validate(self):
		if not self.attendees:
			self._ensure_attendee_rows()

	def _ensure_attendee_rows(self):
		for idx in range(1, 17):
			self.append("attendees", {"learner_name": "", "company": ""})


def _load_templates():
	path = Path(__file__).parent / "safety_briefing_templates.json"
	return json.loads(path.read_text())


def get_template_for_briefing_type(briefing_type):
	templates = _load_templates()
	if briefing_type not in templates:
		frappe.throw(f"No template found for briefing type: {briefing_type}")
	return templates[briefing_type]


def apply_template(doc, template, clear_existing=False):
	if clear_existing:
		doc.discussion_points = []
		doc.practical_items = []
		doc.instructors = []

	doc.form_code = template["form_code"]
	doc.title = template["title"]
	doc.attendee_signature_mode = (
		"Simple" if template["attendee_mode"] == "simple" else "Module Columns"
	)
	doc.signature_labels = template.get("signature_labels") or ""
	doc.instructor_mode = (
		"Single Instructor" if template["instructor_mode"] == "single" else "Course Instructors Table"
	)

	if not doc.discussion_points:
		for idx, point in enumerate(template["discussion_points"], start=1):
			doc.append(
				"discussion_points",
				{"sr_no": idx, "discussion_point": point, "confirmed": 0},
			)

	if not doc.practical_items:
		for item in template["practical_items"]:
			doc.append(
				"practical_items",
				{
					"sr_no": item.get("sr_no"),
					"exercise_group": item.get("exercise_group"),
					"activity_detail": item.get("activity_detail"),
					"risk_points": item.get("risk_points"),
					"confirmed": 0,
				},
			)

	if doc.instructor_mode == "Course Instructors Table" and not doc.instructors:
		for _ in range(template.get("instructor_rows") or 1):
			doc.append("instructors", {"module": "OIS -"})

	if not doc.attendees:
		doc.attendees = []
		for _ in range(16):
			doc.append("attendees", {})


@frappe.whitelist()
def load_template(briefing_type, docname=None, clear_existing=0):
	template = get_template_for_briefing_type(briefing_type)
	clear_existing = frappe.utils.cint(clear_existing)
	docname = (docname or "").strip()
	is_saved_doc = docname and not docname.startswith("new-")

	if is_saved_doc:
		doc = frappe.get_doc("Safety Briefing", docname)
	else:
		doc = frappe.new_doc("Safety Briefing")
		doc.briefing_type = briefing_type

	apply_template(doc, template, clear_existing=clear_existing)

	if not doc.briefing_date:
		doc.briefing_date = today()

	if is_saved_doc:
		doc.save()
		return doc.name

	return {
		"form_code": doc.form_code,
		"title": doc.title,
		"attendee_signature_mode": doc.attendee_signature_mode,
		"signature_labels": doc.signature_labels,
		"instructor_mode": doc.instructor_mode,
		"discussion_points": [_child_row(row, "sr_no", "discussion_point", "confirmed") for row in doc.discussion_points],
		"practical_items": [
			_child_row(row, "sr_no", "exercise_group", "activity_detail", "risk_points", "confirmed")
			for row in doc.practical_items
		],
		"instructors": [_child_row(row, "instructor_name", "module") for row in doc.instructors],
		"attendees": [_child_row(row, "learner_name", "company") for row in doc.attendees],
	}


def _child_row(row, *fields):
	return {field: row.get(field) for field in fields}


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

	attendees = []
	for row in students:
		company = (
			row.customer_name
			or frappe.db.get_value("Student", row.student, "custom_student_company_name")
			or frappe.db.get_value("Student", row.student, "customer_name")
			or ""
		)
		attendees.append(
			{
				"learner_name": row.student_name or row.student,
				"student": row.student,
				"company": company,
			}
		)

	while len(attendees) < 16:
		attendees.append({"learner_name": "", "company": ""})

	return attendees


@frappe.whitelist()
def get_attendees_for_student_group(student_group):
	return get_students_for_group(student_group)


@frappe.whitelist()
def populate_attendees_from_student_group(docname, student_group):
	docname = (docname or "").strip()
	if not docname or docname.startswith("new-"):
		frappe.throw("Please save the Safety Briefing before populating attendees.")
	if not student_group:
		frappe.throw("Student Group is required")

	doc = frappe.get_doc("Safety Briefing", docname)
	doc.attendees = []

	for row in get_students_for_group(student_group):
		if row.get("learner_name") or row.get("student"):
			doc.append("attendees", row)
		else:
			doc.append("attendees", {})

	doc.student_group = student_group
	doc.save()
	return doc.name
