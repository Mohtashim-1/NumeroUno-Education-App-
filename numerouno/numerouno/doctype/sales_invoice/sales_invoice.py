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
def fetch_students_from_sg(customer, student_group, exclude_invoiced=True):
    """Fetch students from selected Student Groups
    
    Args:
        customer: Customer name
        student_group: Student group name(s) - can be string, list, or JSON string
        exclude_invoiced: If True, exclude students that are already in submitted invoices (default: True)
    """
    try:
        students_data = []
        
        # Debug logging
        frappe.logger().info(f"fetch_students_from_sg called with customer: {customer}")
        frappe.logger().info(f"fetch_students_from_sg called with student_group: {student_group}")
        frappe.logger().info(f"student_group type: {type(student_group)}")
        
        # Get already invoiced students if exclude_invoiced is True
        # We'll build a set of (student, student_group) tuples to check for duplicates
        invoiced_students_by_group = set()
        if exclude_invoiced:
            # Get all submitted Sales Invoices for this customer
            submitted_invoices = frappe.get_all(
                "Sales Invoice",
                filters={
                    "customer": customer,
                    "docstatus": 1  # Only submitted invoices
                },
                fields=["name"]
            )
            
            if submitted_invoices:
                invoice_names = [inv.name for inv in submitted_invoices]
                
                # Get all students from submitted invoices with their student groups
                invoiced_student_records = frappe.get_all(
                    "Sales Invoice Student",
                    filters={
                        "parent": ["in", invoice_names]
                    },
                    fields=["student", "student_group"]
                )
                
                # Create set of (student, student_group) tuples
                invoiced_students_by_group = {
                    (record.student, record.student_group) 
                    for record in invoiced_student_records 
                    if record.student and record.student_group
                }
                frappe.logger().info(f"Found {len(invoiced_students_by_group)} already invoiced student-group combinations")
        
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
                # Skip if student is already invoiced for this student group and exclude_invoiced is True
                if exclude_invoiced and (student_row.student, sg_name) in invoiced_students_by_group:
                    frappe.logger().info(f"Skipping already invoiced student: {student_row.student} for group: {sg_name}")
                    continue
                
                student_data = {
                    "student": student_row.student,
                    "student_name": student_row.student_name,
                    "course_name": sg_doc.course,
                    "student_group": sg_name,
                    "start_date": sg_doc.from_date,
                    "end_date": sg_doc.to_date
                }
                students_data.append(student_data)
        
        frappe.logger().info(f"Returning {len(students_data)} students (after excluding invoiced)")
        return students_data
        
    except Exception as e:
        frappe.logger().error(f"Error fetching students from student groups: {str(e)}")
        frappe.throw(f"Error fetching students: {str(e)}")
        return [] 