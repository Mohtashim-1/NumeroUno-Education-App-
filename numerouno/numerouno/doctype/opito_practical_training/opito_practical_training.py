# Copyright (c) 2026, mohtashim and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class OPITOPracticalTraining(Document):
	pass


@frappe.whitelist()
def get_student_group_details(student_group):
	"""Return course and learner count for a Student Group (same pattern as other forms)."""
	student_group = (student_group or "").strip()
	if not student_group:
		return {"course": None, "total_learners": 0}

	course = frappe.db.get_value("Student Group", student_group, "course")
	total_learners = frappe.db.count("Student Group Student", {"parent": student_group})
	return {"course": course, "total_learners": total_learners}
