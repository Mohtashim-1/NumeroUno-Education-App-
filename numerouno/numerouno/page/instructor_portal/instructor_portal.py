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

def _get_mcqs_assignments(student_group_names):
    assignment_filters = {}
    if student_group_names:
        assignment_filters["student_group"] = ["in", student_group_names]
    return frappe.get_all(
        "MCQS Assignment",
        filters=assignment_filters,
        fields=["name", "student_group", "mcqs", "modified"],
        order_by="modified desc",
    )


def _get_group_students(group_names):
    if not group_names:
        return {}

    rows = frappe.get_all(
        "Student Group Student",
        filters={"parent": ["in", list(group_names)], "active": 1},
        fields=["parent", "student", "student_name"],
    )
    grouped = {}
    for row in rows:
        grouped.setdefault(row.parent, []).append(row)
    return grouped


@frappe.whitelist()
def get_instructor_portal_data(attendance_limit=50, attendance_offset=0, card_limit=50, card_offset=0):
    attendance_limit = int(attendance_limit or 50)
    attendance_offset = int(attendance_offset or 0)
    card_limit = int(card_limit or 50)
    card_offset = int(card_offset or 0)
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

    attendance_total = frappe.db.count("Student Attendance", filters=attendance_filters)
    present_total = frappe.db.count(
        "Student Attendance",
        filters={**attendance_filters, "status": "Present"},
    )
    cards_total = frappe.db.count("Student Card", filters=card_filters)

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
        limit=attendance_limit,
        start=attendance_offset,
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
        limit=card_limit,
        start=card_offset,
    )

    student_ids = {row.student for row in cards if row.student}
    student_ids.update(row.student for row in attendance if row.student)
    student_name_map = _get_student_name_map(student_ids)

    for row in attendance:
        if not row.get("student_name"):
            row["student_name"] = student_name_map.get(row.student)

    for row in cards:
        row["student_name"] = student_name_map.get(row.student)

    return {
        "attendance": attendance,
        "cards": cards,
        "attendance_total": attendance_total,
        "present_total": present_total,
        "cards_total": cards_total,
        "attendance_limit": attendance_limit,
        "attendance_offset": attendance_offset,
        "card_limit": card_limit,
        "card_offset": card_offset,
    }


@frappe.whitelist()
def get_instructor_quiz_status(limit=200, offset=0):
    limit = int(limit or 200)
    offset = int(offset or 0)
    user = frappe.session.user
    roles = frappe.get_roles(user)

    if user == "Administrator" or "System Manager" in roles:
        student_group_names = None
    else:
        instructor_names = _get_instructor_names_for_user(user)
        student_group_names = _get_student_group_names_for_instructors(instructor_names)

    if student_group_names == []:
        return {"records": [], "total": 0, "pending": 0, "passed": 0, "failed": 0}

    assignments = _get_mcqs_assignments(student_group_names)
    if not assignments:
        return {"records": [], "total": 0, "pending": 0, "passed": 0, "failed": 0}

    group_names = {row.student_group for row in assignments if row.student_group}
    group_students = _get_group_students(group_names)

    rows = []
    for assignment in assignments:
        students = group_students.get(assignment.student_group, [])
        for student_row in students:
            rows.append({
                "student": student_row.student,
                "student_name": student_row.student_name,
                "student_group": assignment.student_group,
                "quiz": assignment.mcqs,
            })

    rows.sort(key=lambda r: ((r.get("student_name") or "").lower(), r.get("quiz") or ""))
    total = len(rows)
    page_rows = rows[offset:offset + limit]

    student_ids = {row["student"] for row in page_rows if row.get("student")}
    quiz_names = {row["quiz"] for row in page_rows if row.get("quiz")}

    activity_map = {}
    if student_ids and quiz_names:
        activities = frappe.get_all(
            "Quiz Activity",
            filters={
                "student": ["in", list(student_ids)],
                "quiz": ["in", list(quiz_names)],
            },
            fields=["name", "student", "quiz", "score", "status", "activity_date", "creation"],
            order_by="creation desc",
            ignore_permissions=True,
        )
        for activity in activities:
            key = (activity.student, activity.quiz)
            if key not in activity_map:
                activity_map[key] = activity

    pending = passed = failed = 0
    for row in page_rows:
        activity = activity_map.get((row.get("student"), row.get("quiz")))
        if activity:
            row["activity"] = activity.name
            row["score"] = activity.score
            row["status"] = activity.status
            row["activity_date"] = activity.activity_date or activity.creation
        else:
            row["status"] = "Pending"

        if row["status"] == "Pass":
            passed += 1
        elif row["status"] == "Fail":
            failed += 1
        else:
            pending += 1

    return {
        "records": page_rows,
        "total": total,
        "pending": pending,
        "passed": passed,
        "failed": failed,
        "limit": limit,
        "offset": offset,
    }
