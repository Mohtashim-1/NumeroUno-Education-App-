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


def _get_quiz_distinct_question_count_map(quiz_names):
    """Count unique Question links per quiz (duplicate Quiz Question rows count once)."""
    if not quiz_names:
        return {}

    rows = frappe.get_all(
        "Quiz Question",
        filters={"parent": ["in", list(quiz_names)]},
        fields=["parent", "question"],
        ignore_permissions=True,
    )
    question_sets = {}
    for row in rows:
        if not row.question:
            continue
        question_sets.setdefault(row.parent, set()).add(row.question)
    return {quiz: len(questions) for quiz, questions in question_sets.items()}


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
        fields=["parent", "quiz_result", "question"],
        ignore_permissions=True,
    )

    summary = {}
    for row in result_rows:
        if not row.question:
            continue
        data = summary.setdefault(
            row.parent,
            {"correct_questions": set(), "answered_questions": set()},
        )
        data["answered_questions"].add(row.question)
        if (row.quiz_result or "").strip().lower() == "correct":
            data["correct_questions"].add(row.question)

    passing_scores = _get_quiz_passing_score_map({row.quiz for row in activities if row.quiz})
    activity_quiz_map = {row.name: row.quiz for row in activities if row.name}
    quiz_names = {quiz for quiz in activity_quiz_map.values() if quiz}
    quiz_question_counts = _get_quiz_distinct_question_count_map(quiz_names)

    for activity_name, data in summary.items():
        quiz_name = activity_quiz_map.get(activity_name)
        expected_total = quiz_question_counts.get(quiz_name) or len(data["answered_questions"])
        correct = len(data["correct_questions"])
        answered = len(data["answered_questions"])
        is_complete = answered >= expected_total
        percentage = (correct / expected_total * 100) if expected_total else 0
        passing_score = passing_scores.get(quiz_name, 75)

        data["correct"] = correct
        data["answered"] = answered
        data["score"] = f"{correct}/{expected_total}"
        data["status"] = "Pass" if is_complete and percentage >= passing_score else "Fail"
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


def _course_requires_make_model(course):
    if not course:
        return False
    if not frappe.get_meta("Course").has_field("custom_enable_make_and_model"):
        return False
    return bool(frappe.db.get_value("Course", course, "custom_enable_make_and_model"))


def _can_instructor_edit_result(assessment_result, user, roles):
    student_group = frappe.db.get_value("Assessment Result", assessment_result, "student_group")
    if not student_group:
        return False
    if user == "Administrator" or "System Manager" in roles:
        return True
    student_group_names = _resolve_student_group_names(user, roles)
    if student_group_names is None:
        return True
    return student_group in student_group_names


def _attach_make_model_meta(records):
    if not records:
        return records

    courses = {row.get("course") for row in records if row.get("course")}
    course_flags = {course: _course_requires_make_model(course) for course in courses}

    for row in records:
        required = course_flags.get(row.get("course"), False)
        make = (row.get("custom_make") or "").strip()
        model = (row.get("custom_model") or "").strip()
        capacity = (row.get("custom_capacity") or "").strip()
        row["make_model_required"] = required
        row["make"] = make
        row["model"] = model
        row["capacity"] = capacity
        row["make_model_pending"] = required and not (make and model and capacity)

    return records


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


def _scope_student_group_names(student_group_names, student_group=None, course=None):
    """Narrow instructor-scoped student groups by explicit student_group and/or course."""
    student_group = (student_group or "").strip()
    course = (course or "").strip()

    if student_group_names == []:
        return []

    if student_group:
        if student_group_names is not None and student_group not in student_group_names:
            return []
        if course:
            group_course = frappe.db.get_value("Student Group", student_group, "course")
            if group_course != course:
                return []
        return [student_group]

    if course:
        course_filters = {"course": course}
        if student_group_names is None:
            return frappe.get_all("Student Group", filters=course_filters, pluck="name") or []
        return frappe.get_all(
            "Student Group",
            filters={"name": ["in", student_group_names], **course_filters},
            pluck="name",
        ) or []

    return student_group_names


def _apply_scoped_student_group_filter(filters, scoped_names):
    if scoped_names == []:
        return False
    if scoped_names is None:
        return True
    if len(scoped_names) == 1:
        filters["student_group"] = scoped_names[0]
    else:
        filters["student_group"] = ["in", scoped_names]
    return True


