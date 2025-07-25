# Copyright (c) 2025, mohtashim and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PracticalAssesment(Document):
	def validate(self):
		self.get_practical_assesment_table_from_template()

	def get_practical_assesment_table_from_template(self):
		if self.practical_assesment_template and not self.practical_assesment_table:
			# Get the template document
			template_doc = frappe.get_doc("Practical Assesment Template", self.practical_assesment_template)
			
			# Copy practical assessment table from template to current document
			for template_row in template_doc.practical_assesment_table:
				self.append("practical_assesment_table", {
					"assesment_type": template_row.assesment_type,
				})


@frappe.whitelist()
def test_function():
	"""Test function to verify custom functions are loaded"""
	print("=== TEST FUNCTION CALLED ===")
	return "Test function works!"


@frappe.whitelist()
def get_students_by_group(doctype, txt, searchfield, start, page_len, filters):
	"""
	Filter students based on the selected student group
	Get students from Student Group Student table and return student names
	"""
	# Parse filters if it's a string
	if isinstance(filters, str):
		import json
		filters = json.loads(filters)
	
	conditions = []
	
	# Add student group filter - get students from Student Group Student table
	if filters and filters.get('student_group'):
		student_group = filters.get('student_group')
		conditions.append(f"sgs.parent = '{student_group}'")
	
	# Add text search filter - search in student names
	if txt and txt.strip():
		search_text = txt.strip()
		conditions.append(f"(s.student_name LIKE '%{search_text}%' OR sgs.student_name LIKE '%{search_text}%')")
		
	where_clause = " AND ".join(conditions) if conditions else "1=1"
	
	# Query Student Group Student table joined with Student table to get proper names
	query = f"""
		SELECT sgs.student as name, 
		       COALESCE(sgs.student_name, s.student_name, s.name) as student_name
		FROM `tabStudent Group Student` sgs
		LEFT JOIN `tabStudent` s ON sgs.student = s.name
		WHERE {where_clause}
		ORDER BY student_name
		LIMIT {start}, {page_len}
	"""
	
	# Debug logging
	
	result = frappe.db.sql(query, as_dict=True)
	
	# Convert to list format that Frappe expects for dropdowns
	dropdown_result = []
	for row in result:
		dropdown_result.append([row['name'], row['student_name']])
	
	return dropdown_result