from datetime import timedelta
import csv
import io

import frappe
from frappe import _
from frappe.utils import add_days, cint, format_date, getdate, now_datetime, today


ROLE = "Training Portal"
PORTAL_ROLES = frozenset({"Training Portal", "Training Schedule"})

# Seeded once. After that, add or remove the Training Portal role on the User.
INITIAL_USERS = (
	"tenorio.j@numerouno-me.com",  # Jeselle
	"s.arshad@numerouno-me.com",  # Seyad Arshad
	"j.jeyakumar@numerouno-me.com",  # Jebisha
	"f.kaneez@numerouno-me.com",  # Kaneez
	"j.carlo@numerouno-me.com",  # Jan Carlo
	"a.sravon@numerouno-me.com",  # Afsana
)

DEFAULT_SLOTS = [
	("08:00:00", "12:00:00"),
	("13:00:00", "17:00:00"),
	("18:00:00", "22:00:00"),
]

PERIODS = (
	{"key": "morning", "label": "Morning", "from_time": "08:00:00", "to_time": "12:00:00"},
	{"key": "afternoon", "label": "Afternoon", "from_time": "13:00:00", "to_time": "17:00:00"},
	{"key": "evening", "label": "Evening", "from_time": "18:00:00", "to_time": "22:00:00"},
)

COURSE_COLORS = [
	{"key": "leadership", "label": "Leadership", "tone": "blue"},
	{"key": "communication", "label": "Communication", "tone": "green"},
	{"key": "technical", "label": "Technical", "tone": "purple"},
	{"key": "management", "label": "Management", "tone": "yellow"},
	{"key": "marketing", "label": "Marketing", "tone": "pink"},
	{"key": "sales", "label": "Sales", "tone": "teal"},
	{"key": "other", "label": "Other", "tone": "grey"},
]


def _allowed_user(user=None):
	user = (user or frappe.session.user or "").strip()
	if not user or user == "Guest":
		return False
	if user == "Administrator":
		return True
	return bool(PORTAL_ROLES & set(frappe.get_roles(user)))


def _can_view():
	return _allowed_user()


def _can_manage():
	return _allowed_user()


def _require_view():
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in to open the Training Schedule."), frappe.PermissionError)
	if not _can_view():
		frappe.throw(_("You are not allowed to open the Training Schedule."), frappe.PermissionError)


def _require_manage():
	_require_view()
	if not _can_manage():
		frappe.throw(_("You are not allowed to change the training schedule."), frappe.PermissionError)


def _fmt_time(value):
	if value is None or value == "":
		return ""
	if hasattr(value, "total_seconds"):
		total = int(value.total_seconds()) % (24 * 3600)
		hours, rem = divmod(total, 3600)
		minutes = rem // 60
		return f"{hours:02d}:{minutes:02d}"
	text = str(value)
	if " " in text:
		text = text.split(" ")[-1]
	parts = text.split(":")
	if len(parts) >= 2:
		return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
	return text[:5]


def _as_sql_time(value):
	text = (value or "").strip()
	if not text:
		frappe.throw(_("Time is required."))
	if len(text) == 5:
		return text + ":00"
	return text


def _week_bounds(week_start=None):
	base = getdate(week_start) if week_start else getdate()
	monday = base - timedelta(days=base.weekday())
	sunday = add_days(monday, 6)
	return monday, sunday


def _range_bounds(start=None, days=7):
	days = cint(days) or 7
	if days <= 1:
		day = getdate(start) if start else getdate()
		return day, day, 1
	monday, sunday = _week_bounds(start)
	return monday, sunday, 7


def _hour_from_time(value):
	text = _fmt_time(value)
	if not text:
		return 8
	try:
		return int(text.split(":")[0])
	except Exception:
		return 8


def _period_from_time(from_time):
	hour = _hour_from_time(from_time)
	if hour < 12:
		return PERIODS[0]
	if hour < 17:
		return PERIODS[1]
	return PERIODS[2]


def _period_by_key(key):
	key = (key or "").strip().lower()
	for period in PERIODS:
		if period["key"] == key:
			return period
	return PERIODS[0]


def _room_label(room, room_name=None, room_number=None):
	return room_name or room_number or room or ""


def _course_title(course, course_name=None):
	title = (course_name or "").strip()
	if title:
		return title
	course = (course or "").strip()
	if not course:
		return ""
	return frappe.db.get_value("Course", course, "course_name") or course


def _resolve_course(course=None, course_name=None):
	course = (course or "").strip()
	course_name = (course_name or "").strip()
	if course and frappe.db.exists("Course", course):
		return course
	text = course_name or course
	if not text:
		return ""
	found = frappe.db.sql(
		"""
		select name
		from `tabCourse`
		where name = %(t)s or ifnull(course_name, '') = %(t)s
		limit 1
		""",
		{"t": text},
	)
	if found:
		return found[0][0]
	like = f"%{text}%"
	code_clause = ""
	if frappe.db.has_column("Course", "course_code"):
		code_clause = " or ifnull(course_code, '') like %(like)s"
	rows = frappe.db.sql(
		f"""
		select name
		from `tabCourse`
		where name like %(like)s or ifnull(course_name, '') like %(like)s{code_clause}
		order by modified desc
		limit 2
		""",
		{"like": like},
	)
	if len(rows) == 1:
		return rows[0][0]
	if len(rows) > 1:
		frappe.throw(_("Select a training from the list."))
	frappe.throw(_("Training “{0}” was not found. Search and pick it from the list.").format(text))


def _color_for_course(course):
	if not course:
		return COURSE_COLORS[-1]
	idx = sum(ord(ch) for ch in course) % (len(COURSE_COLORS) - 1)
	return COURSE_COLORS[idx]


def _session_status(schedule_date):
	day = getdate(schedule_date)
	now = getdate(today())
	if day < now:
		return "completed"
	if day == now:
		return "in_progress"
	return "upcoming"


def _time_hours(from_time, to_time):
	start = _fmt_time(from_time)
	end = _fmt_time(to_time)
	if not start or not end:
		return 0.0
	sh, sm = [int(part) for part in start.split(":")[:2]]
	eh, em = [int(part) for part in end.split(":")[:2]]
	minutes = (eh * 60 + em) - (sh * 60 + sm)
	if minutes < 0:
		minutes += 24 * 60
	return round(minutes / 60.0, 2)


def _serialize_session(row):
	color = _color_for_course(row.course)
	period = _period_from_time(row.from_time)
	return {
		"name": row.name,
		"date": str(row.schedule_date),
		"time_start": _fmt_time(period["from_time"]),
		"time_end": _fmt_time(period["to_time"]),
		"from_time": _fmt_time(period["from_time"]),
		"to_time": _fmt_time(period["to_time"]),
		"period": period["key"],
		"period_label": period["label"],
		"hours": _time_hours(period["from_time"], period["to_time"]),
		"instructor": row.instructor,
		"instructor_name": row.instructor_name or row.instructor,
		"instructor_image": "",
		"room": row.room,
		"room_name": _room_label(row.room, row.room_name, row.room_number),
		"student_group": row.student_group,
		"student_group_name": row.student_group_name or row.student_group,
		"course": row.course,
		"course_name": row.get("course_name") or row.course,
		"customer": row.custom_customer or "",
		"customer_company": row.customer_name or row.custom_customer or "",
		"color": row.color or "",
		"tone": color["tone"],
		"category": color["label"],
		"status": _session_status(row.schedule_date),
		"student_count": cint(row.get("student_count")),
		"booked": cint(row.get("booked") or row.get("student_count")),
		"invited": cint(row.get("invited") or row.get("booked") or row.get("student_count")),
		"came": cint(row.get("came")),
		"absent": cint(row.get("absent")),
		"max_strength": cint(row.get("max_strength")),
		"remaining": row.get("remaining"),
		"attendance_marked": bool(row.get("attendance_marked")),
	}


