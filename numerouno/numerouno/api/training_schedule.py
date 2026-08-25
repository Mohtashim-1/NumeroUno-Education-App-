from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import add_days, cint, format_date, getdate, now_datetime, today


MANAGE_ROLES = {
	"System Manager",
	"Academics User",
	"Education Manager",
	"Instructor",
	"Trainer",
	"Academic User",
}

DEFAULT_SLOTS = [
	("08:00:00", "10:00:00"),
	("10:15:00", "12:15:00"),
	("12:30:00", "14:30:00"),
	("14:45:00", "16:45:00"),
]

COURSE_COLORS = [
	{"key": "leadership", "label": "Leadership", "tone": "blue"},
	{"key": "communication", "label": "Communication", "tone": "green"},
	{"key": "technical", "label": "Technical", "tone": "purple"},
	{"key": "management", "label": "Management", "tone": "yellow"},
	{"key": "marketing", "label": "Marketing", "tone": "pink"},
	{"key": "sales", "label": "Sales", "tone": "teal"},
	{"key": "other", "label": "Other", "tone": "grey"},
]


def _can_view():
	if frappe.session.user == "Guest":
		return False
	return True


def _can_manage():
	if frappe.session.user == "Administrator":
		return True
	return bool(set(frappe.get_roles()) & MANAGE_ROLES)


def _require_view():
	if not _can_view():
		frappe.throw(_("Please log in to open the Training Schedule."), frappe.PermissionError)


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


def _room_label(room, room_name=None, room_number=None):
	return room_name or room_number or room or ""


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
	return {
		"name": row.name,
		"date": str(row.schedule_date),
		"time_start": _fmt_time(row.from_time),
		"time_end": _fmt_time(row.to_time),
		"from_time": _fmt_time(row.from_time),
		"to_time": _fmt_time(row.to_time),
		"hours": _time_hours(row.from_time, row.to_time),
		"instructor": row.instructor,
		"instructor_name": row.instructor_name or row.instructor,
		"instructor_image": "",
		"room": row.room,
		"room_name": _room_label(row.room, row.room_name, row.room_number),
		"student_group": row.student_group,
		"student_group_name": row.student_group_name or row.student_group,
		"course": row.course,
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
		"slots": [{"from_time": a[:5], "to_time": b[:5]} for a, b in DEFAULT_SLOTS],
		"categories": COURSE_COLORS,
	}


