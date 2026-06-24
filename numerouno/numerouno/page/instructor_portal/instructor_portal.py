import frappe
from frappe import _

from numerouno.numerouno.permissions import ADNOC_CERTIFICATE_VIEW_ROLE


def _has_adnoc_certificate_view_role(roles):
    return ADNOC_CERTIFICATE_VIEW_ROLE in set(roles or [])


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


def _get_adnoc_instructor_names(instructor_names):
    if not instructor_names:
        return set()

    rows = frappe.get_all(
        "Instructor",
        filters={
            "name": ["in", list(instructor_names)],
            "custom_is_adnoc_instructor": 1,
        },
        pluck="name",
    )
    return set(rows)


def _is_adnoc_instructor(user, roles, instructor_name=None):
    if user == "Administrator" or "System Manager" in roles or _has_adnoc_certificate_view_role(roles):
        return True

    instructor_name = (instructor_name or "").strip()
    if instructor_name:
        return bool(
            frappe.db.get_value("Instructor", instructor_name, "custom_is_adnoc_instructor")
        )

    return bool(_get_adnoc_instructor_names(_get_instructor_names_for_user(user)))


def _can_download_adnoc_theory_assessment(assessment_result, user, roles):
    student_group = frappe.db.get_value(
        "Assessment Result", assessment_result, "student_group"
    )
    if not student_group:
        return False

    if user == "Administrator" or "System Manager" in roles:
        return True

    group_instructors = set(
        frappe.get_all(
            "Student Group Instructor",
            filters={"parent": student_group},
            pluck="instructor",
        )
    )
    adnoc_group_instructors = _get_adnoc_instructor_names(group_instructors)
    if not adnoc_group_instructors:
        return False

    if _has_adnoc_certificate_view_role(roles):
        return True

    user_instructors = set(_get_instructor_names_for_user(user))
    return bool(user_instructors.intersection(adnoc_group_instructors))


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


def _get_quiz_passing_score_map(quiz_names):
    if not quiz_names:
        return {}

    rows = frappe.get_all(
        "Quiz",
        filters={"name": ["in", list(quiz_names)]},
        fields=["name", "passing_score"],
    )
    return {row.name: float(row.passing_score or 75) for row in rows}


def _get_group_course_map(group_names):
    if not group_names:
        return {}

    rows = frappe.get_all(
        "Student Group",
        filters={"name": ["in", list(group_names)]},
        fields=["name", "course"],
    )
    return {row.name: row.course for row in rows}


def _get_bulk_result_course_map(courses):
    if not courses or not frappe.get_meta("Course").has_field("custom_result_bulk"):
        return {}

    rows = frappe.get_all(
        "Course",
        filters={"name": ["in", list(courses)]},
        fields=["name", "custom_result_bulk"],
    )
    return {row.name: bool(row.custom_result_bulk) for row in rows}


def _get_latest_submitted_plan_map(group_names):
    if not group_names:
        return {}

    rows = frappe.get_all(
        "Assessment Plan",
        filters={"student_group": ["in", list(group_names)], "docstatus": 1},
        fields=["name", "student_group", "modified"],
        order_by="modified desc",
    )

    plan_map = {}
    for row in rows:
        if row.student_group not in plan_map:
            plan_map[row.student_group] = row.name
    return plan_map


def _get_activity_score_summary(activities):
    activity_names = [row.name for row in activities if row.name]
    if not activity_names:
        return {}

    result_rows = frappe.get_all(
        "Quiz Result",
        filters={"parent": ["in", activity_names], "parenttype": "Quiz Activity"},
        fields=["parent", "quiz_result"],
        ignore_permissions=True,
    )

    summary = {}
    for row in result_rows:
        data = summary.setdefault(row.parent, {"correct": 0, "answered": 0})
        data["answered"] += 1
        if (row.quiz_result or "").strip().lower() == "correct":
            data["correct"] += 1

    passing_scores = _get_quiz_passing_score_map({row.quiz for row in activities if row.quiz})
    activity_quiz_map = {row.name: row.quiz for row in activities if row.name}
    quiz_names = {quiz for quiz in activity_quiz_map.values() if quiz}
    quiz_question_counts = {}
    for quiz_name in quiz_names:
        quiz_question_counts[quiz_name] = frappe.db.count("Quiz Question", {"parent": quiz_name})

    for activity_name, data in summary.items():
        quiz_name = activity_quiz_map.get(activity_name)
        expected_total = quiz_question_counts.get(quiz_name) or data["answered"]
        correct = data["correct"]
        answered = data["answered"]
        is_complete = answered >= expected_total
        percentage = (correct / expected_total * 100) if expected_total else 0
        passing_score = passing_scores.get(quiz_name, 75)

        if is_complete:
            data["score"] = f"{correct}/{expected_total}"
            data["status"] = "Pass" if percentage >= passing_score else "Fail"
        else:
            # Incomplete attempt: show answered count so 105/109 is not read as 105/110.
            data["score"] = f"{correct}/{answered}" if answered else f"0/{expected_total}"
            data["status"] = "Fail"

        data["is_complete"] = is_complete
        data["expected_total"] = expected_total
        data["percentage"] = percentage

    return summary