@frappe.whitelist()
def get_boot():
	_require_view()
	user = frappe.session.user
	fullname = frappe.db.get_value("User", user, "full_name") or user
	image = frappe.db.get_value("User", user, "user_image") or ""
	roles = frappe.get_roles()
	role_label = "Admin" if "System Manager" in roles else (roles[0] if roles else "User")
	monday, sunday = _week_bounds()
	return {
		"user": {
			"name": user,
			"full_name": fullname,
			"image": image,
			"role": role_label,
			"initials": "".join([p[0] for p in fullname.split()[:2]]).upper() or "U",
		},
		"can_manage": _can_manage(),
		"week_start": str(monday),
		"week_end": str(sunday),
		"today": str(getdate(today())),
		"periods": [
			{
				"key": p["key"],
				"label": p["label"],
				"from_time": p["from_time"][:5],
				"to_time": p["to_time"][:5],
			}
			for p in PERIODS
		],
		"slots": [
			{
				"key": p["key"],
				"label": p["label"],
				"from_time": p["from_time"][:5],
				"to_time": p["to_time"][:5],
			}
			for p in PERIODS
		],
		"categories": COURSE_COLORS,
	}


@frappe.whitelist()
def get_week(week_start=None, instructor=None, student_group=None, status=None, search=None, days=7):
	_require_view()
	start, end, day_count = _range_bounds(week_start, days)
	rows = frappe.db.sql(
		"""
		select
			cs.name, cs.schedule_date, cs.from_time, cs.to_time,
			cs.instructor, cs.instructor_name, cs.room, cs.course,
			cs.student_group, cs.color,
			sg.student_group_name, sg.custom_customer,
			c.customer_name,
			r.room_name, r.room_number,
			co.course_name
		from `tabCourse Schedule` cs
		left join `tabStudent Group` sg on sg.name = cs.student_group
		left join `tabCustomer` c on c.name = sg.custom_customer
		left join `tabRoom` r on r.name = cs.room
		left join `tabCourse` co on co.name = cs.course
		where cs.docstatus < 2
		  and cs.schedule_date between %(start)s and %(end)s
		order by cs.schedule_date asc, cs.from_time asc
		""",
		{"start": start, "end": end},
		as_dict=True,
	)

	sessions = [_serialize_session(row) for row in rows]
	_attach_student_counts(sessions)
	_attach_capacity(sessions)
	_apply_candidate_invite_counts(sessions)
	_attach_attendance(sessions)
	_attach_people_search(sessions)

	days_out = []
	for offset in range(day_count):
		day = add_days(start, offset)
		days_out.append(
			{
				"date": str(day),
				"label": day.strftime("%a"),
				"day_num": day.day,
				"is_today": str(day) == today(),
			}
		)

	slot_rows = [
		{
			"key": p["key"],
			"label": p["label"],
			"from_time": p["from_time"][:5],
			"to_time": p["to_time"][:5],
		}
		for p in PERIODS
	]

	trainers = _trainer_cards(sessions)
	rooms = _room_cards(sessions)
	groups = _group_cards(sessions)
	used_rooms = {row["room"] for row in sessions if row.get("room")}
	student_total = sum(cint(g.get("student_count")) for g in groups)

	return {
		"week_start": str(start),
		"week_end": str(end),
		"days_count": day_count,
		"days": days_out,
		"slots": slot_rows,
		"sessions": sessions,
		"stats": {
			"total": len(sessions),
			"completed": len([s for s in sessions if s["status"] == "completed"]),
			"in_progress": len([s for s in sessions if s["status"] == "in_progress"]),
			"upcoming": len([s for s in sessions if s["status"] == "upcoming"]),
			"hours": round(sum(s.get("hours") or 0 for s in sessions), 1),
			"rooms_used": len(used_rooms),
			"rooms_total": len(rooms) or cint(frappe.db.count("Room")) or 1,
			"trainers": len(trainers),
			"trainers_with_sessions": len([t for t in trainers if t.get("week_sessions")]),
			"students": student_total,
			"groups": len(groups),
			"capacity": sum(cint(g.get("max_strength")) for g in groups),
			"remaining": sum(cint(g.get("remaining") or 0) for g in groups if cint(g.get("max_strength"))),
			"invited": student_total,
			"came": _unique_came([g.get("student_group") for g in groups], start, end),
		},
		"trainers": trainers,
		"rooms": rooms,
		"groups": groups,
		"now": str(now_datetime()),
	}


@frappe.whitelist()
def search_links(doctype, txt="", student_group=None):
	_require_view()
	txt = (txt or "").strip()
	like = f"%{txt}%"
	doctype = (doctype or "").strip()

	if doctype == "Student Group":
		return frappe.db.sql(
			"""
			select sg.name, concat_ws(' — ', sg.student_group_name, c.customer_name) as description
			from `tabStudent Group` sg
			left join `tabCustomer` c on c.name = sg.custom_customer
			where sg.disabled = 0
			  and (sg.name like %(txt)s or sg.student_group_name like %(txt)s or ifnull(c.customer_name,'') like %(txt)s)
			order by sg.modified desc
			limit 20
			""",
			{"txt": like},
		)

	if doctype == "Instructor":
		if student_group:
			return frappe.db.sql(
				"""
				select i.name, i.instructor_name
				from `tabStudent Group Instructor` sgi
				inner join `tabInstructor` i on i.name = sgi.instructor
				where sgi.parent = %(student_group)s
				  and (i.name like %(txt)s or i.instructor_name like %(txt)s)
				order by sgi.idx
				limit 20
				""",
				{"student_group": student_group, "txt": like},
			)
		return frappe.db.sql(
			"""
			select name, instructor_name
			from `tabInstructor`
			where ifnull(status, 'Active') != 'Left'
			  and (name like %(txt)s or instructor_name like %(txt)s)
			order by instructor_name
			limit 20
			""",
			{"txt": like},
		)

	if doctype == "Room":
		return frappe.db.sql(
			"""
			select name, concat_ws(' / ', room_name, room_number) as description
			from `tabRoom`
			where name like %(txt)s or ifnull(room_name,'') like %(txt)s or ifnull(room_number,'') like %(txt)s
			order by room_name
			limit 20
			""",
			{"txt": like},
		)

	if doctype == "Customer":
		return frappe.db.sql(
			"""
			select name, customer_name
			from `tabCustomer`
			where disabled = 0
			  and (name like %(txt)s or customer_name like %(txt)s)
			order by modified desc
			limit 20
			""",
			{"txt": like},
		)

	if doctype == "Course":
		code_select = "ifnull(course_code, '')"
		code_where = ""
		if frappe.db.has_column("Course", "course_code"):
			code_where = " or ifnull(course_code, '') like %(txt)s"
		else:
			code_select = "''"
		return frappe.db.sql(
			f"""
			select
				name,
				case
					when {code_select} != '' and {code_select} != ifnull(course_name, name)
						then concat(ifnull(course_name, name), ' (', {code_select}, ')')
					else ifnull(course_name, name)
				end as description
			from `tabCourse`
			where name like %(txt)s
			   or ifnull(course_name, '') like %(txt)s
			   {code_where}
			order by course_name
			limit 20
			""",
			{"txt": like},
		)

	frappe.throw(_("Unsupported search type."))


