# Copyright (c) 2026, NumeroUNO and contributors
# License: MIT

"""Download Theory Assessment PDFs (summary + with questions) for non-ROSPA courses."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

THEORY_SUMMARY_FORMAT = "Theory Assessment Summary"
THEORY_QUESTIONS_FORMAT = "Theory Assesment"

_ALLOWED_ROLES = {
	"Academics User",
	"Education Manager",
	"Instructor",
	"Trainer",
	"Certification",
	"ADNOC Certificate View",
	"Training Coordinator",
	"Training Portal",
	"System Manager",
}


def _is_rospa_course(course: str) -> bool:
	return "rospa" in (course or "").strip().lower()


def _can_download(assessment_result: str, user: str, roles: list[str]) -> bool:
	if not assessment_result or not frappe.db.exists("Assessment Result", assessment_result):
		return False

	course = frappe.db.get_value("Assessment Result", assessment_result, "course") or ""
	if _is_rospa_course(course):
		return False

	if user in {"Administrator", "Guest"}:
		return user == "Administrator"

	if _ALLOWED_ROLES.intersection(roles):
		return True

	# Any instructor linked to the student group
	student_group = frappe.db.get_value(
		"Assessment Result", assessment_result, "student_group"
	)
	if not student_group:
		return False

	from numerouno.numerouno.page.instructor_portal.instructor_portal import (
		_get_instructor_names_for_user,
	)

	group_instructors = set(
		frappe.get_all(
			"Student Group Instructor",
			filters={"parent": student_group},
			pluck="instructor",
		)
	)
	return bool(group_instructors.intersection(_get_instructor_names_for_user(user)))


def _download_pdf(assessment_result: str, print_format: str, filename_suffix: str):
	assessment_result = (assessment_result or "").strip()
	if not assessment_result:
		frappe.throw(_("Assessment Result is required."))

	user = frappe.session.user
	roles = frappe.get_roles(user)

	if not _can_download(assessment_result, user, roles):
		frappe.throw(
			_(
				"You cannot download Theory Assessment for {0}. "
				"Login as Instructor/Trainer (ROSPA courses are excluded)."
			).format(assessment_result),
			frappe.PermissionError,
		)

	doc = frappe.get_doc("Assessment Result", assessment_result)

	prev_ignore = getattr(frappe.flags, "ignore_print_permissions", False)
	prev_docstatus = doc.docstatus
	frappe.flags.ignore_print_permissions = True
	# Cancelled / draft still printable for training records
	if cint(doc.docstatus) in (0, 2):
		doc.docstatus = 1
	try:
		pdf_file = frappe.get_print(
			"Assessment Result",
			assessment_result,
			print_format,
			doc=doc,
			as_pdf=True,
			no_letterhead=1,
		)
	finally:
		doc.docstatus = prev_docstatus
		frappe.flags.ignore_print_permissions = prev_ignore

	safe_name = assessment_result.replace(" ", "-").replace("/", "-")
	frappe.local.response.filename = f"{safe_name}-{filename_suffix}.pdf"
	frappe.local.response.filecontent = pdf_file
	frappe.local.response.type = "pdf"


@frappe.whitelist(methods=["GET", "POST"])
def download_theory_assessment_summary(assessment_result=None):
	"""Summary table (question IDs) + name / score / Pass-Fail — NUTC letterhead."""
	return _download_pdf(
		assessment_result, THEORY_SUMMARY_FORMAT, "Theory-Assessment-Summary"
	)


@frappe.whitelist(methods=["GET", "POST"])
def download_theory_assessment_questions(assessment_result=None):
	"""Full questions layout — NUTC letterhead."""
	return _download_pdf(
		assessment_result, THEORY_QUESTIONS_FORMAT, "Theory-Assessment-Questions"
	)