def _activity_display_rank(activity, summary):
    """Higher rank wins when multiple Quiz Activities exist for the same student + quiz."""
    summary = summary or {}
    status = (activity.status or summary.get("status") or "").strip()
    is_complete = summary.get("is_complete", True)
    correct = summary.get("correct", 0)
    score_text = activity.score or summary.get("score") or ""
    if not correct and "/" in score_text:
        try:
            correct = int(score_text.split("/", 1)[0])
        except ValueError:
            correct = 0

    status_rank = 2 if status == "Pass" else 1
    complete_rank = 1 if is_complete else 0
    creation_rank = activity.creation.isoformat() if activity.creation else ""
    return (status_rank, complete_rank, correct, creation_rank)


def _should_prefer_activity(candidate, current, score_summary):
    if not current:
        return True
    candidate_summary = score_summary.get(candidate.name, {})
    current_summary = score_summary.get(current.name, {})
    return _activity_display_rank(candidate, candidate_summary) > _activity_display_rank(
        current, current_summary
    )


def _get_assessment_result_map(activities):
    assessment_result_map = {}
    fallback_filters = []

    for activity in activities:
        if getattr(activity, "custom_assesment_result", None):
            assessment_result_map[activity.name] = activity.custom_assesment_result
        elif (
            getattr(activity, "student", None)
            and getattr(activity, "custom_student_group", None)
            and getattr(activity, "custom_assesment_plan", None)
        ):
            fallback_filters.append(activity)

    for activity in fallback_filters:
        assessment_result = frappe.db.get_value(
            "Assessment Result",
            {
                "student": activity.student,
                "student_group": activity.custom_student_group,
                "assessment_plan": activity.custom_assesment_plan,
            },
            "name",
        )
        if assessment_result:
            assessment_result_map[activity.name] = assessment_result

    return assessment_result_map


def _attach_nyc_retest_info(row):
	"""Add NYC reassessment checklist / 3-month retest info for failed attempts."""
	from numerouno.numerouno.doctype.nyc_reassessment_checklist.nyc_reassessment_checklist import (
		check_retest_allowed,
		get_retest_status_for_activity,
	)

	row["nyc_checklist"] = None
	row["retest_eligible"] = None
	row["retest_valid_until"] = None
	row["retest_message"] = ""

	if (row.get("status") or "") != "Fail":
		return

	activity_name = row.get("activity")
	assessment_result = row.get("assessment_result")
	if activity_name:
		status = get_retest_status_for_activity(quiz_activity_name=activity_name)
	elif assessment_result:
		status = get_retest_status_for_activity(assessment_result_name=assessment_result)
	else:
		retest = check_retest_allowed(row.get("student"), row.get("student_group"), row.get("quiz"))
		row["retest_eligible"] = retest.get("allowed")
		row["retest_valid_until"] = retest.get("retest_valid_until")
		row["retest_message"] = retest.get("message")
		return

	row["nyc_checklist"] = status.get("checklist")
	row["retest_eligible"] = status.get("eligible")
	row["retest_valid_until"] = status.get("retest_valid_until")
	row["retest_message"] = status.get("message")
	row["retest_status"] = status.get("retest_status")


