# Copyright (c) 2026, NumeroUNO and contributors

import json
from pathlib import Path

import frappe
from frappe.model.document import Document
from frappe.utils import cint, today


class ROSPAPracticalAssessment(Document):
	def before_print(self, settings=None):
		from numerouno.numerouno.utils.signatures import is_empty_signature, resolve_learner_signature

		self._sync_assessor()
		self.learner_signature = resolve_learner_signature(
			self.student, self.student_group, self.learner_signature
		)
		if is_empty_signature(self.assessor_signature) and self.assessor:
			image = frappe.db.get_value("Instructor", self.assessor, "image") or ""
			if image:
				self.assessor_signature = image

	def validate(self):
		if not self.criteria:
			apply_template(self)
		self._sync_assessor()
		self._sync_learner_signature()

	def _sync_learner_signature(self):
		from numerouno.numerouno.utils.signatures import is_empty_signature, resolve_learner_signature

		if not is_empty_signature(getattr(self, "learner_signature", None)):
			return
		self.learner_signature = resolve_learner_signature(
			self.student, self.student_group, self.learner_signature
		)

	def _sync_assessor(self):
		from numerouno.numerouno.utils.signatures import is_empty_signature

		if not self.assessor and self.student_group:
			self.assessor = get_group_instructor(self.student_group)
		if not self.assessor and self.assessor_name:
			self.assessor = resolve_instructor(self.assessor_name)
		if self.assessor:
			self.assessor_name = (
				frappe.db.get_value("Instructor", self.assessor, "instructor_name") or self.assessor_name
			)
			image = frappe.db.get_value("Instructor", self.assessor, "image") or ""
			if image and (is_empty_signature(self.assessor_signature) or self.has_value_changed("assessor")):
				self.assessor_signature = image


def resolve_instructor(value):
	value = (value or "").strip()
	if not value:
		return None
	name = frappe.db.get_value("Instructor", value, "name")
	if name:
		return name
	exact = frappe.db.get_value("Instructor", {"instructor_name": value}, "name")
	if exact:
		return exact
	like = frappe.db.get_value("Instructor", {"instructor_name": ["like", f"{value}%"]}, "name")
	if like:
		return like
	row = frappe.db.sql(
		"""
		select name from `tabInstructor`
		where lower(trim(instructor_name)) = lower(%s)
		limit 1
		""",
		value,
	)
	return row[0][0] if row else None


def get_group_instructor(student_group):
	if not student_group:
		return None
	return frappe.db.get_value(
		"Student Group Instructor",
		{"parent": student_group},
		"instructor",
		order_by="idx asc",
	)


def _load_template():
	path = Path(__file__).parent / "rospa_practical_assessment_template.json"
	return json.loads(path.read_text())


def apply_template(doc):
	template = _load_template()
	doc.form_title = doc.form_title or template.get("form_title")
	doc.form_subtitle = doc.form_subtitle or template.get("form_subtitle")
	doc.criteria = []
	for idx, row in enumerate(template.get("criteria") or [], start=1):
		doc.append(
			"criteria",
			{
				"sr_no": idx,
				"section": row.get("section") or "",
				"outcome": row.get("outcome") or "",
				"criterion": row.get("criterion") or "",
				"achieved": 0,
				"source_of_evidence": "",
			},
		)


def _student_details(student):
	student_name = frappe.db.get_value("Student", student, "student_name") or student
	company = (
		frappe.db.get_value("Student", student, "custom_student_company_name")
		or frappe.db.get_value("Student", student, "customer")
		or ""
	)
	mobile = frappe.db.get_value("Student", student, "student_mobile_number") or ""
	return {
		"student": student,
		"candidate_name": student_name,
		"employing_company": company,
		"mobile_number": mobile,
	}


def _create_for_student(student_group, student_row, assessment_date=None, assessor_name=None, force=False):
	if not force:
		existing = frappe.db.get_value(
			"ROSPA Practical Assessment",
			{
				"student_group": student_group,
				"student": student_row.student,
				"docstatus": ["<", 2],
			},
			"name",
		)
		if existing:
			return {"status": "skipped", "name": existing, "student": student_row.student}

	doc = frappe.new_doc("ROSPA Practical Assessment")
	doc.student_group = student_group
	doc.student = student_row.student
	doc.candidate_name = student_row.student_name or student_row.student
	doc.employing_company = (
		student_row.customer_name
		or frappe.db.get_value("Student", student_row.student, "custom_student_company_name")
		or ""
	)
	doc.mobile_number = frappe.db.get_value("Student", student_row.student, "student_mobile_number") or ""
	doc.assessment_date = assessment_date or today()
	doc.assessor_name = assessor_name or ""
	doc.assessor_date = doc.assessment_date
	apply_template(doc)
	doc.insert(ignore_permissions=True)
	return {"status": "created", "name": doc.name, "student": student_row.student}


