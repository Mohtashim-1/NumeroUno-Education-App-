# mark_as_paid.py

import frappe
from frappe import _

@frappe.whitelist()
def mark_student_as_paid(student_group, student):
    """Mark a specific student as paid in a Student Group"""
    try:
        # Get the Student Group document
        sg_doc = frappe.get_doc("Student Group", student_group)
        
        # Find the student in the students child table
        student_found = False
        for student_row in sg_doc.students:
            if student_row.student == student:
                student_row.custom_invoiced = 1
                student_found = True
                break
        
        if not student_found:
            frappe.throw(_("Student {0} not found in Student Group {1}").format(student, student_group))
        
        # Save the document
        sg_doc.save()
        
        frappe.msgprint(_("Student {0} marked as paid in Student Group {1}").format(student, student_group))
        
        return {"success": True, "message": "Student marked as paid"}
        
    except Exception as e:
        frappe.log_error(f"Error marking student as paid: {str(e)}")
        frappe.throw(_("Error marking student as paid: {0}").format(str(e)))

@frappe.whitelist()
def mark_multiple_students_as_paid(student_data):
    """Mark multiple students as paid"""
    try:
        # Parse the student data (expected format: [{"student_group": "SG-001", "student": "STU-001"}, ...])
        if isinstance(student_data, str):
            import json
            student_data = json.loads(student_data)
        
        success_count = 0
        error_count = 0
        
        for item in student_data:
            try:
                result = mark_student_as_paid(item.get("student_group"), item.get("student"))
                if result.get("success"):
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                error_count += 1
                frappe.log_error(f"Error marking student {item.get('student')} as paid: {str(e)}")
        
        frappe.msgprint(_("Successfully marked {0} students as paid. {1} errors occurred.").format(success_count, error_count))
        
        return {"success": True, "success_count": success_count, "error_count": error_count}
        
    except Exception as e:
        frappe.log_error(f"Error in mark_multiple_students_as_paid: {str(e)}")
        frappe.throw(_("Error marking students as paid: {0}").format(str(e)))

@frappe.whitelist()
def mark_all_students_in_group_as_paid(student_group):
    """Mark all students in a Student Group as paid"""
    try:
        # Get the Student Group document
        sg_doc = frappe.get_doc("Student Group", student_group)
        
        updated_count = 0
        for student_row in sg_doc.students:
            if not student_row.custom_invoiced:
                student_row.custom_invoiced = 1
                updated_count += 1
        
        if updated_count == 0:
            frappe.msgprint(_("No unpaid students found in Student Group {0}").format(student_group))
            return {"success": True, "updated_count": 0}
        
        # Save the document
        sg_doc.save()
        
        frappe.msgprint(_("Marked {0} students as paid in Student Group {1}").format(updated_count, student_group))
        
        return {"success": True, "updated_count": updated_count}
        
    except Exception as e:
        frappe.log_error(f"Error marking all students as paid: {str(e)}")
        frappe.throw(_("Error marking students as paid: {0}").format(str(e)))

@frappe.whitelist()
def get_unpaid_students_summary():
    """Get a summary of unpaid students for quick overview"""
    try:
        # Get total unpaid students
        total_unpaid = frappe.db.sql("""
            SELECT COUNT(*) as count
            FROM `tabStudent Group Student` sgs
            WHERE sgs.custom_invoiced = 0 OR sgs.custom_invoiced IS NULL
        """)[0][0]
        
        # Get groups with unpaid students
        groups_with_unpaid = frappe.db.sql("""
            SELECT COUNT(DISTINCT sg.name) as count
            FROM `tabStudent Group` sg
            JOIN `tabStudent Group Student` sgs ON sgs.parent = sg.name
            WHERE sgs.custom_invoiced = 0 OR sgs.custom_invoiced IS NULL
        """)[0][0]
        
        # Get high priority students (unpaid for more than 30 days)
        high_priority = frappe.db.sql("""
            SELECT COUNT(*) as count
            FROM `tabStudent Group` sg
            JOIN `tabStudent Group Student` sgs ON sgs.parent = sg.name
            WHERE (sgs.custom_invoiced = 0 OR sgs.custom_invoiced IS NULL)
            AND DATEDIFF(CURDATE(), COALESCE(sg.from_date, CURDATE())) > 30
        """)[0][0]
        
        return {
            "total_unpaid": total_unpaid,
            "groups_affected": groups_with_unpaid,
            "high_priority": high_priority
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting unpaid students summary: {str(e)}")
        return {"error": str(e)} 