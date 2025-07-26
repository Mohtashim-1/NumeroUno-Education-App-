# Copyright (c) 2025, mohtashim and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PracticalAssesment(Document):
	def validate(self):
		self.get_practical_assesment_table_from_template()
		self.get_assesment_criteria()
		self.total_rating()


	def get_practical_assesment_table_from_template(self):
		if self.practical_assesment_template and not self.practical_assesment_table:
			# Get the template document
			template_doc = frappe.get_doc("Practical Assesment Template", self.practical_assesment_template)
			
			# Copy practical assessment table from template to current document
			for template_row in template_doc.practical_assesment_table:
				self.append("practical_assesment_table", {
					"assesment_type": template_row.assesment_type,
				})

	def get_assesment_criteria(self):
		"""
		Get maximum score from Assessment Plan for the selected assessment criteria
		"""
		if self.assessment_plan and self.assesment_criteria:
			assesment_plan = frappe.get_doc("Assessment Plan", self.assessment_plan)
			
			# Look for the assessment criteria in the plan's child table
			for criteria_row in assesment_plan.assessment_criteria:
				if criteria_row.assessment_criteria == self.assesment_criteria:
					self.maximum_score = criteria_row.maximum_score
					break
			else:
				# If not found, set default maximum score
				self.maximum_score = 5

	def total_rating(self):
		"""
		Calculate total rating from practical assessment table
		"""
		total = 0
		count = 0
		
		if self.practical_assesment_table:
			for row in self.practical_assesment_table:
				if row.rating:
					total += row.rating
					count += 1
		
		# Calculate average rating
		if count > 0:
			average_rating = total / count
			self.obtained_rating = round(average_rating, 2)
		else:
			self.obtained_rating = 0
		
		# Also set total score for assessment result
		self.total_score = total

	def on_submit(self):
		self.create_assesment_result()

	def create_assesment_result(self):
		"""
		Create or update Assessment Result document when Practical Assessment is submitted
		"""
		# Check if Assessment Result already exists for this student and student group
		existing_result = frappe.db.exists("Assessment Result", {
			"student": self.student,
			"student_group": self.student_group,
			"docstatus": 1  # Submitted
		})

		if existing_result:
			# Update existing Assessment Result by adding new row
			self.update_existing_assessment_result(existing_result)
		else:
			# Create new Assessment Result
			self.create_new_assessment_result()

	def create_new_assessment_result(self):
		"""
		Create a new Assessment Result document
		"""
		# Get student details
		student_doc = frappe.get_doc("Student", self.student)
		company = frappe.defaults.get_defaults().company
		
		# Create Assessment Result
		assessment_result = frappe.new_doc("Assessment Result")
		assessment_result.update({
			"custom_company":company,
			"student": self.student,
			"student_name": student_doc.student_name,
			"student_group": self.student_group,
			"assessment_plan": self.assessment_plan,
			"assessment_group": self.assesment_group,  # Fixed: use assesment_group (one 's')
			"academic_year": frappe.defaults.get_defaults().academic_year,
			"comment": f"Practical Assessment submitted on {self.posting_date}"
		})

		# Add assessment details with proper maximum_score
		for row in self.practical_assesment_table:
			score = row.rating or 0
			maximum_score = self.maximum_score or 5  # Use the maximum_score from assessment criteria
			
		detail_row = assessment_result.append("details", {
			"assessment_criteria": self.assesment_criteria,
			"score": self.maximum_score * self.obtained_rating,
			"grade": self.get_grade(score, maximum_score)
		})
		# Set maximum_score directly on the row object
		detail_row.maximum_score = maximum_score

		# Set total score and overall grade using calculated values
		assessment_result.total_score = self.total_score
		assessment_result.maximum_score = len(self.practical_assesment_table) * (self.maximum_score or 5)
		assessment_result.grade = self.get_grade(self.total_score, assessment_result.maximum_score)

		# Save and submit
		assessment_result.insert(ignore_permissions=True)
		assessment_result.submit()

		frappe.msgprint(f"Assessment Result created: {assessment_result.name}")

	def update_existing_assessment_result(self, existing_result_name):
		"""
		Update existing Assessment Result by adding new assessment details
		"""
		assessment_result = frappe.get_doc("Assessment Result", existing_result_name)
		
		# Add new assessment details
		for row in self.practical_assesment_table:
			score = row.rating or 0
			maximum_score = self.maximum_score or 5
			
			detail_row = assessment_result.append("details", {
				"assessment_criteria": row.assesment_type,
				"score": score,
				"grade": self.get_grade(score, maximum_score)
			})
			# Set maximum_score directly on the row object
			detail_row.maximum_score = maximum_score

		# Update total score and overall grade using calculated values
		assessment_result.total_score += self.total_score
		assessment_result.maximum_score += len(self.practical_assesment_table) * (self.maximum_score or 5)
		assessment_result.grade = self.get_grade(assessment_result.total_score, assessment_result.maximum_score)

		# Save
		assessment_result.save(ignore_permissions=True)

		frappe.msgprint(f"Assessment Result updated: {assessment_result.name}")

	def get_grade(self, score, maximum_score):
		"""
		Calculate grade based on score and maximum score
		You can customize this grading logic as needed
		"""
		if maximum_score == 0:
			return "N/A"
		
		percentage = (score / maximum_score) * 100
		
		if percentage >= 90:
			return "A+"
		elif percentage >= 80:
			return "A"
		elif percentage >= 70:
			return "B+"
		elif percentage >= 60:
			return "B"
		elif percentage >= 50:
			return "C+"
		elif percentage >= 40:
			return "C"
		else:
			return "F"


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
	
	result = frappe.db.sql(query, as_dict=True)
	
	# Convert to list format that Frappe expects for dropdowns
	dropdown_result = []
	for row in result:
		dropdown_result.append([row['name'], row['student_name']])
	
	return dropdown_result

