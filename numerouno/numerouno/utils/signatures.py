import frappe

SIGNATURE_PLACEHOLDER = "/assets/frappe/images/signature-placeholder.png"


def is_empty_signature(value):
	if not value:
		return True
	return SIGNATURE_PLACEHOLDER in value


def get_instructor_signature(instructor):
	"""Instructor.image is labelled Attach Signature on the Instructor profile."""
	instructor = (instructor or "").strip()
	if not instructor:
		return ""
	image = frappe.db.get_value("Instructor", instructor, "image") or ""
	if is_empty_signature(image):
		return ""
	return image


def resolve_signature_url(value):
	"""Return an absolute URL for signature images in forms and PDF print."""
	url = (value or "").strip()
	if not url or is_empty_signature(url):
		return ""
	if url.startswith(("http://", "https://", "data:")):
		return url
	return frappe.utils.get_url(url)


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

	card_sig = frappe.db.get_value("Student Card", {"student": student}, "student_signature") or ""
	if not is_empty_signature(card_sig):
		return card_sig

	image = frappe.db.get_value("Student", student, "image") or ""
	if not is_empty_signature(image):
		return image
	return ""


def _attendance_signature(student, student_group=None):
	params = [student]
	group_sql = ""
	if student_group:
		group_sql = " and student_group = %s"
		params.append(student_group)

	rows = frappe.db.sql(
		f"""
		select custom_student_signature, custom_student_signature1
		from `tabStudent Attendance`
		where student = %s
		  and docstatus < 2
		  and (
			ifnull(trim(custom_student_signature), '') != ''
			or ifnull(trim(custom_student_signature1), '') != ''
		  )
		  {group_sql}
		order by docstatus desc, date desc, modified desc
		limit 10
		""",
		tuple(params),
	)
	for row in rows or []:
		for value in row:
			sig = (value or "").strip()
			if not is_empty_signature(sig):
				return sig
	return ""
