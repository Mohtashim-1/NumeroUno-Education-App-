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
NON_INSTRUCTOR_STAFF_ROLES = [role for role in DEFAULT_STAFF_ROLES if role != "Lead Instructor"]


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


def _get_user_id_for_employee(employee_doc):
	if isinstance(employee_doc, dict):
		employee_doc = frappe._dict(employee_doc)

	user_id = getattr(employee_doc, "user_id", None)
	if not user_id and getattr(employee_doc, "name", None):
		user_id = frappe.db.get_value("Employee", employee_doc.name, "user_id")
	return (user_id or "").strip()


def _resolve_staff_roles_for_employee(employee_doc):
	user_id = _get_user_id_for_employee(employee_doc)
	if not user_id:
		return ", ".join(DEFAULT_STAFF_ROLES)

	user_roles = set(
		frappe.get_all(
			"Has Role",
			filters={"parent": user_id, "parenttype": "User"},
			pluck="role",
		)
	)
	resolved_roles = list(NON_INSTRUCTOR_STAFF_ROLES)
	if "Instructor" in user_roles:
		resolved_roles.insert(0, "Lead Instructor")
	return ", ".join(resolved_roles)


def sync_attendance_staff_from_employee(employee_doc, method=None):
	"""Create or update Attendance Staff when an Employee is saved."""
	if isinstance(employee_doc, dict):
		employee_doc = frappe._dict(employee_doc)

	if not employee_doc.name:
		return

	if employee_doc.status and employee_doc.status != "Active":
		if frappe.db.exists("Attendance Staff", employee_doc.name):
			frappe.db.set_value("Attendance Staff", employee_doc.name, "active", 0, update_modified=False)
		return

	staff_name = employee_doc.employee_name or employee_doc.name
	company = employee_doc.company
	staff_roles = _resolve_staff_roles_for_employee(employee_doc)

	if frappe.db.exists("Attendance Staff", employee_doc.name):
		frappe.db.set_value(
			"Attendance Staff",
			employee_doc.name,
			{
				"staff_name": staff_name,
				"company": company,
				"active": 1,
				"employee": employee_doc.name,
				"staff_roles": staff_roles,
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
			"staff_roles": staff_roles,
		}
	)
	doc.insert(ignore_permissions=True)


def sync_attendance_staff_from_user(user_doc, method=None):
	"""Update Attendance Staff roles when a User's roles change."""
	user = getattr(user_doc, "name", None)
	if not user:
		return

	employee_names = frappe.get_all("Employee", filters={"user_id": user}, pluck="name")
	for employee_name in employee_names:
		employee_doc = frappe.db.get_value(
			"Employee",
			employee_name,
			["name", "employee_name", "company", "status", "user_id"],
			as_dict=True,
		)
		if employee_doc:
			sync_attendance_staff_from_employee(frappe._dict(employee_doc))


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
	if isinstance(filters, str):
		try:
			filters = frappe.parse_json(filters)
		except Exception:
			filters = {}

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
