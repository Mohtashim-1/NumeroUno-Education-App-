import json
from pathlib import Path

import frappe
from frappe.model.document import Document
from frappe.utils import today


class EnglishProficiencyTest(Document):
	pass


def _load_template():
	path = Path(__file__).parent / "english_proficiency_test_template.json"
	return json.loads(path.read_text())


def _serialize_questions(rows):
	fields = (
		"sr_no",
		"question",
		"question_type",
		"option_1",
		"option_2",
		"option_3",
		"option_4",
		"option_5",
		"option_6",
	)
	return [{field: row.get(field) or "" for field in fields} for row in rows]


@frappe.whitelist()
def load_default_template(docname=None):
	template = _load_template()

	if docname and not str(docname).startswith("new-"):
		doc = frappe.get_doc("English Proficiency Test", docname)
	else:
		doc = frappe.new_doc("English Proficiency Test")

	doc.form_title = template["form_title"]
	doc.pass_percentage = template["pass_percentage"]
	doc.reading_title = template["reading_title"]
	doc.reading_passage = template["reading_passage"].replace("\n\n", "<br><br>")
	doc.questions = []
	for row in template["questions"]:
		doc.append(
			"questions",
			{
				"sr_no": row["sr_no"],
				"question": row["question"],
				"question_type": row["question_type"],
				"option_1": row["options"][0] if len(row["options"]) > 0 else "",
				"option_2": row["options"][1] if len(row["options"]) > 1 else "",
				"option_3": row["options"][2] if len(row["options"]) > 2 else "",
				"option_4": row["options"][3] if len(row["options"]) > 3 else "",
				"option_5": row["options"][4] if len(row["options"]) > 4 else "",
				"option_6": row["options"][5] if len(row["options"]) > 5 else "",
			},
		)

	if not doc.date_of_training:
		doc.date_of_training = today()

	if docname and not str(docname).startswith("new-"):
		doc.save()
		return doc.name

	return {
		"form_title": doc.form_title,
		"pass_percentage": doc.pass_percentage,
		"reading_title": doc.reading_title,
		"reading_passage": doc.reading_passage,
		"questions": _serialize_questions(doc.questions),
	}


@frappe.whitelist()
def populate_from_student_group(docname, student_group):
	docname = (docname or "").strip()
	if not docname or docname.startswith("new-"):
		frappe.throw("Please save the English Proficiency Test first.")
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
	doc = frappe.get_doc("English Proficiency Test", docname)
	doc.student_group = student_group
	doc.student = row.student
	doc.candidate_name = row.student_name or row.student
	doc.company_name = row.customer_name or frappe.db.get_value("Student", row.student, "custom_student_company_name") or ""
	doc.save()
	return doc.name
