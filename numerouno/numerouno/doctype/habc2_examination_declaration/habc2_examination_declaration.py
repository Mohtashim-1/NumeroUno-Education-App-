# Copyright (c) 2026, NumeroUNO and contributors

import re

import frappe
from frappe.model.document import Document
from frappe.utils import cint, formatdate, getdate, today


ROWS_PER_PAGE = 20
DEFAULT_CENTRE = "Numero Uno Training and Consulting LLC"
DEFAULT_CENTRE_NO = "12043"


class HABC2ExaminationDeclaration(Document):
	def before_print(self, settings=None):
		self._sync_learner_signatures()
		self.learner_pages = paginate_learners(self.learners)

	def validate(self):
		self._sync_tutor()
		self._sync_learner_signatures()
		self._number_learners()
		self._number_rows()
		if not self.centre_name:
			self.centre_name = DEFAULT_CENTRE
		if not self.centre_number:
			self.centre_number = DEFAULT_CENTRE_NO

	def _sync_tutor(self):
		if not self.nominated_tutor and self.student_group:
			self.nominated_tutor = get_group_instructor(self.student_group)
		if self.nominated_tutor:
			self.nominated_tutor_name = (
				frappe.db.get_value("Instructor", self.nominated_tutor, "instructor_name")
				or self.nominated_tutor_name
			)

	def _number_learners(self):
		filled = [row for row in (self.learners or []) if (row.learner_names or row.learner_surname or row.student)]
		if filled:
			self.number_of_learners = len(filled)

	def _number_rows(self):
		for idx, row in enumerate(self.learners or [], start=1):
			row.sr_no = idx

	def _sync_learner_signatures(self):
		from numerouno.numerouno.utils.signatures import is_empty_signature, resolve_learner_signature

		for row in self.learners or []:
			if not row.student:
				continue
			sig = resolve_learner_signature(row.student, self.student_group, row.signature)
			if sig and is_empty_signature(row.signature):
				row.signature = sig


def get_group_instructor(student_group):
	if not student_group:
		return None
	return frappe.db.get_value(
		"Student Group Instructor",
		{"parent": student_group},
		"instructor",
		order_by="idx asc",
	)


def _strip_name_suffix(value):
	value = (value or "").strip()
	return re.sub(r"\s+-\s+[A-Za-z]{2,}[-0-9A-Za-z]*$", "", value).strip()


def _split_full_name(full):
	parts = [part for part in _strip_name_suffix(full).split() if part]
	if not parts:
		return "", ""
	if len(parts) == 1:
		return parts[0], ""
	return " ".join(parts[:-1]), parts[-1]


def _split_name(student, student_name=""):
	"""Use Student First/Last Name when filled; otherwise split the full name."""
	values = frappe.db.get_value(
		"Student",
		student,
		["first_name", "middle_name", "last_name", "student_name", "custom_full_name_english"],
		as_dict=True,
	) or frappe._dict()
	first = (values.get("first_name") or "").strip()
	middle = (values.get("middle_name") or "").strip()
	last = (values.get("last_name") or "").strip()
	if last:
		given = " ".join(part for part in (first, middle) if part).strip()
		given_u = given.upper()
		last_u = last.upper()
		if given_u.endswith(" " + last_u):
			given = given[: -len(last)].strip()
		return given or first, last

	source = (
		(values.get("custom_full_name_english") or "").strip()
		or (student_name or "").strip()
		or " ".join(part for part in (first, middle) if part).strip()
		or (values.get("student_name") or "").strip()
	)
	return _split_full_name(source)


def _gender_code(value):
	value = (value or "").strip().lower()
	if value in ("m", "male", "man"):
		return "M"
	if value in ("f", "female", "woman"):
		return "F"
	return ""


def _id_type(student):
	eid = frappe.db.get_value("Student", student, "custom_eid_no") or ""
	if eid:
		return "EID"
	return ""


