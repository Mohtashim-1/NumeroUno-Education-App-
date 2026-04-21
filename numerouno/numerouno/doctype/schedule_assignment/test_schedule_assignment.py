# Copyright (c) 2026, mohtashim and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from numerouno.numerouno.doctype.schedule_assignment.schedule_assignment import (
	get_system_manager_emails,
)


class TestScheduleAssignment(FrappeTestCase):
	def test_validate_sets_defaults_and_sequences(self):
		doc = frappe.new_doc("Schedule Assignment")
		doc.schedule_date = "2026-04-16"
		doc.append(
			"entries",
			{
				"session": "Afternoon",
				"assignee_name": "JOSEPH",
				"assignment_details": "APLO/LIFTING SUPERVISOR",
			},
		)
		doc.append(
			"entries",
			{
				"session": "Morning",
				"sequence": 2,
				"assignee_name": "DILBAR",
				"assignment_details": "TFOET - FF/HUET/FA",
			},
		)
		doc.append(
			"entries",
			{
				"session": "Morning",
				"assignee_name": "NANDA",
				"assignment_details": "WMS@9AM",
			},
		)

		doc.run_method("validate")

		self.assertEqual(doc.schedule_title, "APR 16, 2026")
		self.assertTrue(doc.note_primary.startswith("NOTE: COURSE"))
		self.assertEqual([row.assignee_name for row in doc.entries], ["NANDA", "DILBAR", "JOSEPH"])
		self.assertEqual([row.sequence for row in doc.entries], [1, 2, 1])

	def test_get_system_manager_emails_returns_list(self):
		self.assertIsInstance(get_system_manager_emails(), list)