def _sync_activity_score_fields(activities, score_summary):
    updated = False
    for activity in activities:
        summary = score_summary.get(activity.name)
        if not summary:
            continue

        if activity.score == summary["score"] and activity.status == summary["status"]:
            continue

        frappe.db.set_value(
            "Quiz Activity",
            activity.name,
            {
                "score": summary["score"],
                "status": summary["status"],
            },
            update_modified=False,
        )
        activity.score = summary["score"]
        activity.status = summary["status"]
        updated = True

    if updated:
        frappe.db.commit()


def _resolve_student_group_names(user, roles, instructor_name=None):
    instructor_name = (instructor_name or "").strip()
    if user == "Administrator" or "System Manager" in roles:
        allowed_instructors = None
    elif _has_adnoc_certificate_view_role(roles):
        allowed_instructors = sorted(
            frappe.get_all(
                "Instructor",
                filters={"custom_is_adnoc_instructor": 1},
                pluck="name",
            )
        )
    else:
        allowed_instructors = _get_instructor_names_for_user(user)

    if instructor_name:
        if allowed_instructors is not None and instructor_name not in allowed_instructors:
            return []
        if _has_adnoc_certificate_view_role(roles) and not frappe.db.get_value(
            "Instructor", instructor_name, "custom_is_adnoc_instructor"
        ):
            return []
        instructor_names = [instructor_name]
    else:
        instructor_names = allowed_instructors

    if instructor_names is None:
        return None

    return _get_student_group_names_for_instructors(instructor_names)


