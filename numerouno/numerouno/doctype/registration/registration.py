from datetime import date

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate


class Registration(Document):
	def validate(self):
		self._sync_course_context()
		self._sync_learner_name_from_declaration()
		self._normalize_block_letter_fields()
		self._set_full_name()
		self._set_date_of_birth()
		self._normalize_conditional_fields()
		self._apply_review_defaults()
		self._validate_course_dates()

	def _normalize_block_letter_fields(self):
		for fieldname in (
			"joining_declaration_name",
			"learner_surname",
			"other_names",
			"joining_company",
		):
			value = self.get(fieldname)
			if isinstance(value, str) and value.strip():
				self.set(fieldname, " ".join(value.split()).upper())

	def _sync_learner_name_from_declaration(self):
		name_parts = split_name_parts(self.joining_declaration_name)
		if not name_parts:
			return

		if not self.learner_surname:
			self.learner_surname = name_parts["surname"]
		if not self.other_names:
			self.other_names = name_parts["other_names"]

	def _sync_course_context(self):
		if not self.course_name:
			return

		course = frappe.db.get_value(
			"Course",
			self.course_name,
			["course_name", "course_code", "is_opito"],
			as_dict=True,
		)
		if not course:
			return

		if not course.get("is_opito"):
			frappe.throw("Selected Course Name must be an OPITO course.")

		course_title = (course.get("course_name") or self.course_name or "").strip()
		course_code = (course.get("course_code") or "").strip()
		product_label = f"{course_title} ({course_code})" if course_code else course_title

		self.product_title = product_label
		self.joining_product_title = product_label
		self.joining_instructions_title = (
			f"Course Joining Instructions - {course_title}" if course_title else self.joining_instructions_title
		)
		self.joining_opito_code = (
			f"{course_title} OPITO Code ({course_code})" if course_title and course_code else course_title
		)

	def _set_full_name(self):
		parts = [self.learner_surname, self.other_names]
		self.full_name = " ".join(part for part in parts if part)

	def _set_date_of_birth(self):
		day = cint_or_none(self.date_of_birth_day)
		month = cint_or_none(self.date_of_birth_month)
		year = cint_or_none(self.date_of_birth_year)

		if not all([day, month, year]):
			self.date_of_birth = None
			return

		try:
			self.date_of_birth = date(year, month, day).isoformat()
		except ValueError as exc:
			frappe.throw(f"Invalid Date of Birth: {exc}")

	def _normalize_conditional_fields(self):
		if self.aware_of_opito_learner_number != "Yes":
			self.opito_learner_number = None
		elif self.opito_learner_number:
			self.opito_learner_number = " ".join(str(self.opito_learner_number).split()).upper()

		if self.has_vantage_number != "Yes":
			self.vantage_number = None
		elif self.vantage_number:
			self.vantage_number = " ".join(str(self.vantage_number).split()).upper()

	def _apply_review_defaults(self):
		self.registration_status = self.registration_status or "Pending"
		if self.registration_status == "Flagged":
			self.is_flagged = 1
		elif self.is_flagged and self.registration_status == "Approved":
			self.registration_status = "Flagged"

		if not self.signature_date:
			self.signature_date = nowdate()
		if not self.joining_declaration_date:
			self.joining_declaration_date = nowdate()

	def _validate_course_dates(self):
		if self.course_start_date and self.finish_date and self.finish_date < self.course_start_date:
			frappe.throw("Finish Date cannot be earlier than Course Start Date.")


def cint_or_none(value):
	try:
		return int(value)
	except (TypeError, ValueError):
		return None


def split_name_parts(value):
	name = " ".join(str(value or "").split())
	if not name:
		return None

	parts = name.split(" ")
	if len(parts) == 1:
		return {"surname": parts[0], "other_names": parts[0]}

	return {
		"surname": parts[-1],
		"other_names": " ".join(parts[:-1]),
	}
