# Copyright (c) 2024, Numerouno and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date

class AssessmentResult(Document):
	def validate(self):
		# Call parent validate if exists
		if hasattr(super(), 'validate'):
			super().validate()
		
		# Fallback validity date: course start date + 1 year - 1 day
		if not self.certificate_validity_date and self.course_start_date:
			self.certificate_validity_date = add_to_date(
				self.course_start_date,
				years=1,
				days=-1,
				as_string=True
			)
	
	def on_update(self):
		# Only run OCR for image certificates; PDFs should upload without OCR.
		if self.custom_certificate and not self.ocr_extracted_text and self._is_image_certificate():
			self.process_certificate_ocr()

	def _is_image_certificate(self):
		certificate = (self.custom_certificate or '').lower()
		return certificate.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff'))
	
	def process_certificate_ocr(self):
		"""Process OCR for the uploaded certificate"""
		try:
			from numerouno.numerouno.utils.ocr_utils import process_certificate_ocr
			
			result = process_certificate_ocr(
				doctype='Assessment Result',
				docname=self.name,
				field_name='custom_certificate'
			)
			
			if result.get('success'):
				# Update the document with OCR data
				self.ocr_extracted_text = result.get('extracted_text', '')
				self.ocr_confidence = result.get('confidence', 0)
				
				# Save without triggering validation to avoid recursion
				frappe.db.set_value('Assessment Result', self.name, 'ocr_extracted_text', self.ocr_extracted_text)
				frappe.db.set_value('Assessment Result', self.name, 'ocr_confidence', self.ocr_confidence)
				
				frappe.msgprint(
					msg=f"OCR processing completed successfully! Confidence: {self.ocr_confidence:.1f}%",
					title="OCR Success",
					indicator="green"
				)
			else:
				frappe.msgprint(
					msg=f"OCR processing failed: {result.get('message', 'Unknown error')}",
					title="OCR Error",
					indicator="red"
				)
				
		except Exception as e:
			frappe.log_error(f"OCR processing error in Assessment Result: {str(e)}", "Assessment Result OCR")
			frappe.msgprint(
				msg=f"OCR processing failed: {str(e)}",
				title="OCR Error",
				indicator="red"
			)


def _course_allows_bulk_result(course):
	if not course:
		return False

	if not frappe.get_meta("Course").has_field("custom_result_bulk"):
		return False

	return bool(frappe.db.get_value("Course", course, "custom_result_bulk"))


def _get_student_group_course(student_group):
	course = frappe.db.get_value("Student Group", student_group, "course")
	if not course:
		frappe.throw(_("Student Group {0} does not have a course.").format(student_group))
	return course


def _validate_bulk_result_enabled(student_group):
	course = _get_student_group_course(student_group)
	if not _course_allows_bulk_result(course):
		frappe.throw(_("Bulk pass/fail result is not enabled for course {0}.").format(course))
	return course


def _get_bulk_result_assessment_plan(student_group):
	course = _get_student_group_course(student_group)
	plans = frappe.get_all(
		"Assessment Plan",
		filters={
			"student_group": student_group,
			"course": course,
			"docstatus": 1,
		},
		fields=["name"],
		order_by="modified desc",
		limit=1,
	)
	if not plans:
		frappe.throw(
			_("Please submit an Assessment Plan for Student Group {0} before creating pass/fail results.").format(
				student_group
			)
		)
	return plans[0].name


def _get_existing_result(student, assessment_plan):
	return frappe.db.exists(
		"Assessment Result",
		{
			"student": student,
			"assessment_plan": assessment_plan,
			"docstatus": ["<", 2],
		},
	)


def _status_to_score(status, maximum_score):
	status = (status or "").strip().lower()
	if status == "pass":
		return maximum_score
	if status == "fail":
		return 0
	frappe.throw(_("Status must be Pass or Fail."))


