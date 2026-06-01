import frappe
from frappe import _
from frappe.utils import formatdate, getdate, today


def can_bypass_assessment_eligibility_check():
	roles = set(frappe.get_roles(frappe.session.user or "Guest"))
	return bool(roles.intersection({"System Manager", "Administrator"}))


def _attendance_is_valid_for_assessment(attendance):
	if not attendance:
		return False, "missing"
	if attendance.get("status") != "Present":
		return False, "absent"
	if not attendance.get("custom_student_signature"):
		return False, "no_signature"
	if attendance.get("docstatus") != 1:
		return False, "not_submitted"
	return True, "ok"


def get_assessment_eligibility(student, student_group):
	"""Check whether student attended and signed all course schedule days."""
	if not student or not student_group:
		return {
			"eligible": False,
			"message": _("Student and student group are required for assessment eligibility."),
			"total_days": 0,
			"missing_days": 0,
			"missing_dates": [],
		}

	if can_bypass_assessment_eligibility_check():
		return {
			"eligible": True,
			"message": "",
			"total_days": 0,
			"missing_days": 0,
			"missing_dates": [],
			"bypassed": True,
		}

	schedules = frappe.get_all(
		"Course Schedule",
		filters={"student_group": student_group, "docstatus": ["<", 2]},
		fields=["name", "schedule_date"],
		order_by="schedule_date asc",
	)

	if not schedules:
		return {
			"eligible": True,
			"message": "",
			"total_days": 0,
			"missing_days": 0,
			"missing_dates": [],
			"no_schedules": True,
		}

	missing_dates = []
	missing_reasons = []
	today_date = getdate(today())

	for schedule in schedules:
		schedule_date = getdate(schedule.schedule_date) if schedule.schedule_date else None
		# Attendance is only required for days that have already occurred (including today).
		if schedule_date and schedule_date > today_date:
			continue

		attendance = frappe.db.get_value(
			"Student Attendance",
			{
				"student": student,
				"student_group": student_group,
				"course_schedule": schedule.name,
				"docstatus": ["<", 2],
			},
			["name", "status", "custom_student_signature", "docstatus", "date"],
			as_dict=True,
		)
		is_valid, reason = _attendance_is_valid_for_assessment(attendance)
		if not is_valid:
			schedule_date = schedule.schedule_date or (attendance.date if attendance else None)
			missing_dates.append(formatdate(getdate(schedule_date)) if schedule_date else schedule.name)
			missing_reasons.append(reason)

	total_days = len(schedules)
	missing_days = len(missing_dates)
	eligible = missing_days == 0

	message = ""
	if not eligible:
		date_text = ", ".join(missing_dates[:5])
		if len(missing_dates) > 5:
			date_text = f"{date_text}, ..."
		message = _(
			"You are not eligible for assessment. This is a {0}-day course and you are not present "
			"(or attendance signature is missing) for {1} day(s): {2}."
		).format(total_days, missing_days, date_text)

	return {
		"eligible": eligible,
		"message": message,
		"total_days": total_days,
		"missing_days": missing_days,
		"missing_dates": missing_dates,
		"missing_reasons": missing_reasons,
	}


def ensure_assessment_eligible(student, student_group, throw=True):
	result = get_assessment_eligibility(student, student_group)
	if result.get("eligible"):
		return result

	if throw:
		frappe.throw(result.get("message") or _("You are not eligible for assessment."), title=_("Not Eligible"))

	return result


@frappe.whitelist(allow_guest=True)
def check_assessment_eligibility(student, student_group):
	result = get_assessment_eligibility(student, student_group)
	return {"status": "success", **result}