@frappe.whitelist()
def load_default_template(docname=None):
	template = _load_template()

	if docname and not str(docname).startswith("new-"):
		doc = frappe.get_doc("ROSPA Practical Assessment", docname)
	else:
		doc = frappe.new_doc("ROSPA Practical Assessment")

	doc.form_title = template.get("form_title")
	doc.form_subtitle = template.get("form_subtitle")
	apply_template(doc)

	if not doc.assessment_date:
		doc.assessment_date = today()

	if docname and not str(docname).startswith("new-"):
		doc.save()
		return doc.name

	return {
		"form_title": doc.form_title,
		"form_subtitle": doc.form_subtitle,
		"assessment_date": doc.assessment_date,
	}


@frappe.whitelist()
def populate_from_student_group(docname, student_group):
	docname = (docname or "").strip()
	if not docname or docname.startswith("new-"):
		frappe.throw("Please save the ROSPA Practical Assessment first.")
	if not student_group:
		frappe.throw("Student Group is required")

	students = frappe.get_all(
		"Student Group Student",
		filters={"parent": student_group},
		fields=["student", "student_name", "customer_name"],
		order_by="idx",
		limit=1,
	)
	if not students:
		frappe.throw("No students found in the selected Student Group.")

	row = students[0]
	doc = frappe.get_doc("ROSPA Practical Assessment", docname)
	doc.student_group = student_group
	doc.student = row.student
	doc.candidate_name = row.student_name or row.student
	doc.employing_company = (
		row.customer_name
		or frappe.db.get_value("Student", row.student, "custom_student_company_name")
		or ""
	)
	doc.mobile_number = frappe.db.get_value("Student", row.student, "student_mobile_number") or ""
	if not doc.criteria:
		apply_template(doc)
	doc.save()
	return doc.name


@frappe.whitelist()
def get_student_group_preview(student_group):
	student_group = (student_group or "").strip()
	if not student_group:
		frappe.throw("Student Group is required")

	students = frappe.get_all(
		"Student Group Student",
		filters={"parent": student_group},
		fields=["student", "student_name", "customer_name"],
		order_by="idx",
	)
	records = []
	for row in students:
		existing = frappe.db.get_value(
			"ROSPA Practical Assessment",
			{
				"student_group": student_group,
				"student": row.student,
				"docstatus": ["<", 2],
			},
			["name", "docstatus"],
			as_dict=True,
		)
		records.append(
			{
				"student": row.student,
				"student_name": row.student_name or row.student,
				"employing_company": row.customer_name or "",
				"existing_name": existing.name if existing else "",
				"existing_docstatus": existing.docstatus if existing else None,
			}
		)

	course = frappe.db.get_value("Student Group", student_group, "course") or ""
	return {
		"student_group": student_group,
		"course": course,
		"total_students": len(records),
		"records": records,
	}


@frappe.whitelist()
def bulk_create_for_student_group(student_group, assessment_date=None, assessor_name=None, skip_existing=1):
	student_group = (student_group or "").strip()
	if not student_group:
		frappe.throw("Student Group is required")

	students = frappe.get_all(
		"Student Group Student",
		filters={"parent": student_group},
		fields=["student", "student_name", "customer_name"],
		order_by="idx",
	)
	if not students:
		frappe.throw("No students found in the selected Student Group.")

	created = []
	skipped = []
	failed = []

	for row in students:
		try:
			if cint(skip_existing):
				existing = frappe.db.get_value(
					"ROSPA Practical Assessment",
					{
						"student_group": student_group,
						"student": row.student,
						"docstatus": ["<", 2],
					},
					"name",
				)
				if existing:
					skipped.append({"student": row.student, "name": existing})
					continue

			result = _create_for_student(
				student_group,
				row,
				assessment_date=assessment_date or today(),
				assessor_name=assessor_name,
				force=not cint(skip_existing),
			)
			if result["status"] == "created":
				created.append(result)
			else:
				skipped.append(result)
		except Exception as exc:
			failed.append({"student": row.student, "reason": str(exc)})

	frappe.db.commit()
	return {
		"student_group": student_group,
		"created_count": len(created),
		"skipped_count": len(skipped),
		"failed_count": len(failed),
		"created": created,
		"skipped": skipped,
		"failed": failed,
	}
