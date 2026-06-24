# Copyright (c) 2026, mohtashim and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_months, getdate, now_datetime, strip_html, today


RETEST_VALIDITY_MONTHS = 3
DEFAULT_OUTCOME_ROWS = 12
DECLARATION_TEXT = (
	"Declaration: The person named was reassessed by me against the standards of "
	"performance specified in this document and in accordance with the assessment guidance."
)


class NYCReassessmentChecklist(Document):
	def validate(self):
		self._set_retest_validity()
		self._set_retest_status()
		self._ensure_outcome_rows()

	def on_submit(self):
		if self.retest_status == "Expired":
			frappe.throw(_("Cannot submit an expired NYC Reassessment Checklist."))
		if getdate(today()) > getdate(self.retest_valid_until):
			frappe.throw(_("Retest validity period has expired (3 months from first assessment)."))

	def _set_retest_validity(self):
		if self.first_assessment_date:
			self.retest_valid_until = add_months(getdate(self.first_assessment_date), RETEST_VALIDITY_MONTHS)

	def _set_retest_status(self):
		if self.docstatus == 1 and self.reassessment_date:
			self.retest_status = "Reassessed"
			return

		if not self.retest_valid_until:
			self.retest_status = "Eligible"
			return

		if getdate(today()) > getdate(self.retest_valid_until):
			self.retest_status = "Expired"
		else:
			self.retest_status = "Eligible"

	def _ensure_outcome_rows(self):
		while len(self.outcomes or []) < DEFAULT_OUTCOME_ROWS:
			idx = len(self.outcomes or []) + 1
			self.append("outcomes", {"ref_no": idx})


def _pad_outcomes(doc):
	while len(doc.outcomes or []) < DEFAULT_OUTCOME_ROWS:
		idx = len(doc.outcomes or []) + 1
		doc.append("outcomes", {"ref_no": idx})


def _plain_text(value):
	"""Convert rich-text/HTML question content to readable plain text."""
	if not value:
		return ""
	return re.sub(r"\s+", " ", strip_html(str(value))).strip()


def _student_company_name(student, student_group=None):
	if student_group:
		company = frappe.db.get_value(
			"Student Group Student",
			{"parent": student_group, "student": student},
			"customer_name",
		)
		if company:
			return company
	return frappe.db.get_value("Student", student, "custom_student_company_name") or ""


def _wrong_quiz_outcomes(quiz_activity_name):
	rows = frappe.get_all(
		"Quiz Result",
		filters={"parent": quiz_activity_name, "parenttype": "Quiz Activity", "quiz_result": "Wrong"},
		fields=["question", "selected_option"],
		order_by="idx asc",
	)
	outcomes = []
	details = []
	for idx, row in enumerate(rows, start=1):
		question_text = _plain_text(frappe.db.get_value("Question", row.question, "question") or row.question)
		outcomes.append(
			{
				"ref_no": idx,
				"learning_outcome": question_text,
				"source_of_evidence": "Theory Assessment",
				"remarks": f"Selected: {row.selected_option or '-'}",
			}
		)
		details.append(f"{idx}. {question_text}")
	return outcomes, details


def _assessment_result_is_nyc(assessment_result_name):
	result = frappe.db.get_value(
		"Assessment Result",
		assessment_result_name,
		["total_score", "maximum_score", "grade"],
		as_dict=True,
	)
	if not result:
		return False
	grade = (result.grade or "").strip().upper()
	if grade in {"F", "FAIL", "NYC", "NOT YET COMPETENT"}:
		return True
	if result.maximum_score and result.total_score is not None:
		percentage = (float(result.total_score) / float(result.maximum_score)) * 100
		return percentage < 75
	return False


def get_retest_eligibility(first_assessment_date, as_of_date=None):
	as_of_date = getdate(as_of_date or today())
	first_date = getdate(first_assessment_date)
	valid_until = add_months(first_date, RETEST_VALIDITY_MONTHS)
	eligible = as_of_date <= valid_until
	return {
		"eligible": eligible,
		"first_assessment_date": str(first_date),
		"retest_valid_until": str(valid_until),
		"days_remaining": max((valid_until - as_of_date).days, 0) if eligible else 0,
		"message": (
			_("Retest is allowed until {0}.").format(frappe.utils.formatdate(valid_until))
			if eligible
			else _("Retest period expired on {0}. Candidate cannot retest after 3 months.").format(
				frappe.utils.formatdate(valid_until)
			)
		),
	}


