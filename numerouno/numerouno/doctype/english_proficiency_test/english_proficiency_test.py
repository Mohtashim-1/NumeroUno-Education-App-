import json
from pathlib import Path

import frappe
from frappe.model.document import Document
from frappe.utils import cint, today


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
	doc.company_name = (
		row.customer_name
		or frappe.db.get_value("Student", row.student, "custom_student_company_name")
		or ""
	)
	doc.save()
	return doc.name


@frappe.whitelist(allow_guest=True)
def get_wms_pretest_portal():
	"""Public WMS pretest form template for guests (no login)."""
	template = _load_template()
	questions = []
	for row in template.get("questions") or []:
		questions.append(
			{
				"sr_no": row.get("sr_no"),
				"question": row.get("question") or "",
				"question_type": row.get("question_type") or "Single Choice",
				"options": [opt for opt in (row.get("options") or []) if (opt or "").strip()],
			}
		)

	return {
		"form_title": template.get("form_title")
		or "English Language Proficiency Assessment V01 '21 WMS Pre-Requisite",
		"pass_percentage": template.get("pass_percentage") or 80,
		"reading_title": template.get("reading_title") or "",
		"reading_passage": (template.get("reading_passage") or "").replace("\n\n", "<br><br>"),
		"date_of_training": today(),
		"questions": questions,
	}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def submit_wms_pretest_portal(data=None):
	"""Create an English Proficiency Test from the public WMS pretest portal."""
	payload = frappe.parse_json(data) if isinstance(data, str) else (data or {})
	if isinstance(payload, str):
		payload = frappe.parse_json(payload) or {}

	candidate_name = (payload.get("candidate_name") or "").strip()
	company_name = (payload.get("company_name") or "").strip()
	date_of_training = payload.get("date_of_training") or today()
	answers = payload.get("answers") or {}

	if not candidate_name:
		frappe.throw("Candidate name is required.")
	if not company_name:
		frappe.throw("Company name is required.")

	template = _load_template()
	doc = frappe.new_doc("English Proficiency Test")
	doc.form_title = (
		template.get("form_title")
		or "English Language Proficiency Assessment V01 '21 WMS Pre-Requisite"
	)
	doc.pass_percentage = template.get("pass_percentage") or 80
	doc.reading_title = template.get("reading_title") or ""
	doc.reading_passage = (template.get("reading_passage") or "").replace("\n\n", "<br><br>")
	doc.date_of_training = date_of_training
	doc.candidate_name = candidate_name
	doc.company_name = company_name

	answered = 0
	for row in template.get("questions") or []:
		sr_no = str(row.get("sr_no") or "")
		selected = answers.get(sr_no)
		if selected is None:
			selected = answers.get(str(cint(sr_no)))
		if isinstance(selected, list):
			selected = " | ".join([str(v).strip() for v in selected if str(v).strip()])
		else:
			selected = str(selected or "").strip()
		if selected:
			answered += 1

		options = row.get("options") or []
		doc.append(
			"questions",
			{
				"sr_no": row.get("sr_no"),
				"question": row.get("question"),
				"question_type": row.get("question_type") or "Single Choice",
				"option_1": options[0] if len(options) > 0 else "",
				"option_2": options[1] if len(options) > 1 else "",
				"option_3": options[2] if len(options) > 2 else "",
				"option_4": options[3] if len(options) > 3 else "",
				"option_5": options[4] if len(options) > 4 else "",
				"option_6": options[5] if len(options) > 5 else "",
				"selected_answer": selected,
			},
		)

	if answered < 1:
		frappe.throw("Please answer at least one question before submitting.")

	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	frappe.db.commit()

	return {
		"name": doc.name,
		"candidate_name": doc.candidate_name,
		"company_name": doc.company_name,
		"answered": answered,
		"total_questions": len(doc.questions or []),
		"message": "WMS Pretest submitted successfully.",
	}
