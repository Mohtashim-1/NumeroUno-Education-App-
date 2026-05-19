import frappe

from numerouno.numerouno.utils.assessment_eligibility import ensure_assessment_eligible


def validate_quiz_activity_eligibility(doc, method=None):
	if getattr(doc.flags, "skip_assessment_auto_create", False):
		return
	if getattr(doc.flags, "ignore_assessment_eligibility", False):
		return
	if doc.docstatus != 1:
		return
	if not doc.student:
		return

	student_group = getattr(doc, "custom_student_group", None)
	if not student_group:
		return

	ensure_assessment_eligible(doc.student, student_group, throw=True)