def _find_existing_checklist(filters):
	return frappe.db.get_value(
		"NYC Reassessment Checklist",
		{**filters, "docstatus": ["<", 2]},
		"name",
		order_by="creation desc",
	)


def _build_from_quiz_activity(quiz_activity_name):
	activity = frappe.get_doc("Quiz Activity", quiz_activity_name)
	if (activity.status or "").strip() != "Fail":
		frappe.throw(_("NYC Reassessment Checklist can only be created for failed quiz attempts."))

	student_group = getattr(activity, "custom_student_group", None)
	course = activity.course
	course_name = frappe.db.get_value("Course", course, "course_name") if course else activity.quiz
	if student_group and not course:
		course = frappe.db.get_value("Student Group", student_group, "course")

	first_dt = activity.activity_date or getdate(activity.creation)
	first_time = activity.creation.time() if activity.creation else None
	wrong_outcomes, wrong_details = _wrong_quiz_outcomes(quiz_activity_name)
	assessment_result = getattr(activity, "custom_assesment_result", None)

	doc = frappe.new_doc("NYC Reassessment Checklist")
	doc.student = activity.student
	doc.candidate_name = frappe.db.get_value("Student", activity.student, "student_name")
	doc.company_name = _student_company_name(activity.student, student_group)
	doc.student_group = student_group
	doc.course = course
	doc.course_name = course_name or activity.quiz
	doc.quiz_activity = quiz_activity_name
	doc.assessment_result = assessment_result
	doc.first_assessment_date = first_dt
	doc.first_assessment_time = first_time
	doc.assessor_name = frappe.db.get_value("Instructor", {"custom_email": activity.owner}, "instructor_name") or activity.owner
	doc.declaration_text = DECLARATION_TEXT

	score_text = activity.score or ""
	nyc_summary = f"<p><strong>Theory assessment result:</strong> Fail ({frappe.utils.escape_html(score_text)})</p>"
	if wrong_details:
		nyc_summary += "<p><strong>Learning outcomes / questions marked wrong:</strong></p><ul>"
		for item in wrong_details:
			nyc_summary += f"<li>{frappe.utils.escape_html(item)}</li>"
		nyc_summary += "</ul>"
	doc.nyc_details = nyc_summary

	for row in wrong_outcomes:
		doc.append("outcomes", row)
	_pad_outcomes(doc)
	doc._set_retest_validity()
	doc._set_retest_status()
	return doc


def _build_from_assessment_result(assessment_result_name):
	if not _assessment_result_is_nyc(assessment_result_name):
		frappe.throw(_("Assessment Result is not marked as Not Yet Competent / Fail."))

	result = frappe.get_doc("Assessment Result", assessment_result_name)
	first_dt = getdate(result.creation)
	doc = frappe.new_doc("NYC Reassessment Checklist")
	doc.student = result.student
	doc.candidate_name = result.student_name
	doc.company_name = result.customer_name or _student_company_name(result.student, result.student_group)
	doc.student_group = result.student_group
	doc.course = result.course
	doc.course_name = frappe.db.get_value("Course", result.course, "course_name") if result.course else result.course
	doc.assessment_result = assessment_result_name
	doc.first_assessment_date = first_dt
	doc.assessor_name = result.instructor
	doc.declaration_text = DECLARATION_TEXT

	details = frappe.get_all(
		"Assessment Result Detail",
		filters={"parent": assessment_result_name},
		fields=["assessment_criteria", "score", "maximum_score", "grade"],
		order_by="idx asc",
	)
	nyc_lines = []
	ref = 1
	for row in details:
		max_score = float(row.maximum_score or 0)
		score = float(row.score or 0)
		if max_score and score >= max_score:
			continue
		label = row.assessment_criteria or "Assessment Criteria"
		nyc_lines.append(f"{ref}. {label} (Score: {score}/{max_score})")
		doc.append(
			"outcomes",
			{
				"ref_no": ref,
				"learning_outcome": label,
				"source_of_evidence": "Assessment Result",
				"remarks": f"Score: {score}/{max_score}",
			},
		)
		ref += 1

	if not nyc_lines:
		nyc_lines.append(
			f"Overall assessment result: {result.total_score}/{result.maximum_score} (Grade: {result.grade or 'Fail'})"
		)
	doc.nyc_details = "<p><strong>Assessment result NYC details:</strong></p><ul>"
	for line in nyc_lines:
		doc.nyc_details += f"<li>{frappe.utils.escape_html(line)}</li>"
	doc.nyc_details += "</ul>"

	_pad_outcomes(doc)
	doc._set_retest_validity()
	doc._set_retest_status()
	return doc