@frappe.whitelist()
def get_student_group_defaults(student_group, date=None):
	_require_view()
	if not student_group:
		frappe.throw(_("Student Group is required."))
	sg = frappe.db.get_value(
		"Student Group",
		student_group,
		["name", "student_group_name", "course", "custom_customer", "custom_coarse_location", "max_strength"],
		as_dict=True,
	)
	if not sg:
		frappe.throw(_("Student Group not found."))
	customer_name = (
		frappe.db.get_value("Customer", sg.custom_customer, "customer_name") if sg.custom_customer else ""
	)
	room_name = ""
	if sg.custom_coarse_location:
		room_name = frappe.db.get_value("Room", sg.custom_coarse_location, "room_name") or sg.custom_coarse_location
	instructors = frappe.get_all(
		"Student Group Instructor",
		filters={"parent": student_group},
		fields=["instructor", "instructor_name"],
		order_by="idx",
	)
	booked = cint(
		frappe.db.count("Student Group Student", {"parent": student_group})
	)
	capacity = _capacity_payload(booked, sg.max_strength, sg.course)
	attendance = _attendance_counts(student_group, date)
	return {
		"student_group": sg.name,
		"student_group_name": sg.student_group_name,
		"course": sg.course,
		"course_name": _course_title(sg.course),
		"customer": sg.custom_customer,
		"customer_company": customer_name or sg.custom_customer or "",
		"room": sg.custom_coarse_location,
		"room_name": room_name,
		"instructors": instructors,
		"instructor": instructors[0].instructor if instructors else "",
		"instructor_name": instructors[0].instructor_name if instructors else "",
		**capacity,
		**attendance,
	}


@frappe.whitelist()
def save_session(data):
	_require_manage()
	payload = frappe.parse_json(data) if isinstance(data, str) else data
	student_group = (payload.get("student_group") or "").strip()
	instructor = (payload.get("instructor") or "").strip()
	schedule_date = payload.get("date") or payload.get("schedule_date")
	period = _period_by_key(payload.get("period"))
	if not payload.get("period"):
		period = _period_from_time(payload.get("from_time") or payload.get("time_start"))
	from_time = period["from_time"]
	to_time = period["to_time"]
	room = (payload.get("room") or "").strip()
	course = _resolve_course(payload.get("course"), payload.get("course_name"))
	name = (payload.get("name") or "").strip()

	if not instructor:
		frappe.throw(_("Instructor is required."))
	if not schedule_date:
		frappe.throw(_("Date is required."))
	if student_group and not room:
		defaults = get_student_group_defaults(student_group)
		room = defaults.get("room") or ""
	if student_group and not course:
		course = frappe.db.get_value("Student Group", student_group, "course") or ""

	if name:
		doc = frappe.get_doc("Course Schedule", name)
	else:
		doc = frappe.new_doc("Course Schedule")

	doc.student_group = student_group or None
	doc.instructor = instructor
	doc.schedule_date = getdate(schedule_date)
	doc.from_time = from_time
	doc.to_time = to_time
	doc.room = room or None
	doc.course = course or None
	doc.flags.ignore_permissions = True
	doc.flags.ignore_mandatory = True
	if not student_group:
		doc.validate = lambda: _validate_session_without_group(doc)
	doc.save()
	if student_group and payload.get("max_strength") not in (None, ""):
		_set_group_max_strength(student_group, payload.get("max_strength"))
	return {"name": doc.name}


def _move_session_candidates(course_schedule, new_date):
	if not course_schedule or not _candidate_table_exists():
		return 0
	if not frappe.db.has_column("Training Candidate", "date"):
		return 0
	count = cint(
		frappe.db.count("Training Candidate", {"course_schedule": course_schedule})
	)
	if count:
		frappe.db.sql(
			"""
			update `tabTraining Candidate`
			set date = %(date)s
			where course_schedule = %(course_schedule)s
			""",
			{"date": getdate(new_date), "course_schedule": course_schedule},
		)
	return count


@frappe.whitelist()
def reschedule_session(name, date, period=None):
	_require_manage()
	name = (name or "").strip()
	if not name:
		frappe.throw(_("Session is required."))
	if not date:
		frappe.throw(_("New date is required."))
	if not frappe.db.exists("Course Schedule", name):
		frappe.throw(_("Course Schedule {0} not found.").format(name))

	doc = frappe.get_doc("Course Schedule", name)
	new_date = getdate(date)
	period_row = _period_by_key(period) if period else _period_from_time(doc.from_time)
	old_date = doc.schedule_date
	same_slot = str(old_date) == str(new_date) and _fmt_time(doc.from_time) == _fmt_time(period_row["from_time"])
	if same_slot:
		frappe.throw(_("Pick a different date or schedule."))

	doc.schedule_date = new_date
	doc.from_time = period_row["from_time"]
	doc.to_time = period_row["to_time"]
	doc.flags.ignore_permissions = True
	doc.flags.ignore_mandatory = True
	if not doc.student_group:
		doc.validate = lambda: _validate_session_without_group(doc)
	doc.save()
	moved = _move_session_candidates(name, new_date)
	return {
		"name": doc.name,
		"date": str(new_date),
		"old_date": str(old_date),
		"period": period_row["key"],
		"period_label": period_row["label"],
		"moved_candidates": moved,
	}


def _validate_session_without_group(doc):
	if doc.instructor:
		doc.instructor_name = frappe.db.get_value("Instructor", doc.instructor, "instructor_name")
	label = doc.course or "Training Session"
	doc.title = f"{label} by {(doc.instructor_name or doc.instructor)}"
	doc.validate_time()
	from education.education.utils import validate_overlap_for

	validate_overlap_for(doc, "Course Schedule", "instructor")
	if doc.room:
		validate_overlap_for(doc, "Course Schedule", "room")
		validate_overlap_for(doc, "Assessment Plan", "room")
	validate_overlap_for(doc, "Assessment Plan", "supervisor", doc.instructor)


@frappe.whitelist()
def save_max_strength(student_group, max_strength):
	_require_manage()
	if not student_group:
		frappe.throw(_("Student Group is required."))
	max_strength = _set_group_max_strength(student_group, max_strength)
	booked = cint(frappe.db.count("Student Group Student", {"parent": student_group}))
	course = frappe.db.get_value("Student Group", student_group, "course")
	return {"student_group": student_group, **_capacity_payload(booked, max_strength, course)}


@frappe.whitelist()
def delete_session(name):
	_require_manage()
	if not name:
		frappe.throw(_("Session is required."))
	frappe.delete_doc("Course Schedule", name, ignore_permissions=True)
	return {"ok": 1}


def _attach_student_counts(sessions):
	groups = list({row["student_group"] for row in sessions if row.get("student_group")})
	if not groups:
		return
	rows = frappe.db.sql(
		"""
		select parent, count(*) as student_count
		from `tabStudent Group Student`
		where parent in %(groups)s
		group by parent
		""",
		{"groups": groups},
		as_dict=True,
	)
	counts = {row.parent: cint(row.student_count) for row in rows}
	for session in sessions:
		session["student_count"] = counts.get(session.get("student_group"), 0)


