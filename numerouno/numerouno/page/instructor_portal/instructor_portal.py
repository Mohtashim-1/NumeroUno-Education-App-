import frappe


def _get_instructor_names_for_user(user):
    instructor_names = set(
        frappe.get_all("Instructor", filters={"custom_email": user}, pluck="name")
    )

    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if employee:
        instructor_names.update(
            frappe.get_all("Instructor", filters={"employee": employee}, pluck="name")
        )

    return sorted(instructor_names)


def _get_student_group_names_for_instructors(instructor_names):
    if not instructor_names:
        return []

    rows = frappe.get_all(
        "Student Group Instructor",
        filters={"instructor": ["in", instructor_names]},
        fields=["parent"],
        group_by="parent",
    )
    return [row.parent for row in rows]


def _get_student_name_map(student_ids):
    if not student_ids:
        return {}

    rows = frappe.get_all(
        "Student",
        filters={"name": ["in", list(student_ids)]},
        fields=["name", "student_name"],
    )
    return {row.name: row.student_name for row in rows}


@frappe.whitelist()
def get_instructor_portal_data():
    user = frappe.session.user
    roles = frappe.get_roles(user)

    if user == "Administrator" or "System Manager" in roles:
        student_group_names = None
    else:
        instructor_names = _get_instructor_names_for_user(user)
        student_group_names = _get_student_group_names_for_instructors(instructor_names)

    if student_group_names == []:
        return {"attendance": [], "cards": []}

    attendance_filters = {"docstatus": ["in", [0, 1]]}
    card_filters = {"docstatus": ["in", [0, 1]]}

    if student_group_names:
        attendance_filters["student_group"] = ["in", student_group_names]
        card_filters["student_group"] = ["in", student_group_names]

    attendance = frappe.get_all(
        "Student Attendance",
        filters=attendance_filters,
        fields=[
            "name",
            "student",
            "student_name",
            "student_group",
            "date",
            "status",
            "course_schedule",
            "custom_student_signature",
            "docstatus",
        ],
        order_by="date desc, modified desc",
    )

    cards = frappe.get_all(
        "Student Card",
        filters=card_filters,
        fields=[
            "name",
            "student",
            "student_group",
            "student_signature",
            "docstatus",
            "modified",
        ],
        order_by="modified desc",
    )

    student_ids = {row.student for row in cards if row.student}
    student_ids.update(row.student for row in attendance if row.student)
    student_name_map = _get_student_name_map(student_ids)

    for row in attendance:
        if not row.get("student_name"):
            row["student_name"] = student_name_map.get(row.student)

    for row in cards:
        row["student_name"] = student_name_map.get(row.student)

    return {"attendance": attendance, "cards": cards}