def _get_default_company():
	company = frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
	if company:
		return company

	company = frappe.db.get_single_value("System Settings", "default_company")
	if company:
		return company

	companies = frappe.get_all("Company", fields=["name"], limit=1)
	return companies[0].name if companies else None


@frappe.whitelist()
def get_students_for_bulk_pass_fail_result(student_group):
	student_group = (student_group or "").strip()
	if not student_group:
		frappe.throw(_("Student Group is required."))

	course = _validate_bulk_result_enabled(student_group)
	assessment_plan = _get_bulk_result_assessment_plan(student_group)
	students = frappe.get_all(
		"Student Group Student",
		filters={"parent": student_group, "active": 1},
		fields=["student", "student_name"],
		order_by="idx asc",
	)

	for row in students:
		existing_result = _get_existing_result(row.student, assessment_plan)
		row["assessment_result"] = existing_result
		row["result_status"] = "Existing" if existing_result else "Pass"

	return {
		"course": course,
		"assessment_plan": assessment_plan,
		"students": students,
	}


@frappe.whitelist()
def create_bulk_pass_fail_assessment_results(student_group, results_data):
	student_group = (student_group or "").strip()
	if not student_group:
		frappe.throw(_("Student Group is required."))

	_validate_bulk_result_enabled(student_group)
	assessment_plan = _get_bulk_result_assessment_plan(student_group)
	plan_doc = frappe.get_doc("Assessment Plan", assessment_plan)
	if not plan_doc.assessment_criteria:
		frappe.throw(_("Assessment Plan {0} has no criteria.").format(assessment_plan))

	if isinstance(results_data, str):
		import json

		results_data = json.loads(results_data)

	allowed_students = set(
		frappe.get_all(
			"Student Group Student",
			filters={"parent": student_group, "active": 1},
			pluck="student",
		)
	)

	created = []
	skipped = []
	for row in results_data or []:
		student = (row.get("student") or "").strip()
		status = (row.get("result_status") or row.get("status") or "").strip()
		if not student or student not in allowed_students:
			continue
		if status.lower() not in ("pass", "fail"):
			continue

		existing_result = _get_existing_result(student, assessment_plan)
		if existing_result:
			existing_docstatus = frappe.db.get_value("Assessment Result", existing_result, "docstatus")
			if existing_docstatus == 1:
				skipped.append({"student": student, "assessment_result": existing_result, "reason": "Already submitted"})
				continue
			result_doc = frappe.get_doc("Assessment Result", existing_result)
		else:
			result_doc = frappe.new_doc("Assessment Result")
			result_doc.assessment_plan = assessment_plan
			result_doc.student = student
			result_doc.student_group = student_group

		result_doc.comment = _("Bulk pass/fail result marked as {0}.").format(status.title())
		result_doc.set("details", [])
		for criteria in plan_doc.assessment_criteria:
			score = _status_to_score(status, criteria.maximum_score or 0)
			result_doc.append(
				"details",
				{
					"assessment_criteria": criteria.assessment_criteria,
					"maximum_score": criteria.maximum_score,
					"score": score,
				},
			)

		if plan_doc.grading_scale:
			result_doc.grading_scale = plan_doc.grading_scale
		if plan_doc.maximum_assessment_score:
			result_doc.maximum_score = plan_doc.maximum_assessment_score
		if frappe.get_meta("Assessment Result").has_field("custom_company"):
			company = _get_default_company()
			if not company:
				frappe.throw(_("Please set a default Company before creating Assessment Results."))
			result_doc.custom_company = company

		if result_doc.is_new():
			result_doc.insert(ignore_permissions=True)
		else:
			result_doc.save(ignore_permissions=True)

		if result_doc.docstatus == 0:
			result_doc.flags.ignore_permissions = True
			result_doc.submit()

		created.append({"student": student, "assessment_result": result_doc.name, "status": status.title()})

	frappe.db.commit()
	return {
		"assessment_plan": assessment_plan,
		"created": created,
		"skipped": skipped,
	}