def _course_max_strength(course):
	if not course or not frappe.db.has_column("Course", "custom_max_strength"):
		return 0
	return cint(frappe.db.get_value("Course", course, "custom_max_strength"))


def _capacity_payload(booked, max_strength, course=None):
	booked = cint(booked)
	max_strength = cint(max_strength)
	course_max = _course_max_strength(course) if course else 0
	if not max_strength and course_max:
		max_strength = course_max
	remaining = None
	overbooked = 0
	if max_strength:
		remaining = max_strength - booked
		if remaining < 0:
			overbooked = abs(remaining)
			remaining = 0
	return {
		"booked": booked,
		"invited": booked,
		"max_strength": max_strength,
		"course_max_strength": course_max,
		"remaining": remaining,
		"overbooked": overbooked,
	}


def _set_group_max_strength(student_group, max_strength):
	max_strength = cint(max_strength)
	if max_strength < 0:
		frappe.throw(_("Max strength cannot be less than zero."))
	frappe.db.set_value("Student Group", student_group, "max_strength", max_strength)
	return max_strength


def _attach_capacity(sessions):
	groups = list({row["student_group"] for row in sessions if row.get("student_group")})
	group_max = {}
	group_course = {}
	if groups:
		rows = frappe.db.sql(
			"""
			select name, max_strength, course
			from `tabStudent Group`
			where name in %(groups)s
			""",
			{"groups": groups},
			as_dict=True,
		)
		for row in rows:
			group_max[row.name] = cint(row.max_strength)
			group_course[row.name] = row.course
	course_max = {}
	if frappe.db.has_column("Course", "custom_max_strength"):
		courses = list({group_course.get(g) or "" for g in groups} | {row.get("course") or "" for row in sessions})
		courses = [name for name in courses if name]
		if courses:
			rows = frappe.db.sql(
				"""
				select name, custom_max_strength
				from `tabCourse`
				where name in %(courses)s
				""",
				{"courses": courses},
				as_dict=True,
			)
			course_max = {row.name: cint(row.custom_max_strength) for row in rows}
	for session in sessions:
		group = session.get("student_group")
		course = session.get("course") or group_course.get(group)
		capacity = _capacity_payload(
			session.get("student_count"),
			group_max.get(group),
			None,
		)
		if not capacity["max_strength"]:
			capacity["max_strength"] = course_max.get(course, 0)
			if capacity["max_strength"]:
				capacity = _capacity_payload(session.get("student_count"), capacity["max_strength"], None)
		capacity["course_max_strength"] = course_max.get(course, 0)
		session.update(capacity)


def _attendance_counts(student_group, date=None, course_schedule=None):
	if not student_group:
		return {"came": 0, "absent": 0, "attendance_marked": False, "no_show": 0}
	conditions = ["ifnull(docstatus, 0) < 2", "student_group = %(student_group)s"]
	values = {"student_group": student_group}
	if course_schedule:
		conditions.append("course_schedule = %(course_schedule)s")
		values["course_schedule"] = course_schedule
	elif date:
		conditions.append("date = %(date)s")
		values["date"] = date
	else:
		return {"came": 0, "absent": 0, "attendance_marked": False, "no_show": 0}
	rows = frappe.db.sql(
		f"""
		select status, count(distinct student) as cnt
		from `tabStudent Attendance`
		where {" and ".join(conditions)}
		group by status
		""",
		values,
		as_dict=True,
	)
	came = 0
	absent = 0
	for row in rows:
		if (row.status or "").lower() == "present":
			came = cint(row.cnt)
		elif (row.status or "").lower() == "absent":
			absent = cint(row.cnt)
	marked = came + absent > 0
	return {
		"came": came,
		"absent": absent,
		"attendance_marked": marked,
		"no_show": absent,
	}


def _attach_attendance(sessions):
	groups = list({row["student_group"] for row in sessions if row.get("student_group")})
	dates = list({row["date"] for row in sessions if row.get("date")})
	if not groups or not dates:
		for session in sessions:
			session.update({"came": 0, "absent": 0, "attendance_marked": False, "no_show": 0})
		return
	rows = frappe.db.sql(
		"""
		select student_group, date, status, count(distinct student) as cnt
		from `tabStudent Attendance`
		where ifnull(docstatus, 0) < 2
		  and student_group in %(groups)s
		  and date in %(dates)s
		group by student_group, date, status
		""",
		{"groups": groups, "dates": dates},
		as_dict=True,
	)
	counts = {}
	for row in rows:
		key = (row.student_group, str(row.date))
		bucket = counts.setdefault(key, {"came": 0, "absent": 0})
		if (row.status or "").lower() == "present":
			bucket["came"] = cint(row.cnt)
		elif (row.status or "").lower() == "absent":
			bucket["absent"] = cint(row.cnt)
	for session in sessions:
		bucket = counts.get((session.get("student_group"), str(session.get("date") or ""))) or {}
		came = cint(bucket.get("came"))
		absent = cint(bucket.get("absent"))
		invited = cint(session.get("invited") or session.get("booked") or session.get("student_count"))
		session["came"] = came
		session["absent"] = absent
		session["attendance_marked"] = (came + absent) > 0
		session["no_show"] = max(invited - came, 0) if session["attendance_marked"] else 0


def _unique_came(groups, start, end):
	groups = [name for name in groups if name]
	if not groups:
		return 0
	return cint(
		frappe.db.sql(
			"""
			select count(distinct student)
			from `tabStudent Attendance`
			where ifnull(docstatus, 0) < 2
			  and status = 'Present'
			  and student_group in %(groups)s
			  and date between %(start)s and %(end)s
			""",
			{"groups": groups, "start": start, "end": end},
		)[0][0]
	)


def _year_instructor_totals():
	rows = frappe.db.sql(
		"""
		select
			instructor,
			count(*) as year_sessions,
			round(sum(
				case
					when from_time is null or to_time is null then 0
					when to_time >= from_time then timestampdiff(minute, from_time, to_time)
					else timestampdiff(minute, from_time, to_time) + 1440
				end
			) / 60, 1) as year_hours
		from `tabCourse Schedule`
		where docstatus < 2
		  and ifnull(instructor, '') != ''
		  and year(schedule_date) = year(%(today)s)
		group by instructor
		""",
		{"today": today()},
		as_dict=True,
	)
	return {row.instructor: row for row in rows}


def _empty_trainer(name, instructor_name="", status="Active"):
	return {
		"name": name,
		"instructor_name": instructor_name or name,
		"status": status,
		"week_sessions": 0,
		"week_hours": 0,
		"week_groups": 0,
		"week_students": 0,
		"year_sessions": 0,
		"year_hours": 0,
		"_groups": set(),
	}


