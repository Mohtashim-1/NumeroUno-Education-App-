import frappe

from numerouno.numerouno.utils.signatures import (
	get_instructor_signature,
	is_empty_signature,
	resolve_signature_url,
)


def get_attendance_sheet_print_data(student_group):
	"""Batch-load attendance print data for one Student Group (used from print Jinja)."""
	student_group = (student_group or "").strip()
	if not student_group:
		return _empty_payload()

	sg = frappe.get_cached_doc("Student Group", student_group)
	student_ids = [row.student for row in (sg.students or []) if row.student]
	if not student_ids:
		return _empty_payload()

	student_rows = frappe.get_all(
		"Student",
		filters={"name": ["in", student_ids]},
		fields=[
			"name",
			"custom_customer_purchase_order",
			"custom_secondary_customer",
			"nationality",
			"date_of_birth",
		],
	)
	students = {row.name: row for row in student_rows}

	attendance_date = frappe.db.get_value(
		"Student Attendance",
		{"student_group": student_group, "docstatus": 1},
		"date",
		order_by="date asc",
	)

	attendance = {}
	for row in frappe.get_all(
		"Student Attendance",
		filters={
			"student_group": student_group,
			"student": ["in", student_ids],
			"docstatus": 1,
		},
		fields=["student", "date", "custom_student_signature", "custom_student_signature1"],
	):
		attendance[_attendance_key(row.student, row.date)] = row

	cards = {}
	for row in frappe.get_all(
		"Student Card",
		filters={
			"student_group": student_group,
			"student": ["in", student_ids],
			"docstatus": 1,
		},
		fields=["student", "student_signature"],
	):
		if row.student and row.student_signature:
			cards[row.student] = row.student_signature

	instructor_signature_url = ""
	if sg.instructors and sg.instructors[0].instructor:
		instructor_signature_url = _instructor_signature_url(sg.instructors[0].instructor)

	return frappe._dict(
		students=students,
		attendance=attendance,
		cards=cards,
		attendance_date=attendance_date,
		instructor_signature_url=instructor_signature_url,
	)


def _attendance_key(student, date):
	return f"{student}|{frappe.utils.formatdate(date, 'yyyy-mm-dd')}"


def _instructor_signature_url(instructor):
	image = get_instructor_signature(instructor)
	if not image:
		photo = (frappe.db.get_value("Instructor", instructor, "photo") or "").strip()
		if photo and not is_empty_signature(photo):
			image = photo
	return resolve_signature_url(image) if image else ""


def _empty_payload():
	return frappe._dict(
		students={},
		attendance={},
		cards={},
		attendance_date=None,
		instructor_signature_url="",
	)
