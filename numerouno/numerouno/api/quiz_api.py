import frappe
from frappe import _

@frappe.whitelist(allow_guest=True, methods=['GET', 'POST'])
def get_student_groups():
    """Get all student groups for public quiz selection"""
    try:
        student_groups = frappe.get_all(
            "Student Group",
            fields=["name", "student_group_name", "course", "from_date", "to_date"],
            filters={"disabled": 0},
            order_by="student_group_name"
        )
        
        # Convert datetime objects to strings for JSON serialization
        for group in student_groups:
            if group.get('from_date'):
                group['from_date'] = str(group['from_date'])
            if group.get('to_date'):
                group['to_date'] = str(group['to_date'])
        
        return {
            "status": "success",
            "student_groups": student_groups
        }
    except Exception as e:
        frappe.log_error(f"Error getting student groups: {str(e)}", "Quiz API")
        return {
            "status": "error",
            "message": "Failed to load student groups"
        }

@frappe.whitelist(allow_guest=True, methods=['GET', 'POST'])
def get_students_by_group(student_group):
    """Get students from a specific student group"""
    try:
        if not student_group:
            return {
                "status": "error",
                "message": "Student group is required"
            }
        
        # Get students from Student Group Student table
        students = frappe.get_all(
            "Student Group Student",
            filters={"parent": student_group},
            fields=["student", "student_name"],
            order_by="student_name"
        )
        
        return {
            "status": "success",
            "students": students
        }
    except Exception as e:
        frappe.log_error(f"Error getting students by group: {str(e)}", "Quiz API")
        return {
            "status": "error",
            "message": "Failed to load students"
        }

@frappe.whitelist(allow_guest=True, methods=['GET', 'POST'])
def get_available_quizzes(student_group, student):
    """Get available quizzes for a student in a specific group"""
    try:
        if not student_group or not student:
            return {
                "status": "error",
                "message": "Student group and student are required"
            }
        
        # Get the student group details
        student_group_doc = frappe.get_doc("Student Group", student_group)
        course_name = student_group_doc.course
        
        if not course_name:
            return {
                "status": "success",
                "quizzes": []
            }
        
        # Find LMS Course with matching title
        lms_courses = frappe.get_all(
            "LMS Course",
            filters={"title": course_name},
            fields=["name"]
        )
        
        if not lms_courses:
            return {
                "status": "success",
                "quizzes": []
            }
        
        lms_course = lms_courses[0].name
        
        # Get quizzes from the LMS course
        quizzes = frappe.get_all(
            "LMS Quiz",
            filters={"course": lms_course},
            fields=["name", "title", "total_marks", "passing_percentage", "max_attempts"],
            order_by="title"
        )
        
        return {
            "status": "success",
            "quizzes": quizzes
        }
    except Exception as e:
        frappe.log_error(f"Error getting available quizzes: {str(e)}", "Quiz API")
        return {
            "status": "error",
            "message": "Failed to load quizzes"
        }
