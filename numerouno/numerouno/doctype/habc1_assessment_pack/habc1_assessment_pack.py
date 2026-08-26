# Copyright (c) 2026, NumeroUNO and contributors

import frappe
from frappe.model.document import Document
from frappe.utils import cint, formatdate, getdate, today

from numerouno.numerouno.utils.signatures import get_instructor_signature


ROWS_PER_PAGE = 12
REFERRAL_ROWS = 4
DEFAULT_CENTRE = "NUMERO UNO TRAINING AND CONSULTING, LLC"
DEFAULT_VENUE = "P.O.BOX :132435, ICAD - 1, BLOCK - B, BEHIND DALMA MALL, MUSSAFFAH ABU DHABI, UAE."
DEFAULT_PHONE = "25575220"
DEFAULT_CENTRE_NO = "12043"
DEFAULT_TITLE = "Highfield International Emergency First Aid, AED & CPR all Ages (Level 3 Award)"


class HABC1AssessmentPack(Document):
	def before_print(self, settings=None):
		self._sync_tutor()
		self.learner_pages = paginate_learners(self.learners)
		self.referral_rows = pad_referrals(self.referrals)

	def validate(self):
		self._sync_tutor()
		self._number_rows()
		if not self.form_title:
			self.form_title = DEFAULT_TITLE
		if not self.centre_name:
			self.centre_name = DEFAULT_CENTRE
		if not self.centre_number:
			self.centre_number = DEFAULT_CENTRE_NO

	def _sync_tutor(self):
		from numerouno.numerouno.utils.signatures import get_instructor_signature, is_empty_signature

		if not self.tutor and self.student_group:
			self.tutor = get_group_instructor(self.student_group)
		if self.tutor:
			self.tutor_name = (
				frappe.db.get_value("Instructor", self.tutor, "instructor_name") or self.tutor_name
			)
			sig = get_instructor_signature(self.tutor)
			if sig and (is_empty_signature(self.tutor_signature) or self.has_value_changed("tutor")):
				self.tutor_signature = sig
		if self.assessor:
			self.assessor_name = (
				frappe.db.get_value("Instructor", self.assessor, "instructor_name") or self.assessor_name
			)
			sig = get_instructor_signature(self.assessor)
			if sig and (is_empty_signature(self.assessor_signature) or self.has_value_changed("assessor")):
				self.assessor_signature = sig
		elif is_empty_signature(self.assessor_signature) and self.tutor_signature:
			self.assessor_signature = self.tutor_signature

	def _number_rows(self):
		for idx, row in enumerate(self.learners or [], start=1):
			row.sr_no = idx
			if row.learner_name:
				row.learner_name = (row.learner_name or "").upper()


def get_group_instructor(student_group):
	if not student_group:
		return None
	return frappe.db.get_value(
		"Student Group Instructor",
		{"parent": student_group},
		"instructor",
		order_by="idx asc",
	)


def _gender_code(value):
	value = (value or "").strip().lower()
	if value in ("m", "male", "man"):
		return "M"
	if value in ("f", "female", "woman"):
		return "F"
	return ""


def learner_row_from_student(student, student_name="", idx=1):
	full = (student_name or frappe.db.get_value("Student", student, "student_name") or student or "").strip()
	return {
		"sr_no": idx,
		"student": student,
		"learner_name": full.upper(),
		"date_of_birth": frappe.db.get_value("Student", student, "date_of_birth"),
		"telephone": frappe.db.get_value("Student", student, "student_mobile_number") or "",
		"gender": _gender_code(frappe.db.get_value("Student", student, "gender")),
		"refer": 0,
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

	start = sg.get("custom_from_date") or sg.get("from_date")
	end = sg.get("custom_to_date") or sg.get("to_date")
	instructor = get_group_instructor(student_group)
	instructor_name = frappe.db.get_value("Instructor", instructor, "instructor_name") if instructor else ""
	sig = get_instructor_signature(instructor) if instructor else ""
	venue = sg.get("custom_course_location_name") or DEFAULT_VENUE

	students = frappe.get_all(
		"Student Group Student",
		filters={"parent": student_group},
		fields=["student", "student_name"],	
		order_by="idx",
	)
	learners = [
		learner_row_from_student(row.student, row.student_name, idx)
		for idx, row in enumerate(students, start=1)
	]

	return {
		"student_group": student_group,
		"course": sg.course or "",
		"form_title": DEFAULT_TITLE,
		"centre_name": DEFAULT_CENTRE,
		"venue_address": venue,
		"telephone_no": DEFAULT_PHONE,
		"centre_number": DEFAULT_CENTRE_NO,
		"tutor": instructor or "",
		"tutor_name": instructor_name or "",
		"assessor": instructor or "",
		"assessor_name": instructor_name or "",
		"tutor_signature": sig,
		"assessor_signature": sig,
		"course_identification_no": f"CQ {student_group}",
		"course_start_date": start or today(),
		"course_finish_date": end,
		"tutor_date": today(),
		"assessor_date": today(),
		"learners": learners,
		"referrals": [],
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
		chunk = rows[start : start + ROWS_PER_PAGE]
		while len(chunk) < ROWS_PER_PAGE:
			chunk.append(frappe._dict({"sr_no": start + len(chunk) + 1}))
		pages.append(chunk)
	return pages


def pad_referrals(referrals):
	rows = [_as_dict(row) for row in (referrals or [])]
	while len(rows) < REFERRAL_ROWS:
		rows.append(frappe._dict())
	return rows


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
		frappe.throw("Please save the HABC1 Assessment Pack first.")
	if not student_group:
		frappe.throw("Student Group is required")

	defaults = group_defaults(student_group)
	doc = frappe.get_doc("HABC1 Assessment Pack", docname)
	for field, value in defaults.items():
		if field in ("learners", "referrals"):
			continue
		if value and not doc.get(field):
			doc.set(field, value)
	doc.student_group = student_group
	doc.learners = []
	for row in defaults.get("learners") or []:
		doc.append("learners", row)
	doc.save()
	return doc.name
