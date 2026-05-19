import frappe

from numerouno.numerouno.utils.assessment_eligibility import ensure_assessment_eligible


def validate_assessment_eligibility(doc, method=None):
	if getattr(doc.flags, "ignore_assessment_eligibility", False):
		return
	if not doc.student:
		return

	student_group = doc.get("student_group")
	if not student_group:
		return

	ensure_assessment_eligible(doc.student, student_group, throw=True)
