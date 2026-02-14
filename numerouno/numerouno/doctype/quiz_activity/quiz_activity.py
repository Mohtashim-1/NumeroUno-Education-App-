# Copyright (c) 2024, Numerouno and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class QuizActivity(Document):
	pass


def auto_create_assessment_documents(doc, method):
	"""
	Automatically create Assessment Plan, Assessment Result, and Student Group
	after Quiz Activity is created.
	This function is called via doc_events hook in hooks.py
	"""
	try:
		# Skip if already has assessment result
		if hasattr(doc, 'custom_assesment_result') and doc.custom_assesment_result:
			frappe.logger().info(f"[QUIZ ACTIVITY AUTO-CREATE] Quiz Activity {doc.name} already has Assessment Result: {doc.custom_assesment_result}. Skipping auto-creation.")
			return
		
		# Skip if already has assessment plan and student group
		has_assessment_plan = hasattr(doc, 'custom_assesment_plan') and doc.custom_assesment_plan
		has_student_group = hasattr(doc, 'custom_student_group') and doc.custom_student_group
		
		if has_assessment_plan and has_student_group:
			# Check if assessment result exists for this student and assessment plan
			if has_assessment_plan:
				existing_result = frappe.db.exists("Assessment Result", {
					"student": doc.student,
					"assessment_plan": doc.custom_assesment_plan,
					"docstatus": ["<", 2]
				})
				if existing_result:
					frappe.logger().info(f"[QUIZ ACTIVITY AUTO-CREATE] Assessment Result already exists: {existing_result}. Skipping auto-creation.")
					return
		
		# Check if required fields are present
		if not doc.student:
			frappe.logger().warning(f"[QUIZ ACTIVITY AUTO-CREATE] Quiz Activity {doc.name} has no student. Cannot create Assessment documents.")
			return
		
		if not doc.quiz:
			frappe.logger().warning(f"[QUIZ ACTIVITY AUTO-CREATE] Quiz Activity {doc.name} has no quiz. Cannot create Assessment documents.")
			return
		
		frappe.logger().info(f"[QUIZ ACTIVITY AUTO-CREATE] Starting auto-creation for Quiz Activity: {doc.name}")
		
		# Import the function from quiz_api
		from numerouno.numerouno.api.quiz_api import create_assessment_result_from_quiz_activity
		
		# Call the function to create assessment documents
		# This function will create:
		# 1. Student Group (if not found, it will try to find from enrollment or student)
		# 2. Assessment Plan (if not exists)
		# 3. Assessment Result
		try:
			result = create_assessment_result_from_quiz_activity(doc.name)
			
			if result and isinstance(result, dict):
				if result.get("status") == "success":
					frappe.logger().info(f"[QUIZ ACTIVITY AUTO-CREATE] ✓ Successfully created Assessment documents for Quiz Activity: {doc.name}")
				elif result.get("status") == "info":
					frappe.logger().info(f"[QUIZ ACTIVITY AUTO-CREATE] ℹ {result.get('message', '')} for Quiz Activity: {doc.name}")
				elif result.get("status") == "error":
					frappe.logger().error(f"[QUIZ ACTIVITY AUTO-CREATE] ✗ Error creating Assessment documents for Quiz Activity {doc.name}: {result.get('message', 'Unknown error')}")
				else:
					frappe.logger().warning(f"[QUIZ ACTIVITY AUTO-CREATE] Unknown status in result for Quiz Activity {doc.name}: {result}")
			else:
				frappe.logger().warning(f"[QUIZ ACTIVITY AUTO-CREATE] Function returned unexpected result type for Quiz Activity {doc.name}: {type(result)}")
		except Exception as func_error:
			# If the function itself raises an exception, log it
			error_msg = f"Exception calling create_assessment_result_from_quiz_activity for Quiz Activity {doc.name}: {str(func_error)}"
			frappe.log_error(f"{error_msg}\nTraceback: {frappe.get_traceback()}", "Quiz Activity Auto-Create Function Error")
			frappe.logger().error(f"[QUIZ ACTIVITY AUTO-CREATE] {error_msg}")
			
	except Exception as e:
		# Log error but don't fail the quiz activity creation
		error_msg = f"Error in auto_create_assessment_documents for Quiz Activity {doc.name}: {str(e)}"
		frappe.log_error(f"{error_msg}\nTraceback: {frappe.get_traceback()}", "Quiz Activity Auto-Create Error")
		frappe.logger().error(f"[QUIZ ACTIVITY AUTO-CREATE] {error_msg}")

