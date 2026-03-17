import frappe
from frappe.model.document import Document


class CourseDeclarationTemplate(Document):
	def validate(self):
		self._validate_opito_course()
		self._set_parameter_codes()

	def _validate_opito_course(self):
		if not self.course:
			return

		is_opito = frappe.db.get_value("Course", self.course, "is_opito")
		if not is_opito:
			frappe.throw("Course Declaration Template can only be created for OPITO courses.")

	def _set_parameter_codes(self):
		seen_codes = set()
		for index, row in enumerate(self.declarations or [], start=1):
			code = (row.parameter_code or "").strip()
			if not code:
				code = f"DECL-{index}"
			row.parameter_code = code.upper()

			if row.parameter_code in seen_codes:
				frappe.throw(f"Duplicate declaration parameter code found: {row.parameter_code}")
			seen_codes.add(row.parameter_code)
