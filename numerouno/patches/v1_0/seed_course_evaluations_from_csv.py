"""Create Course Evaluations from Student Group Analytics CSV export."""

import csv
import os
import random
import re

import frappe
from frappe.utils import getdate, today

DEFAULT_COMPANY = "Numero Uno Training and Consulting LLC"

RATING_FIELDS = (
	"joining_instructions_clear",
	"training_room_environment",
	"administration_support",
	"objectives_clearly_defined",
	"content_organization",
	"materials_aligned",
	"course_pace",
	"presentation_skills",
	"teaching_effectiveness",
	"knowledge_accessibility",
	"assignments_exercises",
	"handouts_tools_equipment",
	"technology_effectiveness",
)

RATING_CHOICES = (0.6, 0.8, 1.0)


def _normalize_name(name):
	if not name:
		return ""
	return re.sub(r"\s+", " ", str(name).strip().upper())


def _parse_course_date(value):
	if not value:
		return today()
	value = str(value).strip()
	for fmt in ("%d-%m-%y", "%d-%m-%Y", "%Y-%m-%d"):
		try:
			return getdate(value)
		except Exception:
			continue
	return today()


def _resolve_csv_path(file_name=None, file_id=None):
	if file_id:
		path = frappe.db.get_value("File", file_id, "file_url")
		if path:
			file_name = path
	if not file_name:
		file_name = "/files/Student Group Analytics_2026-04-01_2026-09-17.csv"
	if file_name.startswith("/files/"):
		return os.path.join(frappe.get_site_path("public", "files"), os.path.basename(file_name))
	return file_name


def _find_student_in_group(student_group, student_name):
	norm = _normalize_name(student_name)
	if not norm:
		return None

	rows = frappe.db.sql(
		"""
		SELECT sgs.student, st.student_name
		FROM `tabStudent Group Student` sgs
		INNER JOIN `tabStudent` st ON st.name = sgs.student
		WHERE sgs.parent = %(group)s
		""",
		{"group": student_group},
		as_dict=True,
	)
	for row in rows:
		if _normalize_name(row.student_name) == norm:
			return row.student

	# Loose match: CSV name contained in student name or vice versa
	for row in rows:
		st_norm = _normalize_name(row.student_name)
		if norm in st_norm or st_norm in norm:
			return row.student
	return None


def _group_instructor(student_group):
	row = frappe.db.sql(
		"""
		SELECT instructor, instructor_name
		FROM `tabStudent Group Instructor`
		WHERE parent = %(parent)s
		ORDER BY idx ASC
		LIMIT 1
		""",
		{"parent": student_group},
		as_dict=True,
	)
	if not row:
		return ""
	return row[0].get("instructor") or row[0].get("instructor_name") or ""


def execute(file_id=None, file_name=None, submit=1):
	frappe.only_for("System Manager")
	submit = int(submit)
	csv_path = _resolve_csv_path(file_name=file_name, file_id=file_id)
	if not os.path.isfile(csv_path):
		frappe.throw(f"CSV not found: {csv_path}")

	company = DEFAULT_COMPANY
	if not frappe.db.exists("Company", company):
		company = frappe.db.get_value("Company", {}, "name") or ""

	created = []
	skipped = []
	errors = []

	with open(csv_path, newline="", encoding="utf-8-sig") as handle:
		reader = csv.DictReader(handle)
		for row in reader:
			student_group = (row.get("Attendence Ref No") or row.get("Attendance Ref No") or "").strip()
			student_name_csv = (row.get("Student Name") or "").strip()
			course_name = (row.get("Course Name") or "").strip()

			if not student_group or not student_name_csv:
				skipped.append({"row": row, "reason": "missing group or student name"})
				continue

			if not frappe.db.exists("Student Group", student_group):
				skipped.append({"group": student_group, "student": student_name_csv, "reason": "invalid group"})
				continue

			trainee = _find_student_in_group(student_group, student_name_csv)
			if not trainee:
				skipped.append({"group": student_group, "student": student_name_csv, "reason": "student not in group"})
				continue

			if frappe.db.exists(
				"Course Evaluation",
				{"trainee_name": trainee, "student_group": student_group, "docstatus": ["!=", 2]},
			):
				skipped.append({"group": student_group, "student": trainee, "reason": "evaluation exists"})
				continue

			try:
				student_row = frappe.db.get_value(
					"Student",
					trainee,
					["student_email_id", "custom_phone"],
					as_dict=True,
				) or {}

				doc = frappe.new_doc("Course Evaluation")
				doc.naming_series = "CE-.MM.-.#."
				doc.student_group = student_group
				doc.trainee_name = trainee
				doc.course_name = course_name or frappe.db.get_value("Student Group", student_group, "course")
				doc.company = company
				doc.instructor_name = _group_instructor(student_group)
				doc.dates = _parse_course_date(row.get("Course Date"))
				doc.email_id = student_row.get("student_email_id") or ""
				doc.trainee_mobile = student_row.get("custom_phone") or ""

				for field in RATING_FIELDS:
					doc.set(field, random.choice(RATING_CHOICES))

				doc.skills_improve_job_performance = random.choice(("Yes", "No", "Maybe"))
				doc.recommend_course = random.choice(("Yes", "No", "Maybe"))
				doc.course_duration = random.choice(("Too Long", "About Right", "Short"))

				doc.flags.ignore_permissions = True
				doc.insert()
				if submit:
					doc.submit()

				created.append(doc.name)
				if len(created) % 25 == 0:
					frappe.db.commit()
			except Exception as e:
				errors.append(
					{"group": student_group, "student": trainee, "error": str(e)},
				)
				frappe.db.rollback()

	frappe.db.commit()

	return {
		"csv_path": csv_path,
		"created": len(created),
		"sample_names": created[:10],
		"skipped_count": len(skipped),
		"skipped_sample": skipped[:15],
		"errors": errors[:10],
		"error_count": len(errors),
	}