def _trainer_cards(sessions):
	trainers = frappe.db.sql(
		"""
		select name, instructor_name, status
		from `tabInstructor`
		where ifnull(status, 'Active') != 'Left'
		order by instructor_name asc
		limit 300
		""",
		as_dict=True,
	)
	by_id = {
		row.name: _empty_trainer(row.name, row.instructor_name, row.status) for row in trainers
	}
	year_totals = _year_instructor_totals()
	for session in sessions:
		tid = session.get("instructor")
		if not tid:
			continue
		if tid not in by_id:
			by_id[tid] = _empty_trainer(tid, session.get("instructor_name"))
		rec = by_id[tid]
		rec["week_sessions"] += 1
		rec["week_hours"] += session.get("hours") or 0
		if session.get("student_group"):
			rec["_groups"].add(session["student_group"])
	group_students = {row["student_group"]: cint(row.get("student_count")) for row in sessions if row.get("student_group")}
	cards = []
	for rec in by_id.values():
		groups = rec.pop("_groups")
		year = year_totals.get(rec["name"]) or {}
		rec["week_groups"] = len(groups)
		rec["week_students"] = sum(group_students.get(group, 0) for group in groups)
		rec["week_hours"] = round(rec["week_hours"], 1)
		rec["year_sessions"] = cint(year.get("year_sessions"))
		rec["year_hours"] = float(year.get("year_hours") or 0)
		cards.append(rec)
	cards.sort(key=lambda row: (-row["week_sessions"], -row["year_sessions"], (row["instructor_name"] or "").lower()))
	return cards


def _room_cards(sessions):
	rooms = frappe.db.sql(
		"""
		select name, room_name, room_number, seating_capacity
		from `tabRoom`
		order by ifnull(room_name, name) asc
		limit 300
		""",
		as_dict=True,
	)
	by_id = {
		row.name: {
			"name": row.name,
			"room_name": _room_label(row.name, row.room_name, row.room_number),
			"room_number": row.room_number,
			"seating_capacity": cint(row.seating_capacity),
			"week_sessions": 0,
			"week_hours": 0,
			"week_groups": 0,
			"_groups": set(),
		}
		for row in rooms
	}
	for session in sessions:
		rid = session.get("room")
		if not rid:
			continue
		if rid not in by_id:
			by_id[rid] = {
				"name": rid,
				"room_name": session.get("room_name") or rid,
				"room_number": "",
				"seating_capacity": 0,
				"week_sessions": 0,
				"week_hours": 0,
				"week_groups": 0,
				"_groups": set(),
			}
		rec = by_id[rid]
		rec["week_sessions"] += 1
		rec["week_hours"] += session.get("hours") or 0
		if session.get("student_group"):
			rec["_groups"].add(session["student_group"])
	cards = []
	for rec in by_id.values():
		groups = rec.pop("_groups")
		rec["week_groups"] = len(groups)
		rec["week_hours"] = round(rec["week_hours"], 1)
		cards.append(rec)
	cards.sort(key=lambda row: (-row["week_sessions"], (row["room_name"] or "").lower()))
	return cards


def _group_cards(sessions):
	by_id = {}
	for session in sessions:
		group = session.get("student_group")
		if not group:
			continue
		if group not in by_id:
			by_id[group] = {
				"student_group": group,
				"student_group_name": session.get("student_group_name"),
				"course": session.get("course"),
				"customer_company": session.get("customer_company"),
				"instructor": session.get("instructor"),
				"instructor_name": session.get("instructor_name"),
				"room": session.get("room"),
				"room_name": session.get("room_name"),
				"student_count": cint(session.get("student_count")),
				"booked": cint(session.get("booked") or session.get("student_count")),
				"max_strength": cint(session.get("max_strength")),
				"remaining": session.get("remaining"),
				"overbooked": cint(session.get("overbooked")),
				"invited": cint(session.get("invited") or session.get("booked") or session.get("student_count")),
				"came": cint(session.get("came")),
				"absent": cint(session.get("absent")),
				"no_show": cint(session.get("no_show")),
				"attendance_marked": bool(session.get("attendance_marked")),
				"week_sessions": 0,
				"week_hours": 0,
				"sessions": [],
			}
		rec = by_id[group]
		rec["week_sessions"] += 1
		rec["week_hours"] += session.get("hours") or 0
		rec["came"] = max(cint(rec.get("came")), cint(session.get("came")))
		rec["attendance_marked"] = rec.get("attendance_marked") or bool(session.get("attendance_marked"))
		if rec.get("attendance_marked"):
			rec["no_show"] = max(cint(rec.get("invited")) - cint(rec.get("came")), 0)
		rec["sessions"].append(
			{
				"name": session.get("name"),
				"date": session.get("date"),
				"time_start": session.get("time_start"),
				"time_end": session.get("time_end"),
				"instructor_name": session.get("instructor_name"),
				"room_name": session.get("room_name"),
			}
		)
	cards = list(by_id.values())
	for rec in cards:
		rec["week_hours"] = round(rec["week_hours"], 1)
	cards.sort(key=lambda row: ((row["sessions"][0]["date"] if row["sessions"] else ""), row["student_group"]))
	return cards


def _group_students(student_group, date=None, course_schedule=None):
	if not student_group:
		return []
	rows = frappe.db.sql(
		"""
		select
			sgs.student,
			sgs.student_name,
			sgs.group_roll_number,
			sgs.customer_name,
			sgs.custom_course_name as course_name,
			sgs.custom_start_date as start_date,
			sgs.custom_end_date as end_date,
			ifnull(s.custom_customer_purchase_order, sgs.customer_purchase_order) as po_number,
			ifnull(s.custom_student_company_name, sgs.customer_name) as company
		from `tabStudent Group Student` sgs
		left join `tabStudent` s on s.name = sgs.student
		where sgs.parent = %(student_group)s
		order by sgs.idx asc
		""",
		{"student_group": student_group},
		as_dict=True,
	)
	if not rows or (not date and not course_schedule):
		for row in rows:
			row["attendance"] = ""
			row["came"] = 0
			row["start_date"] = _fmt_day(row.get("start_date"))
			row["end_date"] = _fmt_day(row.get("end_date"))
			row["po_number"] = row.get("po_number") or ""
		return rows
	conditions = ["ifnull(docstatus, 0) < 2", "student_group = %(student_group)s"]
	values = {"student_group": student_group}
	if course_schedule:
		conditions.append("course_schedule = %(course_schedule)s")
		values["course_schedule"] = course_schedule
	else:
		conditions.append("date = %(date)s")
		values["date"] = date
	att_rows = frappe.db.sql(
		f"""
		select student, status
		from `tabStudent Attendance`
		where {" and ".join(conditions)}
		""",
		values,
		as_dict=True,
	)
	status_map = {row.student: row.status for row in att_rows}
	for row in rows:
		row["attendance"] = status_map.get(row.student) or ""
		row["came"] = 1 if (row["attendance"] or "").lower() == "present" else 0
		row["start_date"] = _fmt_day(row.get("start_date"))
		row["end_date"] = _fmt_day(row.get("end_date"))
		row["po_number"] = row.get("po_number") or ""
	return rows


