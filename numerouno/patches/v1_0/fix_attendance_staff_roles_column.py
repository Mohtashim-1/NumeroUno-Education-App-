import frappe

from numerouno.numerouno.doctype.attendance_staff.attendance_staff import DEFAULT_STAFF_ROLES

DEFAULT_ROLES_VALUE = ", ".join(DEFAULT_STAFF_ROLES)


def execute():
	_add_staff_roles_column()
	_backfill_staff_roles()


def _add_staff_roles_column():
	if frappe.db.has_column("Attendance Staff", "staff_roles"):
		return

	frappe.db.sql(
		"""
		ALTER TABLE `tabAttendance Staff`
		ADD COLUMN staff_roles TEXT
		"""
	)


def _backfill_staff_roles():
	frappe.db.sql(
		"""
		UPDATE `tabAttendance Staff`
		SET staff_roles = %(roles)s
		WHERE staff_roles IS NULL OR staff_roles = ''
		""",
		{"roles": DEFAULT_ROLES_VALUE},
	)
	frappe.db.commit()