@frappe.whitelist()
def get_instructor_portal_data(
    attendance_limit=50,
    attendance_offset=0,
    card_limit=50,
    card_offset=0,
    student_group=None,
    student=None,
    instructor=None,
):
    attendance_limit = int(attendance_limit or 50)
    attendance_offset = int(attendance_offset or 0)
    card_limit = int(card_limit or 50)
    card_offset = int(card_offset or 0)
    user = frappe.session.user
    roles = frappe.get_roles(user)

    student_group = (student_group or "").strip()
    student = (student or "").strip()
    instructor = (instructor or "").strip()

    student_group_names = _resolve_student_group_names(user, roles, instructor)

    if student_group_names == []:
        return {"attendance": [], "cards": []}

    attendance_filters = {"docstatus": ["in", [0, 1]]}
    card_filters = {"docstatus": ["in", [0, 1]]}

    if student_group:
        if student_group_names is None:
            attendance_filters["student_group"] = student_group
            card_filters["student_group"] = student_group
        elif student_group in student_group_names:
            attendance_filters["student_group"] = student_group
            card_filters["student_group"] = student_group
        else:
            return {"attendance": [], "cards": []}
    elif student_group_names:
        attendance_filters["student_group"] = ["in", student_group_names]
        card_filters["student_group"] = ["in", student_group_names]

    if student:
        attendance_filters["student"] = student
        card_filters["student"] = student

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
def get_instructor_quiz_status(limit=200, offset=0, student_group=None, student=None, instructor=None):
    limit = int(limit or 200)
    offset = int(offset or 0)
    user = frappe.session.user
    roles = frappe.get_roles(user)

    student_group = (student_group or "").strip()
    student = (student or "").strip()
    instructor = (instructor or "").strip()

    student_group_names = _resolve_student_group_names(user, roles, instructor)
    is_adnoc_instructor = _is_adnoc_instructor(user, roles, instructor)

    if student_group_names == []:
        return {
            "records": [],
            "total": 0,
            "pending": 0,
            "passed": 0,
            "failed": 0,
            "is_adnoc_instructor": is_adnoc_instructor,
        }

    if student_group:
        if student_group_names is None:
            student_group_names = [student_group]
        elif student_group in student_group_names:
            student_group_names = [student_group]
        else:
            return {
                "records": [],
                "total": 0,
                "pending": 0,
                "passed": 0,
                "failed": 0,
                "is_adnoc_instructor": is_adnoc_instructor,
            }

    assignments = _get_mcqs_assignments(student_group_names)
    if not assignments:
        return {
            "records": [],
            "total": 0,
            "pending": 0,
            "passed": 0,
            "failed": 0,
            "is_adnoc_instructor": is_adnoc_instructor,
        }

    group_names = {row.student_group for row in assignments if row.student_group}
    group_students = _get_group_students(group_names)
    group_course_map = _get_group_course_map(group_names)
    bulk_course_map = _get_bulk_result_course_map(set(group_course_map.values()))
    bulk_plan_map = _get_latest_submitted_plan_map(group_names)

    rows = []
    for assignment in assignments:
        students = group_students.get(assignment.student_group, [])
        for student_row in students:
            if student and student_row.student != student:
                continue
            rows.append({
                "student": student_row.student,
                "student_name": student_row.student_name,
                "student_group": assignment.student_group,
                "course": group_course_map.get(assignment.student_group),
                "bulk_result_enabled": bulk_course_map.get(group_course_map.get(assignment.student_group), False),
                "bulk_assessment_plan": bulk_plan_map.get(assignment.student_group),
                "quiz": assignment.mcqs,
            })

    rows.sort(key=lambda r: ((r.get("student_name") or "").lower(), r.get("quiz") or ""))
    total = len(rows)
    page_rows = rows[offset:offset + limit]

    student_ids = {row["student"] for row in page_rows if row.get("student")}
    quiz_names = {row["quiz"] for row in page_rows if row.get("quiz")}
    bulk_result_filters = [
        (row.get("student"), row.get("bulk_assessment_plan"))
        for row in page_rows
        if row.get("bulk_result_enabled") and row.get("student") and row.get("bulk_assessment_plan")
    ]

    activity_map = {}
    if student_ids and quiz_names:
        activities = frappe.get_all(
            "Quiz Activity",
            filters={
                "student": ["in", list(student_ids)],
                "quiz": ["in", list(quiz_names)],
            },
            fields=[
                "name",
                "student",
                "quiz",
                "score",
                "status",
                "activity_date",
                "creation",
                "custom_student_group",
                "custom_assesment_plan",
                "custom_assesment_result",
            ],
            order_by="creation desc",
            ignore_permissions=True,
        )
        score_summary = _get_activity_score_summary(activities)
        _sync_activity_score_fields(activities, score_summary)
        assessment_result_map = _get_assessment_result_map(activities)
        for activity in activities:
            summary = score_summary.get(activity.name)
            if summary:
                activity.score = summary["score"]
                activity.status = summary["status"]

            key = (activity.student, activity.quiz)
            existing = activity_map.get(key)
            if _should_prefer_activity(activity, existing, score_summary):
                activity_map[key] = activity
                activity.assessment_result = assessment_result_map.get(activity.name)

    bulk_result_map = {}
    if bulk_result_filters:
        bulk_students = {student for student, _plan in bulk_result_filters}
        bulk_plans = {plan for _student, plan in bulk_result_filters}
        bulk_results = frappe.get_all(
            "Assessment Result",
            filters={
                "student": ["in", list(bulk_students)],
                "assessment_plan": ["in", list(bulk_plans)],
                "docstatus": ["<", 2],
            },
            fields=["name", "student", "assessment_plan", "docstatus"],
            ignore_permissions=True,
        )
        for result in bulk_results:
            bulk_result_map[(result.student, result.assessment_plan)] = result

    pending = passed = failed = 0
    for row in page_rows:
        activity = activity_map.get((row.get("student"), row.get("quiz")))
        if activity:
            row["activity"] = activity.name
            row["score"] = activity.score
            row["status"] = activity.status
            row["activity_date"] = activity.activity_date or activity.creation
            row["assessment_result"] = getattr(activity, "assessment_result", None)
        else:
            row["status"] = "Pending"

        _attach_nyc_retest_info(row)

        if row.get("bulk_result_enabled") and row.get("bulk_assessment_plan"):
            bulk_result = bulk_result_map.get((row.get("student"), row.get("bulk_assessment_plan")))
            if bulk_result:
                row["bulk_assessment_result"] = bulk_result.name
                row["bulk_assessment_result_docstatus"] = bulk_result.docstatus

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
        "is_adnoc_instructor": is_adnoc_instructor,
    }


