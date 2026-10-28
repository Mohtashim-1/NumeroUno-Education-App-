"""Auto-open Course Schedule rows from Course flags on the Training Schedule.

Staff tick **Auto Create Daily Session** on Course (plus slots / weekdays).
A daily job opens missing morning/afternoon sessions for the next week.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, today

from numerouno.numerouno.api.training_schedule import (
	PERIODS,
	_active_instructor,
	_match_course_name,
	_period_by_key,
	_validate_session_portal,
)

FLAG_AUTO = "custom_auto_create_daily_session"
FIELD_SLOTS = "custom_daily_session_slots"
FIELD_WEEKDAYS = "custom_daily_session_weekdays"

TITLE_MARK = "Regular schedule"
WEEKDAY_MAP = {
	"MON": 0,
	"TUE": 1,
	"WED": 2,
	"THU": 3,
	"FRI": 4,
	"SAT": 5,
	"SUN": 6,
	"MONDAY": 0,
	"TUESDAY": 1,
	"WEDNESDAY": 2,
	"THURSDAY": 3,
	"FRIDAY": 4,
	"SATURDAY": 5,
	"SUNDAY": 6,
}


def _slots_from_label(label: str) -> list[dict]:
	text = (label or "").strip().lower()
	if text == "afternoon":
		return [PERIODS[1]]
	if text == "evening":
		return [PERIODS[2]]
	if text in {"morning & afternoon", "morning and afternoon", "8am/1pm"}:
		return [PERIODS[0], PERIODS[1]]
	# default morning
	return [PERIODS[0]]


def _weekdays_from_label(label: str) -> set[int] | None:
	"""None = Mon–Sat (Sunday holiday). Else specific weekdays."""
	text = (label or "").upper().replace("-", ",").replace("/", ",")
	found = set()
	for token in text.replace(" ", "").split(","):
		if token in WEEKDAY_MAP:
			found.add(WEEKDAY_MAP[token])
	return found or None


def _resolve_course(hint: str) -> str:
	if frappe.db.exists("Course", hint):
		return hint
	matched = _match_course_name(hint)
	if matched:
		return matched
	row = frappe.db.sql(
		"""
		select name from `tabCourse`
		where lower(name) like %(q)s or lower(ifnull(course_name,'')) like %(q)s
		order by length(name) asc
		limit 1
		""",
		{"q": f"%{(hint or '').lower().strip()}%"},
	)
	return row[0][0] if row else ""


def _flagged_courses() -> list[dict]:
	if not frappe.db.has_column("Course", FLAG_AUTO):
		return []
	return frappe.get_all(
		"Course",
		filters={FLAG_AUTO: 1},
		fields=["name", FIELD_SLOTS, FIELD_WEEKDAYS],
	)


def _session_exists(course: str, day, from_time: str) -> str | None:
	row = frappe.db.sql(
		"""
		select name from `tabCourse Schedule`
		where course = %(course)s
		  and schedule_date = %(day)s
		  and from_time = %(from_time)s
		limit 1
		""",
		{"course": course, "day": day, "from_time": from_time},
	)
	return row[0][0] if row else None


def _ensure_group(course: str, instructor: str) -> str:
	"""One standing Student Group per course — avoid emails/SO spam per day."""
	year = str(getdate().year)
	if not frappe.db.exists("Academic Year", year):
		year = frappe.db.get_value("Academic Year", {}, "name", order_by="year_start_date desc") or year
	group_name = f"Regular · {course}"[:140]
	existing = frappe.db.get_value("Student Group", {"student_group_name": group_name}, "name")
	if existing:
		return existing
	if frappe.db.exists("Student Group", group_name):
		return group_name

	frappe.flags.mute_emails = True
	frappe.flags.in_import = True
	try:
		group = frappe.get_doc(
			{
				"doctype": "Student Group",
				"academic_year": year,
				"group_based_on": "Course",
				"student_group_name": group_name,
				"course": course,
				"max_strength": 40,
				"instructors": [{"instructor": instructor}] if instructor else [],
			}
		)
		group.flags.ignore_permissions = True
		group.flags.ignore_links = True
		group.insert()
		return group.name
	finally:
		frappe.flags.mute_emails = False
		frappe.flags.in_import = False


def _create_session(course: str, day, period: dict, instructor: str) -> dict:
	existing = _session_exists(course, day, period["from_time"])
	if existing:
		return {"created": False, "reason": "exists", "name": existing, "course": course}

	if not instructor:
		return {"created": False, "reason": "no_instructor", "course": course}

	group_name = _ensure_group(course, instructor)
	doc = frappe.new_doc("Course Schedule")
	doc.student_group = group_name
	doc.instructor = instructor
	doc.schedule_date = day
	doc.from_time = period["from_time"]
	doc.to_time = period["to_time"]
	doc.course = course
	doc.flags.ignore_permissions = True
	doc.flags.ignore_mandatory = True
	doc.validate = lambda: _validate_session_portal(doc)
	doc.save()
	doc.db_set("title", f"{course} · {TITLE_MARK} · {period['label']}"[:140])
	return {
		"created": True,
		"name": doc.name,
		"course": course,
		"date": str(day),
		"period": period["key"],
		"student_group": group_name,
	}


def ensure_regular_schedules(days_ahead: int = 7, from_date=None) -> dict:
	"""Open missing sessions for flagged courses: today .. today+days_ahead."""
	days_ahead = max(1, min(cint(days_ahead) or 7, 31))
	start = getdate(from_date) if from_date else getdate(today())
	created = []
	skipped = []
	no_instructor = []
	courses = _flagged_courses()

	if not courses:
		return {
			"from": str(start),
			"days": days_ahead,
			"created": 0,
			"skipped": 0,
			"flagged_courses": 0,
			"no_instructor": [],
			"sessions": [],
			"message": "No Course has Auto Create Daily Session checked.",
		}

	for offset in range(days_ahead):
		day = add_days(start, offset)
		for row in courses:
			course = row["name"]
			weekdays = _weekdays_from_label(row.get(FIELD_WEEKDAYS) or "")
			if weekdays is not None:
				if day.weekday() not in weekdays:
					continue
			elif day.weekday() == 6:  # Sunday off by default
				continue

			instructor = _active_instructor(course)
			if not instructor:
				instructor = frappe.db.get_value("Instructor", {"status": "Active"}, "name") or ""
			if not instructor:
				no_instructor.append(course)
				continue

			for period in _slots_from_label(row.get(FIELD_SLOTS) or "Morning"):
				result = _create_session(course, day, period, instructor)
				if result.get("created"):
					created.append(result)
				else:
					skipped.append(result)

	frappe.db.commit()
	return {
		"from": str(start),
		"days": days_ahead,
		"created": len(created),
		"skipped": len(skipped),
		"flagged_courses": len(courses),
		"no_instructor": sorted(set(no_instructor)),
		"sessions": created[:50],
	}


def ensure_regular_schedules_daily():
	"""Scheduler entry: keep the next week of regular slots open."""
	return ensure_regular_schedules(days_ahead=7)


@frappe.whitelist(allow_guest=True)
def run_regular_schedule_now(days_ahead=7, from_date=None):
	"""Manual run from desk / console, or Avynqo with the shared booking secret."""
	from numerouno.numerouno.api.training_schedule import _booking_secret_ok, _require_manage

	if not _booking_secret_ok():
		if frappe.session.user == "Guest":
			frappe.throw(_("Not allowed."), frappe.PermissionError)
		_require_manage()
	return ensure_regular_schedules(days_ahead=days_ahead, from_date=from_date)