@frappe.whitelist()
def get_session_detail(name):
	_require_view()
	if not name:
		frappe.throw(_("Session is required."))
	row = frappe.db.sql(
		"""
		select
			cs.name, cs.schedule_date, cs.from_time, cs.to_time,
			cs.instructor, cs.instructor_name, cs.room, cs.course,
			cs.student_group, cs.color,
			sg.student_group_name, sg.custom_customer,
			c.customer_name,
			r.room_name, r.room_number,
			co.course_name
		from `tabCourse Schedule` cs
		left join `tabStudent Group` sg on sg.name = cs.student_group
		left join `tabCustomer` c on c.name = sg.custom_customer
		left join `tabRoom` r on r.name = cs.room
		left join `tabCourse` co on co.name = cs.course
		where cs.name = %(name)s
		""",
		{"name": name},
		as_dict=True,
	)
	if not row:
		frappe.throw(_("Course Schedule {0} not found.").format(name))
	session = _serialize_session(row[0])
	students = _group_students(session.get("student_group"), date=session.get("date"), course_schedule=session.get("name"))
	candidates = _group_candidates(session.get("student_group"), date=session.get("date"), course_schedule=session.get("name"))
	people = _merge_people(students, candidates, student_group=session.get("student_group"))
	session["student_count"] = len(students)
	_attach_capacity([session])
	_apply_candidate_invite_counts([session])
	_attach_attendance([session])
	return {"session": session, "students": students, "candidates": candidates, "people": people}


@frappe.whitelist()
def get_week_students(week_start=None, instructor=None, student_group=None, search=None, search_by=None, days=7):
	_require_view()
	payload = get_week(week_start=week_start, days=days)
	sessions = payload.get("sessions") or []
	if instructor:
		sessions = [row for row in sessions if row.get("instructor") == instructor]
	if student_group:
		sessions = [row for row in sessions if row.get("student_group") == student_group]
	if search:
		needle = (search or "").strip().lower()
		sessions = [
			row
			for row in sessions
			if _session_matches_search(row, needle, search_by)
		]
	groups = []
	seen = {}
	for session in sessions:
		group = session.get("student_group")
		if not group:
			continue
		if group not in seen:
			seen[group] = {
				"student_group": group,
				"student_group_name": session.get("student_group_name"),
				"course": session.get("course"),
				"customer_company": session.get("customer_company"),
				"instructor_name": session.get("instructor_name"),
				"room_name": session.get("room_name"),
				"date": session.get("date"),
				"time_start": session.get("time_start"),
				"time_end": session.get("time_end"),
				"sessions": [],
				"students": _group_students(group, date=session.get("date")),
				"candidates": _group_candidates(group, date=session.get("date"), course_schedule=session.get("name")),
				"booked": session.get("booked"),
				"invited": session.get("invited") or session.get("booked"),
				"came": session.get("came"),
				"absent": session.get("absent"),
				"no_show": session.get("no_show"),
				"attendance_marked": session.get("attendance_marked"),
				"max_strength": session.get("max_strength"),
				"remaining": session.get("remaining"),
				"overbooked": session.get("overbooked"),
			}
			groups.append(seen[group])
			seen[group]["people"] = _merge_people(
				seen[group]["students"], seen[group]["candidates"], student_group=group
			)
		seen[group]["came"] = max(cint(seen[group].get("came")), cint(session.get("came")))
		seen[group]["attendance_marked"] = seen[group].get("attendance_marked") or session.get("attendance_marked")
		seen[group]["sessions"].append(
			{
				"name": session.get("name"),
				"date": session.get("date"),
				"period": session.get("period"),
				"period_label": session.get("period_label"),
				"instructor_name": session.get("instructor_name"),
				"room_name": session.get("room_name"),
				"course": session.get("course"),
				"course_name": session.get("course_name"),
			}
		)
	return {
		"week_start": payload.get("week_start"),
		"week_end": payload.get("week_end"),
		"groups": groups,
		"student_total": sum(len(g.get("people") or g.get("students") or []) for g in groups),
	}


def _fmt_day(value):
	if not value:
		return ""
	try:
		return str(getdate(value))
	except Exception:
		return str(value)[:10]


def _candidate_table_exists():
	return bool(frappe.db.exists("DocType", "Training Candidate"))


def _split_person_name(full_name):
	parts = [part for part in (full_name or "").strip().split() if part]
	if not parts:
		frappe.throw(_("Candidate name is required."))
	return parts[0], " ".join(parts[1:])


def _session_matches_search(row, needle, search_by=None):
	if not needle:
		return True
	search_by = (search_by or "").strip().lower()
	if search_by in ("candidate", "candidate_name"):
		blob = " ".join(
			[
				row.get("people_names") or "",
				row.get("student_group_name") or "",
			]
		)
	elif search_by in ("customer", "customer_name"):
		blob = " ".join(
			[
				row.get("customer_company") or "",
				row.get("customer") or "",
			]
		)
	elif search_by in ("course", "course_name"):
		blob = " ".join(
			[
				row.get("course") or "",
				row.get("course_name") or "",
				row.get("student_group_name") or "",
			]
		)
	else:
		blob = " ".join(
			[
				row.get("people_names") or "",
				row.get("instructor_name") or "",
				row.get("course") or "",
				row.get("student_group") or "",
				row.get("student_group_name") or "",
				row.get("customer_company") or "",
				row.get("room_name") or "",
			]
		)
	return needle in blob.lower()


def _open_candidate_counts(groups):
	if not groups or not _candidate_table_exists():
		return {}
	rows = frappe.db.sql(
		"""
		select student_group, count(*) as cnt
		from `tabTraining Candidate`
		where student_group in %(groups)s
		  and ifnull(student, '') = ''
		group by student_group
		""",
		{"groups": groups},
		as_dict=True,
	)
	return {row.student_group: cint(row.cnt) for row in rows}


def _apply_candidate_invite_counts(sessions):
	groups = list({row.get("student_group") for row in sessions if row.get("student_group")})
	counts = _open_candidate_counts(groups)
	schedule_counts = {}
	if _candidate_table_exists():
		names = [row.get("name") for row in sessions if row.get("name") and not row.get("student_group")]
		if names:
			rows = frappe.db.sql(
				"""
				select course_schedule, count(*) as cnt
				from `tabTraining Candidate`
				where course_schedule in %(names)s
				  and ifnull(student, '') = ''
				group by course_schedule
				""",
				{"names": names},
				as_dict=True,
			)
			schedule_counts = {row.course_schedule: cint(row.cnt) for row in rows}
	for session in sessions:
		extra = cint(counts.get(session.get("student_group")))
		if not session.get("student_group"):
			extra = cint(schedule_counts.get(session.get("name")))
		session["open_candidates"] = extra
		invited = cint(session.get("booked") or session.get("student_count")) + extra
		session["invited"] = invited
		max_strength = cint(session.get("max_strength"))
		if max_strength:
			remaining = max_strength - invited
			session["overbooked"] = abs(remaining) if remaining < 0 else 0
			session["remaining"] = max(remaining, 0)
		else:
			session["remaining"] = None
			session["overbooked"] = 0


def _attach_people_search(sessions):
	groups = list({row.get("student_group") for row in sessions if row.get("student_group")})
	names = {}
	if groups:
		rows = frappe.db.sql(
			"""
			select parent, group_concat(student_name separator ', ') as names
			from `tabStudent Group Student`
			where parent in %(groups)s
			group by parent
			""",
			{"groups": groups},
			as_dict=True,
		)
		names = {row.parent: row.names or "" for row in rows}
	if groups and _candidate_table_exists():
		rows = frappe.db.sql(
			"""
			select student_group, group_concat(candidate_name separator ', ') as names
			from `tabTraining Candidate`
			where student_group in %(groups)s
			group by student_group
			""",
			{"groups": groups},
			as_dict=True,
		)
		for row in rows:
			current = names.get(row.student_group) or ""
			extra = row.names or ""
			names[row.student_group] = ", ".join([part for part in [current, extra] if part])
	for session in sessions:
		session["people_names"] = names.get(session.get("student_group")) or ""