def learner_row_from_student(student, student_name="", idx=1, student_group=None):
	from numerouno.numerouno.utils.signatures import resolve_learner_signature

	names, surname = _split_name(student, student_name)
	return {
		"sr_no": idx,
		"student": student,
		"learner_names": names,
		"learner_surname": surname,
		"signature": resolve_learner_signature(student, student_group, None),
		"date_of_birth": frappe.db.get_value("Student", student, "date_of_birth"),
		"id_type": _id_type(student),
		"telephone": frappe.db.get_value("Student", student, "student_mobile_number") or "",
		"retake": 0,
		"gender": _gender_code(frappe.db.get_value("Student", student, "gender")),
	}


def group_defaults(student_group):
	student_group = (student_group or "").strip()
	if not student_group:
		return {}

	sg = frappe.db.get_value(
		"Student Group",
		student_group,
		[
			"name",
			"course",
			"from_date",
			"to_date",
			"custom_from_date",
			"custom_to_date",
			"custom_course_location_name",
		],
		as_dict=True,
	) or frappe._dict()

	course_title = ""
	if sg.course:
		course_title = (
			frappe.db.get_value("Course", sg.course, "course_name")
			or frappe.db.get_value("Course", sg.course, "name")
			or sg.course
		)

	start = sg.get("custom_from_date") or sg.get("from_date")
	end = sg.get("custom_to_date") or sg.get("to_date")
	instructor = get_group_instructor(student_group)
	instructor_name = (
		frappe.db.get_value("Instructor", instructor, "instructor_name") if instructor else ""
	)

	students = frappe.get_all(
		"Student Group Student",
		filters={"parent": student_group},
		fields=["student", "student_name"],
		order_by="idx",
	)
	learners = [
		learner_row_from_student(row.student, row.student_name, idx, student_group)
		for idx, row in enumerate(students, start=1)
	]

	return {
		"student_group": student_group,
		"course": sg.course or "",
		"centre_name": DEFAULT_CENTRE,
		"centre_number": DEFAULT_CENTRE_NO,
		"nominated_tutor": instructor or "",
		"nominated_tutor_name": instructor_name or "",
		"examination_venue": sg.get("custom_course_location_name") or "",
		"course_exam_id": student_group,
		"number_of_learners": len(learners),
		"qualification_unit_title": course_title,
		"examination_date": start or today(),
		"course_from": start,
		"course_to": end,
		"invigilator_date": today(),
		"learners": learners,
	}


def _as_dict(row):
	if isinstance(row, dict):
		return frappe._dict(row)
	as_dict = getattr(type(row), "as_dict", None)
	if callable(as_dict):
		return frappe._dict(as_dict(row))
	return frappe._dict(row or {})


def paginate_learners(learners):
	rows = [_as_dict(row) for row in (learners or [])]
	if not rows:
		rows = [frappe._dict({"sr_no": i}) for i in range(1, ROWS_PER_PAGE + 1)]
	pages = []
	for start in range(0, max(len(rows), 1), ROWS_PER_PAGE):
		chunk = list(rows[start : start + ROWS_PER_PAGE])
		while len(chunk) < ROWS_PER_PAGE:
			chunk.append(frappe._dict({"sr_no": start + len(chunk) + 1}))
		pages.append(chunk)
	return pages


def format_dob(value):
	if not value:
		return ""
	try:
		return formatdate(getdate(value), "dd/MM/yy")
	except Exception:
		return str(value)


@frappe.whitelist()
def populate_from_student_group(docname, student_group):
	docname = (docname or "").strip()
	if not docname or docname.startswith("new-"):
		frappe.throw("Please save the HABC2 Examination Declaration first.")
	if not student_group:
		frappe.throw("Student Group is required")

	defaults = group_defaults(student_group)
	doc = frappe.get_doc("HABC2 Examination Declaration", docname)
	for field in (
		"student_group",
		"course",
		"centre_name",
		"nominated_tutor",
		"nominated_tutor_name",
		"examination_venue",
		"course_exam_id",
		"number_of_learners",
		"qualification_unit_title",
		"examination_date",
		"course_from",
		"course_to",
	):
		if defaults.get(field) and not doc.get(field):
			doc.set(field, defaults.get(field))
	doc.student_group = student_group
	doc.learners = []
	for row in defaults.get("learners") or []:
		doc.append("learners", row)
	doc.save()
	return doc.name
