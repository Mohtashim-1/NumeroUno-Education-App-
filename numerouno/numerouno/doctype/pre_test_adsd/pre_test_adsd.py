import json
from pathlib import Path

import frappe
from frappe.model.document import Document
from frappe.utils import today


class PreTestADSD(Document):
	pass


def _load_template():
	path = Path(__file__).parent / "pre_test_adsd_template.json"
	return json.loads(path.read_text())


def _serialize_questions(rows):
	return [{"sr_no": row.sr_no, "question": row.question} for row in rows]


@frappe.whitelist()
def load_default_template(docname=None):
	template = _load_template()

	if docname and not str(docname).startswith("new-"):
		doc = frappe.get_doc("Pre Test ADSD", docname)
	else:
		doc = frappe.new_doc("Pre Test ADSD")

	doc.course_title = template["course_title"]
	doc.test_name = template["test_name"]
	doc.total_marks = template["total_marks"]
	doc.questions = []
	for row in template["questions"]:
		doc.append("questions", {"sr_no": row["sr_no"], "question": row["question"]})

	if not doc.test_date:
		doc.test_date = today()

	if docname and not str(docname).startswith("new-"):
		doc.save()
		return doc.name

	return {
		"course_title": doc.course_title,
		"test_name": doc.test_name,
		"total_marks": doc.total_marks,
		"questions": _serialize_questions(doc.questions),
	}


@frappe.whitelist()
def populate_from_student_group(docname, student_group):
	docname = (docname or "").strip()
	if not docname or docname.startswith("new-"):
		frappe.throw("Please save the Pre Test ADSD first.")
	if not student_group:
		frappe.throw("Student Group is required")

	students = frappe.get_all(
		"Student Group Student",
		filters={"parent": student_group},
		fields=["student", "student_name", "customer_name"],
		order_by="idx",
		limit=1,
	)
	if not students:
		frappe.throw("No students found in the selected Student Group.")

	row = students[0]
	doc = frappe.get_doc("Pre Test ADSD", docname)
	doc.student_group = student_group
	doc.student = row.student
	doc.candidate_name = row.student_name or row.student
	doc.company_no = row.customer_name or ""
	doc.telephone = frappe.db.get_value("Student", row.student, "student_mobile_number") or ""
	doc.save()
	return doc.name
