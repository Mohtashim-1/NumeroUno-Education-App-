import frappe

STAFF_ATTENDANCE_USERS = [
	{"email": "m.mamun@numerouno-me.com", "name": "MAMUN"},
	{"email": "s.mohite@numerouno-me.com", "name": "Suraj"},
	{"email": "a.mahakuda@numerouno-me.com", "name": "Ajay"},
	{"email": "j.satyawan@numerouno-me.com", "name": "Jayesh"},
	{"email": "j.lisanja@numerouno-me.com", "name": "JOHN"},
	{"email": "m.flore@numerouno-me.com", "name": "FLORA"},
	{"email": "l.rajapaksha@numerouno-me.com", "name": "LAKMAL"},
	{"email": "a.ameen@numerouno-me.com", "name": "Al Ameen"},
	{"email": "l.syed@numerouno-me.com", "name": "Lal Syed"},
	{"email": "m.pillai@numerouno-me.com", "name": "Madhusudan"},
]

ROLE = "Staff Attendance User"


def execute():
	_ensure_role()
	_assign_role_to_users()


def _ensure_role():
	if frappe.db.exists("Role", ROLE):
		return

	frappe.get_doc(
		{
			"doctype": "Role",
			"role_name": ROLE,
			"desk_access": 1,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()


def _assign_role_to_users():
	assigned = []
	missing = []

	for entry in STAFF_ATTENDANCE_USERS:
		email = entry["email"]
		if not frappe.db.exists("User", email):
			missing.append(entry)
			continue

		user = frappe.get_doc("User", email)
		if ROLE not in [row.role for row in user.roles]:
			user.add_roles(ROLE)
		assigned.append(email)

	frappe.db.commit()
	frappe.logger().info(f"Staff Attendance User role assigned to: {assigned}")
	if missing:
		frappe.logger().warning(f"Staff Attendance User role missing users: {missing}")
