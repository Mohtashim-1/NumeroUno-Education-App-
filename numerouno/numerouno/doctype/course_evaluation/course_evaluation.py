import frappe
from frappe.model.document import Document
from frappe.utils import today


class CourseEvaluation(Document):
	pass


def _can_use_course_evaluation_api():
	"""Allow prefill/link helpers for anyone who can use Course Evaluation (Desk or web form)."""
	if frappe.session.user == "Guest":
		return True
	return frappe.has_permission("Course Evaluation", "create") or frappe.has_permission(
		"Course Evaluation", "write"
	)


def _student_group_db_fields():
	"""Only columns that exist on Student Group (customizations vary by site)."""
	meta = frappe.get_meta("Student Group")
	fields = ["name", "course"]
	for fname in ("from_date", "custom_customer", "company"):
		if meta.has_field(fname):
			fields.append(fname)
	return fields


RATING_FIELDS = (
	"joining_instructions_clear",
	"training_room_environment",
	"administration_support",
	"objectives_clearly_defined",
	"content_organization",
	"materials_aligned",
	"course_pace",
	"presentation_skills",
	"teaching_effectiveness",
	"knowledge_accessibility",
	"assignments_exercises",
	"handouts_tools_equipment",
	"technology_effectiveness",
)


@frappe.whitelist(allow_guest=True)
@frappe.validate_and_sanitize_search_inputs
def get_trainee_query(doctype, txt, searchfield, start, page_len, filters):
	"""Link query: Students in the selected student group (or all students if no group)."""
	if not _can_use_course_evaluation_api():
		frappe.throw(frappe._("Not permitted"), frappe.PermissionError)

	student_group = (filters or {}).get("student_group")
	txt = f"%{txt or ''}%"
	limit = page_len or 20
	offset = start or 0

	if student_group:
		return frappe.db.sql(
			"""
			SELECT sgs.student, IFNULL(st.student_name, sgs.student)
			FROM `tabStudent Group Student` sgs
			LEFT JOIN `tabStudent` st ON st.name = sgs.student
			WHERE sgs.parent = %(student_group)s
			  AND (sgs.student LIKE %(txt)s OR IFNULL(st.student_name, '') LIKE %(txt)s)
			ORDER BY st.student_name ASC, sgs.student ASC
			LIMIT %(limit)s OFFSET %(offset)s
			""",
			{
				"student_group": student_group,
				"txt": txt,
				"limit": limit,
				"offset": offset,
			},
		)

	return frappe.db.sql(
		"""
		SELECT name, student_name
		FROM `tabStudent`
		WHERE name LIKE %(txt)s OR IFNULL(student_name, '') LIKE %(txt)s
		ORDER BY student_name ASC, name ASC
		LIMIT %(limit)s OFFSET %(offset)s
		""",
		{"txt": txt, "limit": limit, "offset": offset},
	)


@frappe.whitelist(allow_guest=True)
@frappe.validate_and_sanitize_search_inputs
def get_student_group_query(doctype, txt, searchfield, start, page_len, filters):
	"""Link query: Student Groups that include the selected student."""
	if not _can_use_course_evaluation_api():
		frappe.throw(frappe._("Not permitted"), frappe.PermissionError)

	student = (filters or {}).get("student")
	txt = f"%{txt or ''}%"
	limit = page_len or 20
	offset = start or 0

	if student:
		return frappe.db.sql(
			"""
			SELECT DISTINCT sg.name, CONCAT(IFNULL(sg.course, ''), ' | ', IFNULL(sg.from_date, ''))
			FROM `tabStudent Group Student` sgs
			INNER JOIN `tabStudent Group` sg ON sg.name = sgs.parent
			WHERE sgs.student = %(student)s
			  AND sg.name LIKE %(txt)s
			ORDER BY sg.from_date DESC, sg.name ASC
			LIMIT %(limit)s OFFSET %(offset)s
			""",
			{"student": student, "txt": txt, "limit": limit, "offset": offset},
		)

	return frappe.db.sql(
		"""
		SELECT name, CONCAT(IFNULL(course, ''), ' | ', IFNULL(from_date, ''))
		FROM `tabStudent Group`
		WHERE name LIKE %(txt)s
		ORDER BY modified DESC
		LIMIT %(limit)s OFFSET %(offset)s
		""",
		{"txt": txt, "limit": limit, "offset": offset},
	)


@frappe.whitelist(allow_guest=True)
def apply_student_group_details(student_group, student=None):
	"""Desk / web form helper: prefill course evaluation from Student Group."""
	if not _can_use_course_evaluation_api():
		frappe.throw(frappe._("Not permitted"), frappe.PermissionError)

	if not student_group:
		frappe.throw("Student Group is required")

	if not frappe.db.exists("Student Group", student_group):
		frappe.throw("Invalid Student Group")

	if student and not frappe.db.exists(
		"Student Group Student",
		{"parent": student_group, "student": student},
	):
		frappe.throw("Selected student is not in this student group.")

	sg = frappe.db.get_value(
		"Student Group",
		student_group,
		_student_group_db_fields(),
		as_dict=True,
	) or {}

	instructor_name = ""
	instructor_row = frappe.db.sql(
		"""
		SELECT instructor, instructor_name
		FROM `tabStudent Group Instructor`
		WHERE parent = %(parent)s
		ORDER BY idx ASC
		LIMIT 1
		""",
		{"parent": student_group},
		as_dict=True,
	)
	if instructor_row:
		instructor_name = (
			instructor_row[0].get("instructor") or instructor_row[0].get("instructor_name") or ""
		)

	company = ""
	for candidate in (sg.get("company"), sg.get("custom_customer")):
		if candidate and frappe.db.exists("Company", candidate):
			company = candidate
			break

	email_id = ""
	trainee_mobile = ""
	if student and frappe.db.exists("Student", student):
		student_row = frappe.db.get_value(
			"Student",
			student,
			["student_email_id", "custom_phone"],
			as_dict=True,
		) or {}
		email_id = student_row.get("student_email_id") or ""
		trainee_mobile = student_row.get("custom_phone") or ""

	return {
		"course_name": sg.get("course") or "",
		"company": company,
		"instructor_name": instructor_name,
		"dates": str(sg.get("from_date") or today()),
		"trainee_name": student or "",
		"email_id": email_id,
		"trainee_mobile": trainee_mobile,
		"student_group": sg.get("name"),
	}


@frappe.whitelist(allow_guest=True)
def get_student_groups_for_student(student):
	if not _can_use_course_evaluation_api():
		frappe.throw(frappe._("Not permitted"), frappe.PermissionError)

	if not student:
		return []
	return frappe.get_all(
		"Student Group Student",
		filters={"student": student},
		pluck="parent",
		order_by="parent asc",
	)
