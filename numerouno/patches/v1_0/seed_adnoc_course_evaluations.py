"""One-off: seed Course Evaluation records for ADNOC Q2123 candidates. Run via bench execute."""

import random

import frappe
from frappe.utils import getdate, today

COURSE = "ADNOC Defensive Driving for Light Vehicle (Q2123)"
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
SKILLS_CHOICES = ("Yes", "No", "Maybe")
RECOMMEND_CHOICES = ("Yes", "No", "Maybe")
DURATION_CHOICES = ("Too Long", "About Right", "Short")

COMMENTS = (
	"Well structured course.",
	"Good practical examples.",
	"Instructor was knowledgeable and helpful.",
	"Facilities were comfortable.",
	"Would attend similar training again.",
	"",
)


def execute(count=200, course=COURSE, submit=1):
	frappe.only_for("System Manager")
	count = int(count)
	submit = int(submit)

	pairs = frappe.db.sql(
		"""
		SELECT
			sgs.student AS trainee_name,
			sgs.parent AS student_group,
			sg.from_date,
			sg.course,
			(
				SELECT sgi.instructor
				FROM `tabStudent Group Instructor` sgi
				WHERE sgi.parent = sg.name
				ORDER BY sgi.idx ASC
				LIMIT 1
			) AS instructor_name
		FROM `tabStudent Group Student` sgs
		INNER JOIN `tabStudent Group` sg ON sg.name = sgs.parent
		WHERE sg.course = %(course)s
		  AND NOT EXISTS (
			SELECT 1
			FROM `tabCourse Evaluation` ce
			WHERE ce.trainee_name = sgs.student
			  AND ce.student_group = sgs.parent
		  )
		ORDER BY sg.from_date DESC, sgs.parent ASC, sgs.student ASC
		LIMIT %(limit)s
		""",
		{"course": course, "limit": count},
		as_dict=True,
	)

	if not pairs:
		return {"created": 0, "message": "No candidate/group pairs without an evaluation."}

	company = DEFAULT_COMPANY
	if not frappe.db.exists("Company", company):
		company = frappe.db.get_value("Company", {}, "name") or ""

	created = []
	errors = []

	for row in pairs:
		try:
			student_row = frappe.db.get_value(
				"Student",
				row.trainee_name,
				["student_email_id", "custom_phone"],
				as_dict=True,
			) or {}

			doc = frappe.new_doc("Course Evaluation")
			doc.naming_series = "CE-.MM.-.#."
			doc.course_name = row.course or course
			doc.company = company
			doc.instructor_name = row.instructor_name or ""
			doc.dates = getdate(row.from_date) if row.from_date else today()
			doc.trainee_name = row.trainee_name
			doc.student_group = row.student_group
			doc.email_id = student_row.get("student_email_id") or ""
			doc.trainee_mobile = student_row.get("custom_phone") or ""

			for field in RATING_FIELDS:
				doc.set(field, random.choice(RATING_CHOICES))

			doc.skills_improve_job_performance = random.choice(SKILLS_CHOICES)
			doc.recommend_course = random.choice(RECOMMEND_CHOICES)
			doc.course_duration = random.choice(DURATION_CHOICES)
			doc.additional_comments = random.choice(COMMENTS)

			doc.flags.ignore_permissions = True
			doc.insert()

			if submit:
				doc.submit()

			created.append(doc.name)
			if len(created) % 25 == 0:
				frappe.db.commit()
		except Exception as e:
			errors.append({"trainee": row.trainee_name, "group": row.student_group, "error": str(e)})
			frappe.db.rollback()

	frappe.db.commit()

	return {
		"course": course,
		"requested": count,
		"created": len(created),
		"sample_names": created[:5],
		"errors": errors[:10],
		"error_count": len(errors),
	}