INSTRUCTOR_FORM_CONFIGS = {
    "resit": {
        "doctype": "NYC Reassessment Checklist",
        "fields": [
            "name",
            "candidate_name",
            "student",
            "student_group",
            "first_assessment_date",
            "retest_status",
            "retest_valid_until",
            "docstatus",
            "modified",
        ],
        "student_filter": True,
    },
    "assessor_checklist": {
        "doctype": "Assessor Checklist",
        "fields": [
            "name",
            "checklist_type",
            "form_code",
            "student_group",
            "assessment_date",
            "docstatus",
            "modified",
        ],
        "student_filter": False,
    },
    "safety_briefing": {
        "doctype": "Safety Briefing",
        "fields": [
            "name",
            "briefing_type",
            "form_code",
            "student_group",
            "briefing_date",
            "docstatus",
            "modified",
        ],
        "student_filter": False,
    },
    "wms_pretest": {
        "doctype": "English Proficiency Test",
        "fields": [
            "name",
            "candidate_name",
            "student",
            "student_group",
            "date_of_training",
            "result",
            "docstatus",
            "modified",
        ],
        "student_filter": True,
    },
    "adsd_pretest": {
        "doctype": "Pre Test ADSD",
        "fields": [
            "name",
            "candidate_name",
            "student",
            "student_group",
            "test_date",
            "result",
            "score",
            "docstatus",
            "modified",
        ],
        "student_filter": True,
    },
}


def _build_instructor_form_filters(
    user,
    roles,
    instructor=None,
    student_group=None,
    student=None,
    course=None,
    student_filter=False,
):
    instructor = (instructor or "").strip()
    student_group = (student_group or "").strip()
    student = (student or "").strip()
    course = (course or "").strip()

    student_group_names = _resolve_student_group_names(user, roles, instructor)
    if student_group_names == []:
        return None

    scoped_names = _scope_student_group_names(student_group_names, student_group, course)
    filters = {"docstatus": ["in", [0, 1]]}
    if not _apply_scoped_student_group_filter(filters, scoped_names):
        return None

    if student_filter and student:
        filters["student"] = student

    return filters


def _get_instructor_form_records(
    form_key,
    limit=50,
    offset=0,
    student_group=None,
    student=None,
    course=None,
    instructor=None,
):
    config = INSTRUCTOR_FORM_CONFIGS.get(form_key)
    if not config:
        frappe.throw(_("Invalid instructor form key."))

    limit = int(limit or 50)
    offset = int(offset or 0)
    user = frappe.session.user
    roles = frappe.get_roles(user)

    filters = _build_instructor_form_filters(
        user,
        roles,
        instructor=instructor,
        student_group=student_group,
        student=student,
        course=course,
        student_filter=config.get("student_filter"),
    )
    if filters is None:
        return {"records": [], "total": 0}

    doctype = config["doctype"]
    total = frappe.db.count(doctype, filters=filters)
    records = frappe.get_all(
        doctype,
        filters=filters,
        fields=config["fields"],
        order_by="modified desc",
        limit=limit,
        start=offset,
    )
    return {"records": records, "total": total}


@frappe.whitelist()
def get_instructor_form_records(
    form_key,
    limit=50,
    offset=0,
    student_group=None,
    student=None,
    course=None,
    instructor=None,
):
    return _get_instructor_form_records(
        form_key,
        limit=limit,
        offset=offset,
        student_group=student_group,
        student=student,
        course=course,
        instructor=instructor,
    )