@frappe.whitelist()
def get_week(week_start=None, instructor=None, student_group=None, status=None, search=None):
	_require_view()
	monday, sunday = _week_bounds(week_start)
	rows = frappe.db.sql(
		"""
		select
			cs.name, cs.schedule_date, cs.from_time, cs.to_time,
			cs.instructor, cs.instructor_name, cs.room, cs.course,
			cs.student_group, cs.color,
			sg.student_group_name, sg.custom_customer,
			c.customer_name,
			r.room_name, r.room_number
		from `tabCourse Schedule` cs
		left join `tabStudent Group` sg on sg.name = cs.student_group
		left join `tabCustomer` c on c.name = sg.custom_customer
		left join `tabRoom` r on r.name = cs.room
		where cs.docstatus < 2
		  and cs.schedule_date between %(start)s and %(end)s
		order by cs.schedule_date asc, cs.from_time asc
		""",
		{"start": monday, "end": sunday},
		as_dict=True,
	)

	sessions = [_serialize_session(row) for row in rows]
	_attach_student_counts(sessions)
	_attach_capacity(sessions)
	_attach_attendance(sessions)

	days = []
	for offset in range(7):
		day = add_days(monday, offset)
		days.append(
			{
				"date": str(day),
				"label": format_date(day, "ddd"),
				"day_num": day.day,
				"is_today": str(day) == today(),
			}
		)

	slot_keys = {(_fmt_time(a), _fmt_time(b)) for a, b in DEFAULT_SLOTS}
	for row in sessions:
		slot_keys.add((row["time_start"], row["time_end"]))
	slots = sorted(slot_keys, key=lambda item: item[0] or "99:99")
	slot_rows = [{"from_time": a, "to_time": b, "label": f"{a} - {b}"} for a, b in slots]

	trainers = _trainer_cards(sessions)
	rooms = _room_cards(sessions)
	groups = _group_cards(sessions)
	used_rooms = {row["room"] for row in sessions if row.get("room")}
	student_total = sum(cint(g.get("student_count")) for g in groups)

	return {
		"week_start": str(monday),
		"week_end": str(sunday),
		"days": days,
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
			"came": _unique_came([g.get("student_group") for g in groups], monday, sunday),
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
	from_time = _as_sql_time(payload.get("from_time") or payload.get("time_start"))
	to_time = _as_sql_time(payload.get("to_time") or payload.get("time_end"))
	room = (payload.get("room") or "").strip()
	course = (payload.get("course") or "").strip()
	name = (payload.get("name") or "").strip()

	if not student_group:
		frappe.throw(_("Student Group is required."))
	if not instructor:
		frappe.throw(_("Instructor is required."))
	if not schedule_date:
		frappe.throw(_("Date is required."))
	if not room:
		defaults = get_student_group_defaults(student_group)
		room = defaults.get("room") or ""
	if not room:
		frappe.throw(_("Room is required."))
	if not course:
		course = frappe.db.get_value("Student Group", student_group, "course")
	if not course:
		frappe.throw(_("Course is missing on the Student Group."))

	if name:
		doc = frappe.get_doc("Course Schedule", name)
	else:
		doc = frappe.new_doc("Course Schedule")

	doc.student_group = student_group
	doc.instructor = instructor
	doc.schedule_date = getdate(schedule_date)
	doc.from_time = from_time
	doc.to_time = to_time
	doc.room = room
	doc.course = course
	doc.flags.ignore_permissions = True
	doc.save()
	if payload.get("max_strength") not in (None, ""):
		_set_group_max_strength(student_group, payload.get("max_strength"))
	return {"name": doc.name}


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
			r.room_name, r.room_number
		from `tabCourse Schedule` cs
		left join `tabStudent Group` sg on sg.name = cs.student_group
		left join `tabCustomer` c on c.name = sg.custom_customer
		left join `tabRoom` r on r.name = cs.room
		where cs.name = %(name)s
		""",
		{"name": name},
		as_dict=True,
	)
	if not row:
		frappe.throw(_("Course Schedule {0} not found.").format(name))
	session = _serialize_session(row[0])
	students = _group_students(session.get("student_group"), date=session.get("date"), course_schedule=session.get("name"))
	session["student_count"] = len(students)
	_attach_capacity([session])
	_attach_attendance([session])
	return {"session": session, "students": students}


@frappe.whitelist()
def get_week_students(week_start=None, instructor=None, student_group=None, search=None):
	_require_view()
	payload = get_week(week_start=week_start)
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
			if needle in " ".join(
				[
					row.get("instructor_name") or "",
					row.get("course") or "",
					row.get("student_group") or "",
					row.get("student_group_name") or "",
					row.get("customer_company") or "",
					row.get("room_name") or "",
				]
			).lower()
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
		seen[group]["came"] = max(cint(seen[group].get("came")), cint(session.get("came")))
		seen[group]["attendance_marked"] = seen[group].get("attendance_marked") or session.get("attendance_marked")
		seen[group]["sessions"].append(
			{
				"name": session.get("name"),
				"date": session.get("date"),
				"time_start": session.get("time_start"),
				"time_end": session.get("time_end"),
				"instructor_name": session.get("instructor_name"),
				"room_name": session.get("room_name"),
				"course": session.get("course"),
			}
		)
	return {
		"week_start": payload.get("week_start"),
		"week_end": payload.get("week_end"),
		"groups": groups,
		"student_total": sum(len(g["students"]) for g in groups),
	}
