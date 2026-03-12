import frappe
from frappe import _

def get_context(context):
    """Get context for quiz attempt page"""
    context.no_cache = 1
    context.no_breadcrumbs = 1
    
    # Get quiz name from URL
    quiz_name = frappe.form_dict.get('quiz_name')
    if not quiz_name:
        frappe.throw(_("Quiz not found"), frappe.PermissionError)
    
    # Check if quiz exists
    if not frappe.db.exists("LMS Quiz", quiz_name):
        frappe.throw(_("Quiz not found"), frappe.PermissionError)
    
    # Get quiz details
    quiz_doc = frappe.get_doc("LMS Quiz", quiz_name)
    context.quiz_name = quiz_name
    context.quiz_title = quiz_doc.title
    context.quiz_course = quiz_doc.course
    
    # Get student and student group from query parameters
    context.student = frappe.form_dict.get('student')
    context.student_group = frappe.form_dict.get('student_group')
    
    if not context.student or not context.student_group:
        frappe.throw(_("Student and student group are required"), frappe.PermissionError)
    
    # Verify student belongs to the student group
    if not frappe.db.exists("Student Group Student", {
        "parent": context.student_group,
        "student": context.student
    }):
        frappe.throw(_("Student does not belong to the selected group"), frappe.PermissionError)
    
    # Get student details
    student_doc = frappe.get_doc("Student", context.student)
    context.student_name = student_doc.student_name
    context.student_email = student_doc.student_email_id
    
    # Get student group details
    student_group_doc = frappe.get_doc("Student Group", context.student_group)
    context.student_group_title = student_group_doc.title
    context.course_name = student_group_doc.course
    
    return context