@frappe.whitelist()
def get_instructor_portal_data(
    attendance_limit=50,
    attendance_offset=0,
    card_limit=50,
    card_offset=0,
    student_group=None,
    student=None,
    course=None,
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
    course = (course or "").strip()
    instructor = (instructor or "").strip()

    student_group_names = _resolve_student_group_names(user, roles, instructor)

    if student_group_names == []:
        return {"attendance": [], "cards": []}

    scoped_names = _scope_student_group_names(student_group_names, student_group, course)
    attendance_filters = {"docstatus": ["in", [0, 1]]}
    card_filters = {"docstatus": ["in", [0, 1]]}

    if not _apply_scoped_student_group_filter(attendance_filters, scoped_names):
        return {"attendance": [], "cards": []}
    _apply_scoped_student_group_filter(card_filters, scoped_names)

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
def get_instructor_quiz_status(
    limit=200, offset=0, student_group=None, student=None, course=None, instructor=None
):
    limit = int(limit or 200)
    offset = int(offset or 0)
    user = frappe.session.user
    roles = frappe.get_roles(user)

    student_group = (student_group or "").strip()
    student = (student or "").strip()
    course = (course or "").strip()
    instructor = (instructor or "").strip()

    student_group_names = _resolve_student_group_names(user, roles, instructor)
    is_adnoc_instructor = _is_adnoc_instructor(user, roles, instructor)
    empty_response = {
        "records": [],
        "total": 0,
        "pending": 0,
        "passed": 0,
        "failed": 0,
        "is_adnoc_instructor": is_adnoc_instructor,
    }

    if student_group_names == []:
        return empty_response

    student_group_names = _scope_student_group_names(student_group_names, student_group, course)
    if student_group_names == []:
        return empty_response

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
                activity.percentage = summary.get("percentage")

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
            if getattr(activity, "percentage", None) is not None:
                row["percentage"] = round(activity.percentage, 1)
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
def get_instructor_results(
    limit=50, offset=0, student_group=None, student=None, course=None, instructor=None
):
    limit = int(limit or 50)
    offset = int(offset or 0)
    user = frappe.session.user
    roles = frappe.get_roles(user)

    student_group = (student_group or "").strip()
    student = (student or "").strip()
    course = (course or "").strip()
    instructor = (instructor or "").strip()

    student_group_names = _resolve_student_group_names(user, roles, instructor)
    is_adnoc_instructor = _is_adnoc_instructor(user, roles, instructor)
    empty_response = {
        "records": [],
        "total": 0,
        "limit": limit,
        "offset": offset,
        "is_adnoc_instructor": is_adnoc_instructor,
    }

    if student_group_names == []:
        return empty_response

    scoped_names = _scope_student_group_names(student_group_names, student_group, course)
    filters = {"docstatus": ["<", 2]}
    if not _apply_scoped_student_group_filter(filters, scoped_names):
        return empty_response

    if student:
        filters["student"] = student
    if course:
        filters["course"] = course

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
            "custom_make",
            "custom_model",
            "custom_capacity",
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

    records = _attach_make_model_meta(records)

    return {
        "records": records,
        "total": total,
        "limit": limit,
        "offset": offset,
        "is_adnoc_instructor": is_adnoc_instructor,
    }


@frappe.whitelist()
def update_assessment_result_make_model(assessment_result, make, model, capacity=None):
    assessment_result = (assessment_result or "").strip()
    make = (make or "").strip()
    model = (model or "").strip()
    capacity = (capacity or "").strip()
    if not assessment_result:
        frappe.throw(_("Assessment Result is required"))
    if not make or not model or not capacity:
        frappe.throw(_("Make, Model and Capacity are required"))

    user = frappe.session.user
    roles = frappe.get_roles(user)
    if not _can_instructor_edit_result(assessment_result, user, roles):
        frappe.throw(_("Not permitted to update this assessment result."), frappe.PermissionError)

    course = frappe.db.get_value("Assessment Result", assessment_result, "course")
    if not _course_requires_make_model(course):
        frappe.throw(_("Make and Model are not enabled for this course."))

    frappe.db.set_value(
        "Assessment Result",
        assessment_result,
        {"custom_make": make, "custom_model": model, "custom_capacity": capacity},
        update_modified=True,
    )
    return {
        "assessment_result": assessment_result,
        "make": make,
        "model": model,
        "capacity": capacity,
    }


@frappe.whitelist()
def get_instructor_bulk_assessments(student_group=None, student=None, course=None, instructor=None):
    user = frappe.session.user
    roles = frappe.get_roles(user)

    student_group = (student_group or "").strip()
    student = (student or "").strip()
    course = (course or "").strip()
    instructor = (instructor or "").strip()

    student_group_names = _resolve_student_group_names(user, roles, instructor)
    if student_group_names == []:
        return {"records": []}

    group_names = _scope_student_group_names(student_group_names, student_group, course)
    if group_names == []:
        return {"records": []}

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
def get_instructor_safety_briefings(
    limit=50,
    offset=0,
    student_group=None,
    course=None,
    instructor=None,
):
    return _get_instructor_form_records(
        "safety_briefing",
        limit=limit,
        offset=offset,
        student_group=student_group,
        course=course,
        instructor=instructor,
    )


SAFETY_BRIEFING_TYPES = [
    "Basic H2S",
    "TBOSIET",
    "TSbB",
    "TFOET",
    "THUET",
    "BOSIET EBS",
    "FOET EBS",
    "HUET EBS",
]

SAFETY_BRIEFING_COURSE_HINTS = [
    ("Basic H2S", ("BASIC H2S", "H2S", "OPITO H2S")),
    ("TBOSIET", ("TBOSIET", "T BOSIET", "TROPICAL BOSIET")),
    ("TSbB", ("TSBB", "T SBB", "TSBB")),
    ("TFOET", ("TFOET", "T FOET", "TROPICAL FOET")),
    ("THUET", ("THUET", "T HUET")),
    ("BOSIET EBS", ("BOSIET EBS", "BOSIET")),
    ("FOET EBS", ("FOET EBS", "FOET")),
    ("HUET EBS", ("HUET EBS", "HUET")),
]


def _guess_briefing_type_for_course(course_name):
    course_name = (course_name or "").strip().upper()
    if not course_name:
        return None
    for briefing_type, keywords in SAFETY_BRIEFING_COURSE_HINTS:
        if any(keyword in course_name for keyword in keywords):
            return briefing_type
    return None


def _pick_group_briefing(briefings):
    if not briefings:
        return None
    submitted = [row for row in briefings if row.docstatus == 1]
    if submitted:
        return submitted[0]
    return briefings[0]


@frappe.whitelist()
def get_safety_briefing_group_status(student_group=None, course=None, instructor=None):
    user = frappe.session.user
    roles = frappe.get_roles(user)
    student_group = (student_group or "").strip()
    course = (course or "").strip()
    instructor = (instructor or "").strip()
    empty_response = {
        "groups": [],
        "summary": {"total": 0, "submitted": 0, "draft": 0, "pending": 0},
        "briefing_types": SAFETY_BRIEFING_TYPES,
    }

    student_group_names = _resolve_student_group_names(user, roles, instructor)
    if student_group_names == []:
        return empty_response

    scoped_groups = _scope_student_group_names(student_group_names, student_group, course)
    if scoped_groups == []:
        return empty_response

    group_filters = {}
    if scoped_groups is not None:
        group_filters["name"] = ["in", scoped_groups]

    groups = frappe.get_all(
        "Student Group",
        filters=group_filters,
        fields=["name", "course"],
        order_by="modified desc",
        limit=300,
    )
    if not groups:
        return {
            "groups": [],
            "summary": {"total": 0, "submitted": 0, "draft": 0, "pending": 0},
            "briefing_types": SAFETY_BRIEFING_TYPES,
        }

    group_names = [row.name for row in groups]
    briefing_rows = frappe.get_all(
        "Safety Briefing",
        filters={"student_group": ["in", group_names], "docstatus": ["<", 2]},
        fields=[
            "name",
            "student_group",
            "briefing_type",
            "briefing_date",
            "docstatus",
            "modified",
        ],
        order_by="modified desc",
    )

    briefings_by_group = {}
    for row in briefing_rows:
        briefings_by_group.setdefault(row.student_group, []).append(row)

    status_order = {"pending": 0, "draft": 1, "submitted": 2}
    rows = []
    summary = {"total": 0, "submitted": 0, "draft": 0, "pending": 0}

    for group in groups:
        expected_type = _guess_briefing_type_for_course(group.course)
        briefing = _pick_group_briefing(briefings_by_group.get(group.name) or [])
        if briefing:
            status = "submitted" if briefing.docstatus == 1 else "draft"
            summary[status] += 1
        else:
            status = "pending"
            summary["pending"] += 1
        summary["total"] += 1

        rows.append(
            {
                "student_group": group.name,
                "course": group.course,
                "expected_briefing_type": expected_type,
                "status": status,
                "briefing_name": briefing.name if briefing else None,
                "briefing_type": briefing.briefing_type if briefing else expected_type,
                "briefing_date": briefing.briefing_date if briefing else None,
                "docstatus": briefing.docstatus if briefing else None,
                "modified": briefing.modified if briefing else None,
            }
        )

    rows.sort(
        key=lambda row: (
            status_order.get(row["status"], 9),
            row.get("student_group") or "",
        )
    )
    return {"groups": rows, "summary": summary, "briefing_types": SAFETY_BRIEFING_TYPES}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_instructor_student_groups(doctype, txt, searchfield, start, page_len, filters):
    user = frappe.session.user
    roles = frappe.get_roles(user)
    student_group_names = _resolve_student_group_names(user, roles)
    course = ((filters or {}).get("course") or "").strip()

    if student_group_names == []:
        return []

    name_filters = []
    if student_group_names is not None:
        name_filters.append(["name", "in", student_group_names])
    if course:
        name_filters.append(["course", "=", course])
    if txt:
        name_filters.append(["name", "like", f"%{txt}%"])

    rows = frappe.get_all(
        "Student Group",
        filters=name_filters,
        fields=["name"],
        order_by="name desc",
        start=start,
        page_length=page_len,
    )
    return [[row.name] for row in rows]


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_instructor_courses(doctype, txt, searchfield, start, page_len, filters):
    user = frappe.session.user
    roles = frappe.get_roles(user)
    student_group_names = _resolve_student_group_names(user, roles)

    if student_group_names == []:
        return []

    group_filters = []
    if student_group_names is not None:
        group_filters.append(["name", "in", student_group_names])

    groups = frappe.get_all(
        "Student Group",
        filters=group_filters,
        fields=["course"],
        distinct=True,
    )
    course_names = sorted({group.course for group in groups if group.course})
    if not course_names:
        return []

    course_filters = [["name", "in", course_names]]
    if txt:
        course_filters.append(["name", "like", f"%{txt}%"])

    rows = frappe.get_all(
        "Course",
        filters=course_filters,
        fields=["name", "course_name"],
        order_by="course_name asc",
        start=start,
        page_length=page_len,
    )
    return [[row.name, row.course_name] for row in rows]


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
