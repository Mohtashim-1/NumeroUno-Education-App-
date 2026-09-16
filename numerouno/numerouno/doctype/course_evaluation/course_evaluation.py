import frappe
from frappe.model.document import Document
from frappe.utils import today


class CourseEvaluation(Document):
	pass


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


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_trainee_query(doctype, txt, searchfield, start, page_len, filters):
	"""Link query: Students in the selected student group (or all students if no group)."""
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


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_student_group_query(doctype, txt, searchfield, start, page_len, filters):
	"""Link query: Student Groups that include the selected student."""
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


@frappe.whitelist()
def apply_student_group_details(student_group, student=None):
	"""Desk / web form helper: prefill course evaluation from Student Group."""
	if not student_group:
		frappe.throw("Student Group is required")

	sg = frappe.get_doc("Student Group", student_group)

	if student:
		in_group = frappe.db.exists(
			"Student Group Student",
			{"parent": student_group, "student": student},
		)
		if not in_group:
			frappe.throw("Selected student is not in this student group.")

	instructor_name = ""
	if getattr(sg, "instructors", None):
		first_instructor = sg.instructors[0]
		instructor_name = (
			getattr(first_instructor, "instructor", None)
			or getattr(first_instructor, "instructor_name", None)
			or ""
		)

	company = ""
	possible_company = getattr(sg, "custom_customer", None) or getattr(sg, "company", None)
	if possible_company and frappe.db.exists("Company", possible_company):
		company = possible_company
	elif possible_company and frappe.db.exists("Customer", possible_company):
		# Some groups store customer name; keep for display on course_name area if needed
		pass

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
		"course_name": sg.course or "",
		"company": company,
		"instructor_name": instructor_name,
		"dates": str(sg.from_date or today()),
		"trainee_name": student or "",
		"email_id": email_id,
		"trainee_mobile": trainee_mobile,
		"student_group": sg.name,
	}


@frappe.whitelist()
def get_student_groups_for_student(student):
	if not student:
		return []
	return frappe.get_all(
		"Student Group Student",
		filters={"student": student},
		pluck="parent",
		order_by="parent asc",
	)