@frappe.whitelist()
def create_from_quiz_activity(quiz_activity_name):
	quiz_activity_name = (quiz_activity_name or "").strip()
	if not quiz_activity_name:
		frappe.throw(_("Quiz Activity is required"))

	existing = _find_existing_checklist({"quiz_activity": quiz_activity_name})
	if existing:
		return {"name": existing, "existing": True}

	doc = _build_from_quiz_activity(quiz_activity_name)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name, "existing": False, "retest_status": doc.retest_status, "retest_valid_until": doc.retest_valid_until}


@frappe.whitelist()
def create_from_assessment_result(assessment_result_name):
	assessment_result_name = (assessment_result_name or "").strip()
	if not assessment_result_name:
		frappe.throw(_("Assessment Result is required"))

	existing = _find_existing_checklist({"assessment_result": assessment_result_name})
	if existing:
		return {"name": existing, "existing": True}

	doc = _build_from_assessment_result(assessment_result_name)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name, "existing": False, "retest_status": doc.retest_status, "retest_valid_until": doc.retest_valid_until}


@frappe.whitelist()
def get_retest_status_for_activity(quiz_activity_name=None, assessment_result_name=None):
	quiz_activity_name = (quiz_activity_name or "").strip()
	assessment_result_name = (assessment_result_name or "").strip()

	checklist_name = None
	first_assessment_date = None
	if quiz_activity_name:
		checklist_name = _find_existing_checklist({"quiz_activity": quiz_activity_name})
		if not first_assessment_date:
			activity = frappe.db.get_value(
				"Quiz Activity",
				quiz_activity_name,
				["activity_date", "creation", "status"],
				as_dict=True,
			)
			if activity:
				first_assessment_date = activity.activity_date or getdate(activity.creation)
	elif assessment_result_name:
		checklist_name = _find_existing_checklist({"assessment_result": assessment_result_name})
		first_assessment_date = frappe.db.get_value("Assessment Result", assessment_result_name, "creation")
		if first_assessment_date:
			first_assessment_date = getdate(first_assessment_date)

	eligibility = get_retest_eligibility(first_assessment_date) if first_assessment_date else {
		"eligible": True,
		"retest_valid_until": None,
		"days_remaining": None,
		"message": "",
	}

	if checklist_name:
		checklist = frappe.db.get_value(
			"NYC Reassessment Checklist",
			checklist_name,
			["name", "retest_status", "retest_valid_until"],
			as_dict=True,
		)
		return {
			"checklist": checklist.name,
			"retest_status": checklist.retest_status,
			"retest_valid_until": checklist.retest_valid_until,
			**eligibility,
		}

	return {
		"checklist": None,
		"retest_status": "Eligible" if eligibility.get("eligible") else "Expired",
		"retest_valid_until": eligibility.get("retest_valid_until"),
		**eligibility,
	}


def check_retest_allowed(student, student_group, quiz_name=None):
	"""Return retest eligibility without throwing."""
	filters = {"student": student, "status": "Fail", "docstatus": ["<", 2]}
	if quiz_name:
		filters["quiz"] = quiz_name

	failed_activities = frappe.get_all(
		"Quiz Activity",
		filters=filters,
		fields=["name", "activity_date", "creation", "quiz"],
		order_by="creation asc",
		limit=1,
	)
	if not failed_activities:
		return {"allowed": True, "eligible": True, "message": ""}

	first = failed_activities[0]
	first_date = first.activity_date or getdate(first.creation)
	eligibility = get_retest_eligibility(first_date)
	return {
		"allowed": eligibility.get("eligible"),
		"eligible": eligibility.get("eligible"),
		"first_assessment_date": eligibility.get("first_assessment_date"),
		"retest_valid_until": eligibility.get("retest_valid_until"),
		"days_remaining": eligibility.get("days_remaining"),
		"message": eligibility.get("message"),
		"first_failed_activity": first.name,
	}


def ensure_retest_allowed(student, student_group, quiz_name=None):
	"""Block retest attempts after 3 months from the first failed quiz activity."""
	result = check_retest_allowed(student, student_group, quiz_name)
	if not result.get("allowed"):
		frappe.throw(result.get("message"), title=_("Retest Not Allowed"))
	return True
