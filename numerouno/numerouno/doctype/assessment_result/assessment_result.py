# Copyright (c) 2024, Numerouno and contributors
# For license information, please see license.txt

import frappe
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