@frappe.whitelist()
def get_instructor_results(limit=50, offset=0, student_group=None, student=None, instructor=None):
    limit = int(limit or 50)
    offset = int(offset or 0)
    user = frappe.session.user
    roles = frappe.get_roles(user)

    student_group = (student_group or "").strip()
    student = (student or "").strip()
    instructor = (instructor or "").strip()

    student_group_names = _resolve_student_group_names(user, roles, instructor)
    is_adnoc_instructor = _is_adnoc_instructor(user, roles, instructor)

    if student_group_names == []:
        return {
            "records": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "is_adnoc_instructor": is_adnoc_instructor,
        }

    filters = {"docstatus": ["<", 2]}
    if student_group:
        if student_group_names is None:
            filters["student_group"] = student_group
        elif student_group in student_group_names:
            filters["student_group"] = student_group
        else:
            return {
                "records": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "is_adnoc_instructor": is_adnoc_instructor,
            }
    elif student_group_names:
        filters["student_group"] = ["in", student_group_names]

    if student:
        filters["student"] = student

    total = frappe.db.count("Assessment Result", filters=filters)
    records = frappe.get_all(
        "Assessment Result",
        filters=filters,
        fields=[
            "name",
            "assessment_plan",
            "student",
            "student_name",
            "student_group",
            "course",
            "total_score",
            "maximum_score",
            "grade",
            "docstatus",
            "modified",
            "creation",
        ],
        order_by="modified desc",
        limit=limit,
        start=offset,
        ignore_permissions=True,
    )

    student_ids = {row.student for row in records if row.student and not row.student_name}
    student_name_map = _get_student_name_map(student_ids)
    for row in records:
        if not row.get("student_name"):
            row["student_name"] = student_name_map.get(row.student)

    return {
        "records": records,
        "total": total,
        "limit": limit,
        "offset": offset,
        "is_adnoc_instructor": is_adnoc_instructor,
    }


@frappe.whitelist()
def get_instructor_bulk_assessments(student_group=None, student=None, instructor=None):
    user = frappe.session.user
    roles = frappe.get_roles(user)

    student_group = (student_group or "").strip()
    student = (student or "").strip()
    instructor = (instructor or "").strip()

    student_group_names = _resolve_student_group_names(user, roles, instructor)
    if student_group_names == []:
        return {"records": []}

    if student_group:
        if student_group_names is None:
            group_names = [student_group]
        elif student_group in student_group_names:
            group_names = [student_group]
        else:
            return {"records": []}
    else:
        group_names = student_group_names

    group_filters = {}
    if group_names:
        group_filters["name"] = ["in", group_names]

    groups = frappe.get_all(
        "Student Group",
        filters=group_filters,
        fields=["name", "course"],
        order_by="name asc",
    )
    if not groups:
        return {"records": []}

    course_map = {row.name: row.course for row in groups}
    bulk_course_map = _get_bulk_result_course_map(set(course_map.values()))
    eligible_groups = [
        row.name
        for row in groups
        if bulk_course_map.get(row.course)
    ]
    if not eligible_groups:
        return {"records": []}

    plan_map = _get_latest_submitted_plan_map(eligible_groups)
    plan_names = {plan for plan in plan_map.values() if plan}

    result_map = {}
    if plan_names:
        result_rows = frappe.get_all(
            "Assessment Result",
            filters={"assessment_plan": ["in", list(plan_names)], "docstatus": ["<", 2]},
            fields=["name", "student", "assessment_plan", "docstatus"],
            ignore_permissions=True,
        )
        for row in result_rows:
            result_map[(row.student, row.assessment_plan)] = row

    student_filters = {"parent": ["in", eligible_groups], "active": 1}
    if student:
        student_filters["student"] = student

    student_rows = frappe.get_all(
        "Student Group Student",
        filters=student_filters,
        fields=["parent", "student", "student_name", "idx"],
        order_by="parent asc, idx asc",
    )

    records = []
    for row in student_rows:
        group_name = row.parent
        course = course_map.get(group_name)
        assessment_plan = plan_map.get(group_name)
        existing_result = result_map.get((row.student, assessment_plan)) if assessment_plan else None
        records.append(
            {
                "student": row.student,
                "student_name": row.student_name,
                "student_group": group_name,
                "course": course,
                "assessment_plan": assessment_plan,
                "assessment_result": existing_result.name if existing_result else None,
                "assessment_result_docstatus": existing_result.docstatus if existing_result else None,
                "ready": bool(assessment_plan and not existing_result),
            }
        )

    return {"records": records}


def _validate_bulk_assessment_group_access(student_group, instructor=None):
    student_group = (student_group or "").strip()
    if not student_group:
        frappe.throw(_("Student Group is required."))

    user = frappe.session.user
    roles = frappe.get_roles(user)
    student_group_names = _resolve_student_group_names(user, roles, instructor)
    if student_group_names is not None and student_group not in student_group_names:
        frappe.throw(_("You are not allowed to manage bulk assessments for this student group."), frappe.PermissionError)


