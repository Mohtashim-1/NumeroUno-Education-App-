import frappe

SIGNATURE_PLACEHOLDER = "/assets/frappe/images/signature-placeholder.png"


def is_empty_signature(value):
	if not value:
		return True
	return SIGNATURE_PLACEHOLDER in value


def get_student_attendance_signature(student, student_group=None):
	"""Latest Student Attendance signature for this student, preferring the same group."""
	student = (student or "").strip()
	if not student:
		return ""

	student_group = (student_group or "").strip() or None
	if student_group:
		sig = _attendance_signature(student, student_group)
		if sig:
			return sig
	return _attendance_signature(student, None)


def resolve_learner_signature(student, student_group=None, learner_signature=None):
	"""Form field -> Student Attendance -> Student Card."""
	if not is_empty_signature(learner_signature):
		return learner_signature or ""

	student = (student or "").strip()
	if not student:
		return ""

	sig = get_student_attendance_signature(student, student_group)
	if sig:
		return sig

	return frappe.db.get_value("Student Card", {"student": student}, "student_signature") or ""


def _attendance_signature(student, student_group=None):
	params = [student]
	group_sql = ""
	if student_group:
		group_sql = " and student_group = %s"
		params.append(student_group)

	row = frappe.db.sql(
		f"""
		select custom_student_signature, custom_student_signature1
		from `tabStudent Attendance`
		where student = %s
		  and (
			ifnull(custom_student_signature, '') != ''
			or ifnull(custom_student_signature1, '') != ''
		  )
		  {group_sql}
		order by docstatus desc, date desc, modified desc
		limit 1
		""",
		tuple(params),
	)
	if not row:
		return ""
	return (row[0][0] or row[0][1] or "") or ""
