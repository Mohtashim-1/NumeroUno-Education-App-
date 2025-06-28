import frappe
from frappe import _

@frappe.whitelist()
def fetch_students_group(customer):
    """Fetch Student Groups for a specific customer"""
    try:
        # Get all Student Groups for the customer
        student_groups = frappe.get_all(
            "Student Group",
            filters={"custom_customer": customer},
            fields=["name", "title", "course", "from_date", "to_date"]
        )
        
        return [sg.name for sg in student_groups]
        
    except Exception as e:
        frappe.log_error(f"Error fetching student groups for customer {customer}: {str(e)}")
        return []

@frappe.whitelist()
def fetch_students_from_sg(customer, student_group):
    """Fetch students from selected Student Groups"""
    try:
        students_data = []
        
        # Debug logging
        frappe.logger().info(f"fetch_students_from_sg called with customer: {customer}")
        frappe.logger().info(f"fetch_students_from_sg called with student_group: {student_group}")
        frappe.logger().info(f"student_group type: {type(student_group)}")
        
        # Handle different input formats
        if isinstance(student_group, str):
            # If it's a string, try to parse it as JSON or split by comma
            import json
            try:
                # Try to parse as JSON first
                student_group = json.loads(student_group)
            except:
                # If not JSON, split by comma and clean up
                student_group = [sg.strip().replace('"', '').replace('[', '').replace(']', '') 
                               for sg in student_group.split(',') if sg.strip()]
        
        # Ensure student_group is a list
        if not isinstance(student_group, list):
            student_group = [student_group]
        
        frappe.logger().info(f"Processed student_group list: {student_group}")
        
        for sg_name in student_group:
            if not sg_name:
                continue
                
            # Clean up the student group name
            sg_name = str(sg_name).strip().replace('"', '').replace('[', '').replace(']', '')
            
            frappe.logger().info(f"Processing student group: {sg_name}")
            
            # Check if the Student Group exists
            if not frappe.db.exists("Student Group", sg_name):
                frappe.logger().error(f"Student Group {sg_name} does not exist!")
                continue
                
            # Get the Student Group
            sg_doc = frappe.get_doc("Student Group", sg_name)
            
            # Get students from the Student Group
            for student_row in sg_doc.students:
                student_data = {
                    "student": student_row.student,
                    "student_name": student_row.student_name,
                    "course_name": sg_doc.course,
                    "student_group": sg_name,
                    "start_date": sg_doc.from_date,
                    "end_date": sg_doc.to_date
                }
                students_data.append(student_data)
        
        frappe.logger().info(f"Returning {len(students_data)} students")
        return students_data
        
    except Exception as e:
        frappe.logger().error(f"Error fetching students from student groups: {str(e)}")
        frappe.throw(f"Error fetching students: {str(e)}")
        return [] 