def _get_or_create_default_assessment_group():
    assessment_group = frappe.get_all("Assessment Group", fields=["name"], limit=1)
    if assessment_group:
        return assessment_group[0].name

    doc = frappe.new_doc("Assessment Group")
    doc.assessment_group_name = "Default Assessment Group"
    doc.insert(ignore_permissions=True)
    return doc.name


def _get_or_create_pass_fail_criteria():
    criteria_name = "Pass/Fail Assessment"
    criteria = frappe.get_all(
        "Assessment Criteria",
        filters={"assessment_criteria": criteria_name},
        fields=["name"],
        limit=1,
    )
    if criteria:
        return criteria[0].name

    doc = frappe.new_doc("Assessment Criteria")
    doc.assessment_criteria = criteria_name
    doc.insert(ignore_permissions=True)
    return doc.name


def _get_default_grading_scale(course):
    grading_scale = frappe.db.get_value("Course", course, "default_grading_scale")
    if grading_scale:
        return grading_scale

    grading_scales = frappe.get_all("Grading Scale", fields=["name"], limit=1)
    if grading_scales:
        return grading_scales[0].name

    frappe.throw(_("Please create a Grading Scale before creating Assessment Plans."))


def _get_bulk_assessment_slot(student_group):
    try:
        from numerouno.numerouno.api.quiz_api import _find_available_assessment_slot

        return _find_available_assessment_slot(student_group)
    except Exception:
        return frappe.utils.today(), "06:00:00", "08:00:00"


def _ensure_bulk_assessment_plan(student_group):
    course = frappe.db.get_value("Student Group", student_group, "course")
    if not course:
        frappe.throw(_("Student Group {0} does not have a course.").format(student_group))

    if not _get_bulk_result_course_map({course}).get(course):
        frappe.throw(_("Bulk pass/fail result is not enabled for course {0}.").format(course))

    existing_plan = _get_latest_submitted_plan_map([student_group]).get(student_group)
    if existing_plan:
        return existing_plan

    student_group_doc = frappe.get_doc("Student Group", student_group)
    assessment_group = _get_or_create_default_assessment_group()
    criteria = _get_or_create_pass_fail_criteria()
    grading_scale = _get_default_grading_scale(course)
    schedule_date, from_time, to_time = _get_bulk_assessment_slot(student_group)

    if not schedule_date:
        schedule_date = frappe.utils.today()
    if not from_time:
        from_time = "06:00:00"
    if not to_time:
        to_time = "08:00:00"

    plan = frappe.new_doc("Assessment Plan")
    plan.student_group = student_group
    plan.course = course
    plan.assessment_name = "Bulk Pass/Fail Assessment - {0}".format(student_group)
    plan.assessment_group = assessment_group
    plan.grading_scale = grading_scale
    plan.schedule_date = schedule_date
    plan.from_time = from_time
    plan.to_time = to_time
    plan.maximum_assessment_score = 100
    plan.append(
        "assessment_criteria",
        {
            "assessment_criteria": criteria,
            "maximum_score": 100,
        },
    )

    if getattr(student_group_doc, "program", None):
        plan.program = student_group_doc.program
    if getattr(student_group_doc, "academic_year", None):
        plan.academic_year = student_group_doc.academic_year
    if getattr(student_group_doc, "academic_term", None):
        plan.academic_term = student_group_doc.academic_term

    plan.insert(ignore_permissions=True)
    plan.flags.ignore_permissions = True
    plan.submit()
    frappe.db.commit()
    return plan.name


@frappe.whitelist()
def get_instructor_bulk_assessment_students(student_group, instructor=None):
    _validate_bulk_assessment_group_access(student_group, instructor)

    from numerouno.numerouno.doctype.assessment_result.assessment_result import (
        get_students_for_bulk_pass_fail_result,
    )

    return get_students_for_bulk_pass_fail_result(student_group)


@frappe.whitelist()
def submit_instructor_bulk_assessment_results(student_group, results_data, instructor=None):
    _validate_bulk_assessment_group_access(student_group, instructor)
    _ensure_bulk_assessment_plan(student_group)

    from numerouno.numerouno.doctype.assessment_result.assessment_result import (
        create_bulk_pass_fail_assessment_results,
    )

    return create_bulk_pass_fail_assessment_results(student_group, results_data)


