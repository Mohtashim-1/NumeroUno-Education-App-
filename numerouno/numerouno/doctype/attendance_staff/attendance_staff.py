# Copyright (c) 2026, mohtashim and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr


DEFAULT_STAFF_ROLES = [
	"Lead Instructor",
	"Diver",
	"Trainee Crane Operator",
	"Crane Operator",
	"Pool Safety Person",
]


class AttendanceStaff(Document):
	def validate(self):
		self._sync_staff_name()
		self._ensure_staff_roles()

	def _sync_staff_name(self):
		if self.employee:
			self.staff_name = frappe.db.get_value("Employee", self.employee, "employee_name")

	def _ensure_staff_roles(self):
		if not self.staff_roles:
			self.staff_roles = ", ".join(DEFAULT_STAFF_ROLES)


def sync_attendance_staff_from_employee(employee_doc):
	"""Create or update Attendance Staff when an Employee is saved."""
	if not employee_doc.name:
		return

	if employee_doc.status and employee_doc.status != "Active":
		if frappe.db.exists("Attendance Staff", employee_doc.name):
			frappe.db.set_value("Attendance Staff", employee_doc.name, "active", 0, update_modified=False)
		return

	staff_name = employee_doc.employee_name or employee_doc.name
	company = employee_doc.company

	if frappe.db.exists("Attendance Staff", employee_doc.name):
		frappe.db.set_value(
			"Attendance Staff",
			employee_doc.name,
			{
				"staff_name": staff_name,
				"company": company,
				"active": 1,
				"employee": employee_doc.name,
			},
			update_modified=True,
		)
		return

	doc = frappe.get_doc(
		{
			"doctype": "Attendance Staff",
			"name": employee_doc.name,
			"employee": employee_doc.name,
			"staff_name": staff_name,
			"company": company,
			"active": 1,
			"staff_roles": ", ".join(DEFAULT_STAFF_ROLES),
		}
	)
	doc.insert(ignore_permissions=True)


def create_attendance_staff_for_all_employees():
	employees = frappe.get_all(
		"Employee",
		filters={"status": "Active"},
		fields=["name", "employee_name", "company", "status"],
	)
	created = 0
	updated = 0

	for employee in employees:
		if frappe.db.exists("Attendance Staff", employee.name):
			sync_attendance_staff_from_employee(frappe._dict(employee))
			updated += 1
			continue

		sync_attendance_staff_from_employee(frappe._dict(employee))
		created += 1

	frappe.db.commit()
	return {"created": created, "updated": updated, "total": len(employees)}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_staff_by_role(doctype, txt, searchfield, start, page_len, filters):
	role = (filters or {}).get("role")
	conditions = ["active = 1"]
	values = {"txt": f"%{txt}%", "start": start, "page_len": page_len}

	if role:
		conditions.append("staff_roles LIKE %(role_pattern)s")
		values["role_pattern"] = f"%{cstr(role).strip()}%"

	if txt:
		conditions.append("(staff_name LIKE %(txt)s OR name LIKE %(txt)s)")

	return frappe.db.sql(
		f"""
		SELECT name, staff_name
		FROM `tabAttendance Staff`
		WHERE {' AND '.join(conditions)}
		ORDER BY staff_name
		LIMIT %(page_len)s OFFSET %(start)s
		""",
		values,
	)
