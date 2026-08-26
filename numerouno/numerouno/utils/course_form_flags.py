"""Course flags that control which forms appear on the instructor portal."""

from __future__ import annotations

import frappe
from frappe.utils import cint


FLAG_SAFETY_BRIEFING = "custom_safety_briefing_required"
FLAG_ASSESSOR_CHECKLIST = "custom_course_assessor_checklist_required"
FLAG_ROSPA = "custom_rospa_required"

FLAG_FIELDS = (
	FLAG_SAFETY_BRIEFING,
	FLAG_ASSESSOR_CHECKLIST,
	FLAG_ROSPA,
)

FORM_KEY_TO_FLAG = {
	"safety_briefing": FLAG_SAFETY_BRIEFING,
	"assessor_checklist": FLAG_ASSESSOR_CHECKLIST,
	"rospa": FLAG_ROSPA,
	"rospa_practical": FLAG_ROSPA,
	"rospa_learning_outcome": FLAG_ROSPA,
}

PDF_KEY_TO_FLAG = {
	"safety_briefing": FLAG_SAFETY_BRIEFING,
	"assessor_checklist": FLAG_ASSESSOR_CHECKLIST,
	"course_assessor_checklist": FLAG_ASSESSOR_CHECKLIST,
	"rospa_practical": FLAG_ROSPA,
	"rospa_learning_outcome": FLAG_ROSPA,
}


def empty_form_flags():
	return {
		"safety_briefing": 0,
		"assessor_checklist": 0,
		"rospa": 0,
	}


def _has_flag_columns():
	try:
		return frappe.db.has_column("Course", FLAG_SAFETY_BRIEFING)
	except Exception:
		return False


def flags_for_courses(courses):
	flags = empty_form_flags()
	courses = [name for name in (courses or []) if name]
	if not courses or not _has_flag_columns():
		return flags

	rows = frappe.get_all(
		"Course",
		filters={"name": ["in", list(set(courses))]},
		fields=["name", *FLAG_FIELDS],
	)
	for row in rows:
		if cint(row.get(FLAG_SAFETY_BRIEFING)):
			flags["safety_briefing"] = 1
		if cint(row.get(FLAG_ASSESSOR_CHECKLIST)):
			flags["assessor_checklist"] = 1
		if cint(row.get(FLAG_ROSPA)):
			flags["rospa"] = 1
	return flags


def course_has_flag(course, flag_field):
	course = (course or "").strip()
	if not course or flag_field not in FLAG_FIELDS or not _has_flag_columns():
		return 0
	return cint(frappe.db.get_value("Course", course, flag_field))


def _flagged_course_names(flag_field):
	if flag_field not in FLAG_FIELDS or not _has_flag_columns():
		return []
	return frappe.get_all("Course", filters={flag_field: 1}, pluck="name") or []


def flags_for_student_groups(student_group_names):
	"""OR the course flags for the given student groups.

	``None`` means no group restriction (e.g. System Manager): any flagged
	course in the system turns the matching portal tab on.
	"""
	if student_group_names == []:
		return empty_form_flags()

	if student_group_names is None:
		flags = empty_form_flags()
		if not _has_flag_columns():
			return flags
		if frappe.db.exists("Course", {FLAG_SAFETY_BRIEFING: 1}):
			flags["safety_briefing"] = 1
		if frappe.db.exists("Course", {FLAG_ASSESSOR_CHECKLIST: 1}):
			flags["assessor_checklist"] = 1
		if frappe.db.exists("Course", {FLAG_ROSPA: 1}):
			flags["rospa"] = 1
		return flags

	courses = frappe.get_all(
		"Student Group",
		filters={"name": ["in", list(student_group_names)]},
		pluck="course",
		distinct=True,
	)
	return flags_for_courses(courses)


def resolve_form_flags(course=None, student_group=None, student_group_names=None):
	course = (course or "").strip()
	student_group = (student_group or "").strip()
	if course:
		return flags_for_courses([course])
	if student_group:
		group_course = frappe.db.get_value("Student Group", student_group, "course")
		return flags_for_courses([group_course] if group_course else [])
	return flags_for_student_groups(student_group_names)


def filter_student_groups_by_flag(student_group_names, flag_field):
	"""Keep only student groups whose course has ``flag_field`` checked."""
	if student_group_names == []:
		return []

	flagged_courses = _flagged_course_names(flag_field)
	if not flagged_courses:
		return []

	filters = {"course": ["in", flagged_courses]}
	if student_group_names is not None:
		filters["name"] = ["in", list(student_group_names)]
	return frappe.get_all("Student Group", filters=filters, pluck="name") or []


def filter_group_rows_by_flag(groups, flag_field):
	if not groups:
		return []
	flagged_courses = set(_flagged_course_names(flag_field))
	if not flagged_courses:
		return []
	return [row for row in groups if (row.get("course") or "") in flagged_courses]


def catalog_key_allowed(key, student_group=None, student=None):
	"""Whether a PDF-bundle / catalog key should be listed for this selection."""
	flag_field = PDF_KEY_TO_FLAG.get(key)
	if not flag_field:
		return True

	courses = []
	student_group = (student_group or "").strip()
	student = (student or "").strip()
	if student_group:
		course = frappe.db.get_value("Student Group", student_group, "course")
		if course:
			courses.append(course)
	elif student:
		group_names = frappe.get_all(
			"Student Group Student",
			filters={"student": student, "active": 1},
			pluck="parent",
		)
		if group_names:
			courses.extend(
				frappe.get_all(
					"Student Group",
					filters={"name": ["in", group_names]},
					pluck="course",
					distinct=True,
				)
			)

	if not courses:
		return False
	return any(course_has_flag(course, flag_field) for course in courses if course)


def row_catalog_key_allowed(key, student_group=None):
	flag_field = PDF_KEY_TO_FLAG.get(key)
	if not flag_field:
		return True
	student_group = (student_group or "").strip()
	if not student_group:
		return False
	course = frappe.db.get_value("Student Group", student_group, "course")
	return bool(course_has_flag(course, flag_field))
