"""Convert legacy Select labels on Course Evaluation to Rating decimals before column type change."""

import frappe

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

LABEL_TO_RATING = {
	"Excellent": "1",
	"Good": "0.8",
	"Average": "0.6",
	"Poor": "0.2",
}


def execute():
	if not frappe.db.table_exists("Course Evaluation"):
		return

	for fieldname in RATING_FIELDS:
		if not frappe.db.has_column("Course Evaluation", fieldname):
			continue
		for label, rating in LABEL_TO_RATING.items():
			frappe.db.sql(
				f"""
				UPDATE `tabCourse Evaluation`
				SET `{fieldname}` = %(rating)s
				WHERE `{fieldname}` = %(label)s
				""",
				{"rating": rating, "label": label},
			)
		frappe.db.sql(
			f"""
			UPDATE `tabCourse Evaluation`
			SET `{fieldname}` = NULL
			WHERE `{fieldname}` = '' OR `{fieldname}` IS NULL
			""",
		)
		# Any leftover non-numeric text (unexpected labels)
		frappe.db.sql(
			f"""
			UPDATE `tabCourse Evaluation`
			SET `{fieldname}` = NULL
			WHERE `{fieldname}` IS NOT NULL
			  AND `{fieldname}` NOT REGEXP '^[0-9]+(\\\\.[0-9]+)?$'
			""",
		)

	frappe.db.commit()