@frappe.whitelist()
def submit_instructor_bulk_assessment_rows(results_data, instructor=None):
    if isinstance(results_data, str):
        import json

        results_data = json.loads(results_data)

    grouped_results = {}
    for row in results_data or []:
        student_group = (row.get("student_group") or "").strip()
        student = (row.get("student") or "").strip()
        result_status = (row.get("result_status") or row.get("status") or "").strip()
        if not student_group or not student or result_status.lower() not in ("pass", "fail"):
            continue

        grouped_results.setdefault(student_group, []).append(
            {"student": student, "result_status": result_status}
        )

    if not grouped_results:
        frappe.throw(_("Select at least one student result."))

    from numerouno.numerouno.doctype.assessment_result.assessment_result import (
        create_bulk_pass_fail_assessment_results,
    )

    created = []
    skipped = []
    assessment_plans = {}
    for student_group, rows in grouped_results.items():
        _validate_bulk_assessment_group_access(student_group, instructor)
        _ensure_bulk_assessment_plan(student_group)
        result = create_bulk_pass_fail_assessment_results(student_group, rows)
        assessment_plans[student_group] = result.get("assessment_plan")
        created.extend(result.get("created") or [])
        skipped.extend(result.get("skipped") or [])

    return {
        "assessment_plans": assessment_plans,
        "created": created,
        "skipped": skipped,
    }


@frappe.whitelist()
def submit_instructor_pass_fail_result(student_group, student, status):
    student_group = (student_group or "").strip()
    student = (student or "").strip()
    status = (status or "").strip()
    if not student_group or not student:
        frappe.throw(_("Student Group and Student are required."))

    user = frappe.session.user
    roles = frappe.get_roles(user)
    student_group_names = _resolve_student_group_names(user, roles)
    if student_group_names is not None and student_group not in student_group_names:
        frappe.throw(_("You are not allowed to submit results for this student group."), frappe.PermissionError)

    if not frappe.db.exists(
        "Student Group Student",
        {"parent": student_group, "student": student, "active": 1},
    ):
        frappe.throw(_("Student {0} is not active in Student Group {1}.").format(student, student_group))

    from numerouno.numerouno.doctype.assessment_result.assessment_result import (
        create_bulk_pass_fail_assessment_results,
    )

    result = create_bulk_pass_fail_assessment_results(
        student_group,
        [{"student": student, "result_status": status}],
    )
    created = result.get("created") or []
    skipped = result.get("skipped") or []
    if created:
        return created[0]
    if skipped:
        return skipped[0]
    frappe.throw(_("No Assessment Result was created."))


@frappe.whitelist()
def download_adnoc_theory_assessment(assessment_result):
    assessment_result = (assessment_result or "").strip()
    if not assessment_result:
        frappe.throw(_("Assessment Result is required."))

    user = frappe.session.user
    roles = frappe.get_roles(user)

    if not _can_download_adnoc_theory_assessment(assessment_result, user, roles):
        frappe.throw(
            _("Only System Managers or ADNOC instructors assigned to this student group can download this report."),
            frappe.PermissionError,
        )

    doc = frappe.get_doc("Assessment Result", assessment_result)
    pdf_file = frappe.get_print(
        "Assessment Result",
        assessment_result,
        "Theory Assesment",
        doc=doc,
        as_pdf=True,
        no_letterhead=1,
    )

    frappe.local.response.filename = "{}-Theory-Assesment.pdf".format(
        assessment_result.replace(" ", "-").replace("/", "-")
    )
    frappe.local.response.filecontent = pdf_file
    frappe.local.response.type = "pdf"


@frappe.whitelist()
def create_nyc_reassessment_checklist(quiz_activity=None, assessment_result=None):
	from numerouno.numerouno.doctype.nyc_reassessment_checklist.nyc_reassessment_checklist import (
		create_from_assessment_result,
		create_from_quiz_activity,
	)

	quiz_activity = (quiz_activity or "").strip()
	assessment_result = (assessment_result or "").strip()
	if quiz_activity:
		return create_from_quiz_activity(quiz_activity)
	if assessment_result:
		return create_from_assessment_result(assessment_result)
	frappe.throw(_("Quiz Activity or Assessment Result is required."))
