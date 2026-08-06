import json
from pathlib import Path

import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt, today


class EnglishProficiencyTest(Document):
	def validate(self):
		ensure_question_correct_answers(self)
		compute_score_and_result(self)


def _load_template():
	path = Path(__file__).parent / "english_proficiency_test_template.json"
	return json.loads(path.read_text())


def _template_correct_answer_map():
	template = _load_template()
	return {
		str(cint(row.get("sr_no"))): (row.get("correct_answer") or "").strip()
		for row in template.get("questions") or []
		if row.get("sr_no") is not None
	}


def _normalize_answer(value):
	text = (value or "").strip()
	if not text:
		return ""
	return " ".join(text.lower().split())


def _answer_tokens(value):
	"""Split multi-select answers saved as 'A | B | C'."""
	raw = (value or "").strip()
	if not raw:
		return set()
	parts = [p.strip() for p in raw.split("|")]
	return {_normalize_answer(p) for p in parts if p.strip()}


def answer_is_correct(row, correct_map=None):
	selected = (row.get("selected_answer") if hasattr(row, "get") else getattr(row, "selected_answer", None)) or ""
	correct = (row.get("correct_answer") if hasattr(row, "get") else getattr(row, "correct_answer", None)) or ""
	if not correct and correct_map is not None:
		sr = str(cint(row.get("sr_no") if hasattr(row, "get") else getattr(row, "sr_no", 0)))
		correct = correct_map.get(sr) or ""
	if not selected or not correct:
		return False

	qtype = (row.get("question_type") if hasattr(row, "get") else getattr(row, "question_type", None)) or "Single Choice"
	if qtype == "Multiple Choice":
		selected_tokens = _answer_tokens(selected)
		correct_tokens = _answer_tokens(correct)
		# Exact option match OR selecting every individual option when key is "All of the Above"
		if selected_tokens == correct_tokens:
			return True
		if _normalize_answer(correct) == _normalize_answer("All of the Above"):
			options = []
			for i in range(1, 7):
				opt = row.get(f"option_{i}") if hasattr(row, "get") else getattr(row, f"option_{i}", None)
				if opt and _normalize_answer(opt) != _normalize_answer("All of the Above"):
					options.append(_normalize_answer(opt))
			if options and selected_tokens == set(options):
				return True
		return False

	return _normalize_answer(selected) == _normalize_answer(correct)


def ensure_question_correct_answers(doc):
	"""Backfill correct answers from the official template by question number."""
	correct_map = _template_correct_answer_map()
	for row in doc.questions or []:
		if not (row.correct_answer or "").strip():
			sr = str(cint(row.sr_no))
			if correct_map.get(sr):
				row.correct_answer = correct_map[sr]


def compute_score_and_result(doc):
	"""
	10 questions x 1 mark each.
	Pass when score percentage >= pass_percentage (default 80% => 8/10).
	"""
	rows = list(doc.questions or [])
	total = len(rows)
	if not total:
		doc.score = ""
		doc.result = ""
		return {"correct": 0, "total": 0, "percentage": 0, "result": ""}

	correct_map = _template_correct_answer_map()
	correct = 0
	for row in rows:
		if answer_is_correct(row, correct_map=correct_map):
			correct += 1

	percentage = (correct / total) * 100.0
	pass_mark = cint(doc.pass_percentage) or 80
	doc.score = f"{correct}/{total}"
	doc.result = "Pass" if percentage >= pass_mark else "Fail"
	return {
		"correct": correct,
		"total": total,
		"percentage": round(percentage, 2),
		"result": doc.result,
		"score": doc.score,
	}


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
		"correct_answer",
		"selected_answer",
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
				"correct_answer": row.get("correct_answer") or "",
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
				"correct_answer": row.get("correct_answer") or "",
				"selected_answer": selected,
			},
		)

	if answered < 1:
		frappe.throw("Please answer at least one question before submitting.")

	# Score/result are computed in validate(); submit so it is not left as Draft.
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	doc.submit()
	frappe.db.commit()

	return {
		"name": doc.name,
		"candidate_name": doc.candidate_name,
		"company_name": doc.company_name,
		"answered": answered,
		"total_questions": len(doc.questions or []),
		"score": doc.score,
		"result": doc.result,
		"pass_percentage": doc.pass_percentage,
		"docstatus": doc.docstatus,
		"message": "WMS Pretest submitted successfully.",
	}
