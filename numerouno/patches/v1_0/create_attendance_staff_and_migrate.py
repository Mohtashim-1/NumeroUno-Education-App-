import frappe

from numerouno.numerouno.doctype.attendance_staff.attendance_staff import (
	create_attendance_staff_for_all_employees,
	sync_attendance_staff_from_employee,
)

STAFF_ATTENDANCE_FIELDS = [
	"lead_instructor",
	"diver_1",
	"diver_2",
	"trainee_crane_operator",
	"crane_operator",
	"pool_safety_person",
]


def execute():
	result = create_attendance_staff_for_all_employees()
	_ensure_staff_attendance_references()
	frappe.logger().info(f"Attendance Staff migration completed: {result}")


def _ensure_staff_attendance_references():
	referenced_employees = set()

	for fieldname in STAFF_ATTENDANCE_FIELDS:
		for value in frappe.db.sql(
			f"""
			SELECT DISTINCT `{fieldname}`
			FROM `tabStaff Attendance`
			WHERE `{fieldname}` IS NOT NULL AND `{fieldname}` != ''
			"""
		):
			if value[0]:
				referenced_employees.add(value[0])

	for employee in referenced_employees:
		if frappe.db.exists("Attendance Staff", employee):
			continue

		employee_doc = frappe.db.get_value(
			"Employee",
			employee,
			["name", "employee_name", "company", "status"],
			as_dict=True,
		)
		if not employee_doc:
			continue

		sync_attendance_staff_from_employee(frappe._dict(employee_doc))

	frappe.db.commit()