def _group_candidates(student_group, date=None, course_schedule=None):
	if not _candidate_table_exists():
		return []
	if not student_group and not course_schedule:
		return []
	conditions = []
	values = {}
	if student_group:
		conditions.append("student_group = %(student_group)s")
		values["student_group"] = student_group
		if course_schedule:
			conditions.append("(ifnull(course_schedule, '') = '' or course_schedule = %(course_schedule)s)")
			values["course_schedule"] = course_schedule
	else:
		conditions.append("course_schedule = %(course_schedule)s")
		values["course_schedule"] = course_schedule
	if date:
		conditions.append("(date is null or date = %(date)s)")
		values["date"] = date
	lunch_select = ""
	if frappe.db.has_column("Training Candidate", "lunch"):
		lunch_select = ", lunch"
	rows = frappe.db.sql(
		f"""
		select
			name, candidate_name, po_number, customer, customer_name,
			date, student_group, course, course_schedule, student, status
			{lunch_select}
		from `tabTraining Candidate`
		where {" and ".join(conditions)}
		order by creation asc
		""",
		values,
		as_dict=True,
	)
	for row in rows:
		row["date"] = _fmt_day(row.get("date"))
		row["start_date"] = row["date"]
		row["end_date"] = row["date"]
		row["company"] = row.get("customer_name") or row.get("customer") or ""
		row["po_number"] = row.get("po_number") or ""
		row["lunch"] = row.get("lunch") or "No"
	return rows


def _merge_people(students, candidates, student_group=None):
	people = []
	linked = {row.get("student") for row in (students or []) if row.get("student")}
	for idx, row in enumerate(students or []):
		people.append(
			{
				"kind": "student",
				"name": row.get("student"),
				"student": row.get("student"),
				"candidate": "",
				"candidate_name": row.get("student_name"),
				"po_number": row.get("po_number") or "",
				"company": row.get("company") or row.get("customer_name") or "",
				"attendance": row.get("attendance") or "",
				"start_date": row.get("start_date") or "",
				"end_date": row.get("end_date") or "",
				"group_roll_number": row.get("group_roll_number") or (idx + 1),
				"student_group": student_group or row.get("student_group") or "",
				"can_create_student": 0,
				"lunch": row.get("lunch") or "No",
			}
		)
	for row in candidates or []:
		if row.get("student") and row.get("student") in linked:
			continue
		people.append(
			{
				"kind": "candidate",
				"name": row.get("name"),
				"student": row.get("student") or "",
				"candidate": row.get("name"),
				"candidate_name": row.get("candidate_name"),
				"po_number": row.get("po_number") or "",
				"customer": row.get("customer") or "",
				"company": row.get("company") or row.get("customer_name") or "",
				"attendance": "",
				"start_date": row.get("date") or "",
				"end_date": row.get("date") or "",
				"group_roll_number": len(people) + 1,
				"student_group": student_group or row.get("student_group") or "",
				"can_create_student": 0 if row.get("student") else 1,
				"lunch": row.get("lunch") or "No",
			}
		)
	return people


def _resolve_customer(customer=None, customer_name=None):
	customer = (customer or "").strip()
	customer_name = (customer_name or "").strip()
	if customer and frappe.db.exists("Customer", customer):
		return customer, frappe.db.get_value("Customer", customer, "customer_name") or customer_name or customer
	if customer_name:
		found = frappe.db.get_value("Customer", {"customer_name": customer_name}, "name")
		if found:
			return found, customer_name
		found = frappe.db.get_value("Customer", customer_name, "name")
		if found:
			return found, frappe.db.get_value("Customer", found, "customer_name") or customer_name
	return "", customer_name


def _ensure_customer(customer=None, customer_name=None):
	customer, customer_name = _resolve_customer(customer, customer_name)
	if customer:
		return customer, customer_name
	if not customer_name:
		frappe.throw(_("Customer name is required to create a Student."))
	doc = frappe.new_doc("Customer")
	doc.customer_name = customer_name
	doc.customer_type = "Company"
	selling = frappe.get_single("Selling Settings")
	if getattr(selling, "customer_group", None):
		doc.customer_group = selling.customer_group
	if getattr(selling, "territory", None):
		doc.territory = selling.territory
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name, customer_name


def _lunch_value(value):
	text = str(value or "").strip().lower()
	if text in ("1", "yes", "y", "true"):
		return "Yes"
	return "No"


def _candidate_names_from_payload(payload):
	chunks = []
	if payload.get("candidate_names"):
		chunks.append(payload.get("candidate_names"))
	if payload.get("candidate_name"):
		chunks.append(payload.get("candidate_name"))
	names = []
	seen = set()
	for chunk in chunks:
		items = chunk if isinstance(chunk, (list, tuple)) else [chunk]
		for item in items:
			for part in str(item or "").replace(";", "\n").splitlines():
				name = part.strip()
				key = name.lower()
				if name and key not in seen:
					seen.add(key)
					names.append(name)
	return names


def _insert_candidate(payload, candidate_name):
	student_group = (payload.get("student_group") or "").strip()
	course_schedule = (payload.get("course_schedule") or "").strip()
	if not student_group and not course_schedule:
		frappe.throw(_("Save the session first, then add the candidate."))
	schedule_date = payload.get("date") or today()
	customer, customer_name = _resolve_customer(payload.get("customer"), payload.get("customer_name"))
	doc = frappe.new_doc("Training Candidate")
	doc.candidate_name = candidate_name
	doc.po_number = (payload.get("po_number") or "").strip()
	doc.customer = customer
	doc.customer_name = customer_name
	doc.date = getdate(schedule_date)
	doc.student_group = student_group or None
	doc.course = payload.get("course") or (
		frappe.db.get_value("Student Group", student_group, "course") if student_group else ""
	)
	doc.course_schedule = course_schedule
	doc.status = "Invited"
	if frappe.get_meta("Training Candidate").has_field("lunch"):
		doc.lunch = _lunch_value(payload.get("lunch"))
	doc.flags.ignore_permissions = True
	doc.flags.ignore_mandatory = True
	doc.insert()
	if payload.get("create_student"):
		return create_student_from_candidate(doc.name)
	return {"name": doc.name, "candidate": _candidate_payload(doc)}


@frappe.whitelist()
def add_candidate(data):
	_require_manage()
	if not _candidate_table_exists():
		frappe.throw(_("Training Candidate is not installed yet. Please migrate the Numerouno app."))
	payload = frappe.parse_json(data) if isinstance(data, str) else (data or {})
	names = _candidate_names_from_payload(payload)
	if not names:
		frappe.throw(_("Candidate name is required."))
	created = [_insert_candidate(payload, name) for name in names]
	if len(created) == 1:
		return created[0]
	return {"count": len(created), "candidates": created}


def _candidate_payload(doc):
	return {
		"name": doc.name,
		"candidate_name": doc.candidate_name,
		"po_number": doc.po_number,
		"customer": doc.customer,
		"customer_name": doc.customer_name,
		"date": str(doc.date) if doc.date else "",
		"student_group": doc.student_group,
		"course": doc.course,
		"course_schedule": doc.course_schedule,
		"student": doc.student,
		"status": doc.status,
		"lunch": getattr(doc, "lunch", None) or "No",
	}


