# Copyright (c) 2026, mohtashim and contributors
# For license information, please see license.txt

import frappe
import json
from pathlib import Path
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, formatdate, get_url_to_form


class ScheduleAssignment(Document):
	def validate(self):
		self.set_schedule_title()
		self.set_default_notes()
		self.populate_default_instructors()
		self.normalize_entries()

	def on_submit(self):
		self.email_schedule_to_system_managers()

	def set_schedule_title(self):
		if self.schedule_date:
			self.schedule_title = formatdate(self.schedule_date, "MMM dd, yyyy").upper()

	def set_default_notes(self):
		if not self.note_primary:
			self.note_primary = "NOTE: COURSE & ROOM ALLOCATION MAY CHANGE BASED ON REQUIREMENTS"

		if not self.note_secondary:
			self.note_secondary = (
				"TBA TRAINERS: PLEASE ATTEND ANY OF ABOVE REQUIRED TRAINING "
				"W/ ATTENDANCE SHEET & ASSESSMENT FOR YOUR RECORD"
			)

	def populate_default_instructors(self):
		if any(
			(row.instructor or "").strip()
			or (row.assignee_name or "").strip()
			or (row.assignment_details or "").strip()
			or (row.room_or_batch or "").strip()
			for row in self.entries
		):
			return

		self.entries = []

		for instructor in get_default_instructors():
			self.append(
				"entries",
				{
					"session": "Morning",
					"instructor": instructor.get("name"),
					"assignee_name": instructor.get("instructor_name"),
					# "assignment_details": "TBA",
				},
			)

	def normalize_entries(self):
		session_order = {"Morning": 0, "Afternoon": 1}

		for row in self.entries:
			row.session = row.session or "Morning"
			row.sequence = cint(row.sequence)
			row.assignment_details = (row.assignment_details or "").strip() or ""

			if row.instructor and not row.assignee_name:
				row.assignee_name = (
					frappe.db.get_value("Instructor", row.instructor, "instructor_name") or row.assignee_name
				)

		self.entries = sorted(
			self.entries,
			key=lambda row: (
				session_order.get(row.session, 99),
				cint(row.sequence or 0),
				(row.assignee_name or "").strip().lower(),
			),
		)

		session_counters = {"Morning": 0, "Afternoon": 0}
		for row in self.entries:
			session_counters.setdefault(row.session, 0)
			session_counters[row.session] += 1
			if not row.sequence:
				row.sequence = session_counters[row.session]

	def email_schedule_to_system_managers(self):
		recipients = get_system_manager_emails()
		if not recipients:
			return

		subject = _("Schedule Assignment {0} - {1}").format(
			self.name, formatdate(self.schedule_date, "MMM dd, yyyy")
		)
		doc_url = get_url_to_form(self.doctype, self.name)
		message = """
			<p>Schedule Assignment <strong>{name}</strong> has been submitted.</p>
			<p><strong>Date:</strong> {date}</p>
			<p><a href="{url}">Open Schedule Assignment</a></p>
		""".format(name=self.name, date=formatdate(self.schedule_date, "MMM dd, yyyy"), url=doc_url)

		try:
			frappe.sendmail(
				recipients=recipients,
				subject=subject,
				message=message,
				reference_doctype=self.doctype,
				reference_name=self.name,
				attachments=[
					frappe.attach_print(
						self.doctype,
						self.name,
						print_format="Schedule Assignment Sheet",
						print_letterhead=False,
					)
				],
			)
		except frappe.OutgoingEmailError:
			frappe.log_error(frappe.get_traceback(), "Schedule Assignment email failed")


@frappe.whitelist()
def get_default_instructors():
	return frappe.get_all(
		"Instructor",
		filters={"status": "Active"},
		fields=["name", "instructor_name"],
		order_by="instructor_name asc",
	)


def get_system_manager_emails():
	users = frappe.get_all(
		"Has Role",
		filters={"role": "System Manager", "parenttype": "User"},
		pluck="parent",
	)
	if not users:
		return []

	email_rows = frappe.get_all(
		"User",
		filters={
			"name": ["in", users],
			"enabled": 1,
			"user_type": "System User",
		},
		fields=["email"],
	)
	return list(dict.fromkeys(row.email for row in email_rows if row.email))


@frappe.whitelist()
def sync_schedule_assignment_print_format():
	json_path = (
		Path(frappe.get_app_path("numerouno"))
		/ "numerouno"
		/ "print_format"
		/ "schedule_assignment_sheet"
		/ "schedule_assignment_sheet.json"
	)
	data = json.loads(json_path.read_text())
	doc = frappe.get_doc("Print Format", "Schedule Assignment Sheet")
	doc.css = data.get("css") or ""
	doc.html = data.get("html") or ""
	doc.custom_format = data.get("custom_format") or 0
	doc.print_format_type = data.get("print_format_type") or "Jinja"
	doc.save(ignore_permissions=True)
	return {"name": doc.name, "modified": doc.modified}
