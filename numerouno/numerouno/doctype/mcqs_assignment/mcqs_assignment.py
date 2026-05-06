# Copyright (c) 2025, mohtashim and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class MCQSAssignment(Document):
	def validate(self):
		if not self.assignment_flow:
			self.assignment_flow = "Direct MCQs"

		if self.assignment_flow != "Section Wise MCQs":
			self.quiz_section_profile = None
			return

		if not self.mcqs:
			frappe.throw(_("Select MCQS before using Section Wise MCQs."))

		if not self.quiz_section_profile:
			self.quiz_section_profile = frappe.db.exists("Quiz Section Profile", self.mcqs)

		if not self.quiz_section_profile:
			frappe.throw(
				_(
					"Create a Quiz Section Profile for quiz {0}, then select it here."
				).format(frappe.bold(self.mcqs))
			)

		profile_quiz = frappe.db.get_value(
			"Quiz Section Profile",
			self.quiz_section_profile,
			"quiz",
		)
		if profile_quiz != self.mcqs:
			frappe.throw(
				_(
					"Quiz Section Profile {0} belongs to quiz {1}, not {2}."
				).format(
					frappe.bold(self.quiz_section_profile),
					frappe.bold(profile_quiz),
					frappe.bold(self.mcqs),
				)
			)

		question_rows = frappe.get_all(
			"Quiz Question",
			filters={"parent": self.mcqs},
			fields=["custom_section_key"],
		)
		unmapped_count = len([row for row in question_rows if not (row.custom_section_key or "").strip()])
		if unmapped_count:
			frappe.throw(
				_(
					"{0} question row(s) in quiz {1} do not have Section Key. "
					"Open the Quiz and map every question row to a section key first."
				).format(unmapped_count, frappe.bold(self.mcqs))
			)