@frappe.whitelist()
def create_student_from_candidate(name):
	_require_manage()
	if not name:
		frappe.throw(_("Candidate is required."))
	doc = frappe.get_doc("Training Candidate", name)
	if doc.student:
		return {"name": doc.name, "student": doc.student, "candidate": _candidate_payload(doc)}
	if not (doc.candidate_name or "").strip():
		frappe.throw(_("Candidate name is required."))

	customer, customer_name = _resolve_customer(doc.customer, doc.customer_name)
	doc.customer = customer or None
	doc.customer_name = customer_name

	first_name, last_name = _split_person_name(doc.candidate_name)
	student = frappe.new_doc("Student")
	student.first_name = first_name
	if last_name:
		student.last_name = last_name
	student.naming_series = "EDU-STU-.YYYY.-"
	student.joining_date = doc.date or today()
	if customer:
		student.customer_name = customer
	if frappe.get_meta("Student").has_field("custom_contact_type"):
		student.custom_contact_type = "Without Email"
	if frappe.get_meta("Student").has_field("custom_mode_of_payment"):
		student.custom_mode_of_payment = "Purchase Order" if (doc.po_number or "").strip() else "Cash"
	if frappe.get_meta("Student").has_field("custom_customer_purchase_order"):
		student.custom_customer_purchase_order = doc.po_number
	if frappe.get_meta("Student").has_field("custom_student_company_name"):
		student.custom_student_company_name = customer_name
	student.flags.ignore_permissions = True
	student.flags.ignore_mandatory = True
	student.insert()

	doc.student = student.name
	doc.status = "Student Created"
	doc.flags.ignore_permissions = True
	doc.save()
	return {"name": doc.name, "student": student.name, "candidate": _candidate_payload(doc)}


@frappe.whitelist()
def update_po_number(candidate=None, student=None, student_group=None, po_number=None):
	"""Update PO on a Training Candidate and/or linked Student without resaving the group."""
	_require_manage()
	po_number = (po_number or "").strip()
	candidate = (candidate or "").strip()
	student = (student or "").strip()
	student_group = (student_group or "").strip()
	if not candidate and not student:
		frappe.throw(_("Select a candidate or student."))

	if candidate:
		if not frappe.db.exists("Training Candidate", candidate):
			frappe.throw(_("Candidate not found."))
		frappe.db.set_value("Training Candidate", candidate, "po_number", po_number)
		linked = frappe.db.get_value("Training Candidate", candidate, ["student", "student_group"])
		if linked:
			student = student or (linked[0] or "")
			student_group = student_group or (linked[1] or "")

	if student:
		if frappe.db.exists("Student", student) and frappe.get_meta("Student").has_field(
			"custom_customer_purchase_order"
		):
			frappe.db.set_value("Student", student, "custom_customer_purchase_order", po_number)
		if student_group and frappe.get_meta("Student Group Student").has_field("customer_purchase_order"):
			row_name = frappe.db.get_value(
				"Student Group Student",
				{"parent": student_group, "student": student},
				"name",
			)
			if row_name:
				frappe.db.set_value("Student Group Student", row_name, "customer_purchase_order", po_number)
		if _candidate_table_exists():
			for name in frappe.get_all("Training Candidate", filters={"student": student}, pluck="name"):
				frappe.db.set_value("Training Candidate", name, "po_number", po_number)

	return {"ok": 1, "po_number": po_number}


def _csv_header_key(header):
	return "".join(ch for ch in (header or "").lower() if ch.isalnum())


def _parse_candidate_csv(content):
	if content is None:
		return []
	if isinstance(content, bytes):
		content = content.decode("utf-8-sig")
	text = str(content).replace("\ufeff", "").strip()
	if not text:
		return []
	reader = csv.DictReader(io.StringIO(text))
	key_map = {
		"candidatename": "candidate_name",
		"name": "candidate_name",
		"candidate": "candidate_name",
		"fullname": "candidate_name",
		"ponumber": "po_number",
		"po": "po_number",
		"customerponumber": "po_number",
		"customer": "customer_name",
		"customername": "customer_name",
		"company": "customer_name",
		"companyname": "customer_name",
		"lunch": "lunch",
	}
	rows = []
	for raw in reader:
		mapped = {}
		for header, value in (raw or {}).items():
			field = key_map.get(_csv_header_key(header))
			if field:
				mapped[field] = (value or "").strip()
		name = mapped.get("candidate_name") or ""
		if not name:
			continue
		mapped["lunch"] = _lunch_value(mapped.get("lunch"))
		rows.append(mapped)
	return rows


@frappe.whitelist()
def update_candidate(data):
	_require_manage()
	if not _candidate_table_exists():
		frappe.throw(_("Training Candidate is not installed yet. Please migrate the Numerouno app."))
	payload = frappe.parse_json(data) if isinstance(data, str) else (data or {})
	name = (payload.get("name") or payload.get("candidate") or "").strip()
	if not name:
		frappe.throw(_("Candidate is required."))
	doc = frappe.get_doc("Training Candidate", name)
	names = _candidate_names_from_payload(payload)
	if names:
		doc.candidate_name = names[0]
	if "po_number" in payload:
		doc.po_number = (payload.get("po_number") or "").strip()
	if payload.get("date"):
		doc.date = getdate(payload.get("date"))
	customer, customer_name = _resolve_customer(payload.get("customer"), payload.get("customer_name"))
	if customer or customer_name:
		doc.customer = customer or doc.customer
		doc.customer_name = customer_name or doc.customer_name
	if frappe.get_meta("Training Candidate").has_field("lunch") and payload.get("lunch") is not None:
		doc.lunch = _lunch_value(payload.get("lunch"))
	doc.flags.ignore_permissions = True
	doc.save()
	return {"name": doc.name, "candidate": _candidate_payload(doc)}


@frappe.whitelist()
def delete_candidate(name):
	_require_manage()
	name = (name or "").strip()
	if not name:
		frappe.throw(_("Candidate is required."))
	if not frappe.db.exists("Training Candidate", name):
		frappe.throw(_("Candidate {0} not found.").format(name))
	frappe.delete_doc("Training Candidate", name, ignore_permissions=True)
	return {"ok": 1, "name": name}


@frappe.whitelist()
def import_candidates_csv(data):
	_require_manage()
	if not _candidate_table_exists():
		frappe.throw(_("Training Candidate is not installed yet. Please migrate the Numerouno app."))
	payload = frappe.parse_json(data) if isinstance(data, str) else (data or {})
	rows = _parse_candidate_csv(payload.get("csv_content") or payload.get("csv"))
	if not rows:
		frappe.throw(_("No candidates found in the CSV. Use columns: Candidate Name, PO Number, Customer, Lunch."))
	created = []
	for row in rows:
		row_payload = {
			"student_group": payload.get("student_group"),
			"course_schedule": payload.get("course_schedule"),
			"course": payload.get("course"),
			"date": payload.get("date"),
			"po_number": row.get("po_number") or payload.get("po_number"),
			"customer": row.get("customer") or payload.get("customer"),
			"customer_name": row.get("customer_name") or payload.get("customer_name"),
			"lunch": row.get("lunch") or payload.get("lunch"),
		}
		created.append(_insert_candidate(row_payload, row["candidate_name"]))
	return {"count": len(created), "candidates": created}

