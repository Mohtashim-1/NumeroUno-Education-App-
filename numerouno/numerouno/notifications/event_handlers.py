import frappe
from frappe import _
from .notification_manager import NotificationManager
from .notification_config import NotificationConfig

def handle_student_welcome(doc, method):
    """Handle welcome email for new students"""
    try:
        if method == "after_insert":
            # Get student details
            student_name = doc.student_name or doc.name
            email = doc.student_email_id or frappe.db.get_value("User", doc.user, "email")
            program_name = doc.program or "Training Program"
            
            if email:
                NotificationManager.send_welcome_email(student_name, email, program_name)
                print(f"Welcome email sent to new student: {student_name}")
                
    except Exception as e:
        print(f"Failed to send welcome email: {str(e)}")

def handle_student_group_creation(doc, method):
    """Handle notifications when student group is created"""
    try:
        if method == "after_insert":
            # Send notification to management about new student group
            student_count = len(doc.students) if hasattr(doc, 'students') else 0
            program_name = doc.program or "Training Program"
            
            # Get management emails
            management_emails = NotificationConfig.get_management_emails()
            
            if management_emails:
                subject = f"New Student Group Created - {doc.student_group_name}"
                
                body = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <div style="background-color: #d4edda; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                        <h3 style="color: #155724; margin: 0;">📚 New Student Group Created</h3>
                    </div>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h4>Group Details:</h4>
                        <ul>
                            <li><strong>Group Name:</strong> {doc.student_group_name}</li>
                            <li><strong>Program:</strong> {program_name}</li>
                            <li><strong>Student Count:</strong> {student_count}</li>
                            <li><strong>Created By:</strong> {doc.owner}</li>
                            <li><strong>Creation Date:</strong> {doc.creation}</li>
                        </ul>
                    </div>
                    
                    <p>Please review and take necessary action for this new student group.</p>
                    
                    <p>Best regards,<br>
                    <strong>Numero Uno System</strong></p>
                </div>
                """
                
                frappe.sendmail(
                    recipients=management_emails,
                    subject=subject,
                    message=body,
                    now=True
                )
                
                print(f"Student group creation notification sent for: {doc.student_group_name}")
            
            # Send notification to assigned instructors
            handle_instructor_assignment_to_student_group(doc)
                
    except Exception as e:
        print(f"Failed to send student group creation notification: {str(e)}")

def handle_instructor_assignment_to_student_group(doc):
    """Handle notifications when instructors are assigned to student groups"""
    try:
        # Check if instructors are assigned to this student group
        if hasattr(doc, 'instructors') and doc.instructors:
            for instructor_row in doc.instructors:
                instructor_name = instructor_row.instructor_name or instructor_row.instructor
                instructor_email = frappe.db.get_value("Instructor", instructor_row.instructor, "custom_email")
                
                if instructor_email:
                    student_count = len(doc.students) if hasattr(doc, 'students') else 0
                    program_name = doc.program or "Training Program"
                    course_name = doc.course or "Training Course"
                    
                    subject = f"New Student Group Assignment - {doc.student_group_name}"
                    
                    body = f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                        <div style="background-color: #d1ecf1; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                            <h3 style="color: #0c5460; margin: 0;">👨‍🏫 New Student Group Assignment</h3>
                        </div>
                        
                        <p>Dear <strong>{instructor_name}</strong>,</p>
                        
                        <p>You have been assigned as an instructor to a new student group.</p>
                        
                        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <h4>Assignment Details:</h4>
                            <ul>
                                <li><strong>Student Group:</strong> {doc.student_group_name}</li>
                                <li><strong>Program:</strong> {program_name}</li>
                                <li><strong>Course:</strong> {course_name}</li>
                                <li><strong>Student Count:</strong> {student_count}</li>
                                <li><strong>Academic Year:</strong> {doc.academic_year or 'N/A'}</li>
                                <li><strong>Academic Term:</strong> {doc.academic_term or 'N/A'}</li>
                                <li><strong>Group Based On:</strong> {doc.group_based_on or 'N/A'}</li>
                            </ul>
                        </div>
                        
                        <p>Please review the student group details and prepare for your teaching assignment.</p>
                        
                        <p>You can view the Student Group details by clicking the link below:</p>
                        <p><a href="{frappe.utils.get_url('/app/student-group/{0}'.format(doc.name))}">View Student Group</a></p>
                        
                        <p>Best regards,<br>
                        <strong>Numero Uno Training Team</strong></p>
                    </div>
                    """
                    
                    frappe.sendmail(
                        recipients=[instructor_email],
                        subject=subject,
                        message=body,
                        now=True
                    )
                    
                    print(f"Instructor assignment notification sent to: {instructor_name} ({instructor_email})")
                else:
                    print(f"No email found for instructor: {instructor_name}")
        else:
            print(f"No instructors assigned to student group: {doc.student_group_name}")
            
    except Exception as e:
        print(f"Failed to send instructor assignment notification: {str(e)}")

def handle_student_group_instructor_update(doc, method):
    """Handle notifications when instructors are added to existing student groups"""
    try:
        if method == "on_update":
            # Get the previous version of the document to compare
            doc_before = doc.get_doc_before_save()
            
            if doc_before:
                # Get current and previous instructor lists
                current_instructors = set()
                previous_instructors = set()
                
                if hasattr(doc, 'instructors') and doc.instructors:
                    current_instructors = {row.instructor for row in doc.instructors}
                
                if hasattr(doc_before, 'instructors') and doc_before.instructors:
                    previous_instructors = {row.instructor for row in doc_before.instructors}
                
                # Find newly added instructors
                new_instructors = current_instructors - previous_instructors
                
                if new_instructors:
                    print(f"New instructors detected: {new_instructors}")
                    
                    # Send notifications to newly added instructors
                    for instructor_id in new_instructors:
                        instructor_name = frappe.db.get_value("Instructor", instructor_id, "instructor_name") or instructor_id
                        instructor_email = frappe.db.get_value("Instructor", instructor_id, "custom_email")
                        
                        if instructor_email:
                            student_count = len(doc.students) if hasattr(doc, 'students') else 0
                            program_name = doc.program or "Training Program"
                            course_name = doc.course or "Training Course"
                            
                            subject = f"Student Group Assignment - {doc.student_group_name}"
                            
                            body = f"""
                            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                                <div style="background-color: #d1ecf1; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                                    <h3 style="color: #0c5460; margin: 0;">👨‍🏫 New Student Group Assignment</h3>
                                </div>
                                
                                <p>Dear <strong>{instructor_name}</strong>,</p>
                                
                                <p>You have been assigned as an instructor to an existing student group.</p>
                                
                                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                                    <h4>Assignment Details:</h4>
                                    <ul>
                                        <li><strong>Student Group:</strong> {doc.student_group_name}</li>
                                        <li><strong>Program:</strong> {program_name}</li>
                                        <li><strong>Course:</strong> {course_name}</li>
                                        <li><strong>Student Count:</strong> {student_count}</li>
                                        <li><strong>Academic Year:</strong> {doc.academic_year or 'N/A'}</li>
                                        <li><strong>Academic Term:</strong> {doc.academic_term or 'N/A'}</li>
                                        <li><strong>Group Based On:</strong> {doc.group_based_on or 'N/A'}</li>
                                    </ul>
                                </div>
                                
                                <p>Please review the student group details and prepare for your teaching assignment.</p>
                                
                                <p>You can view the Student Group details by clicking the link below:</p>
                                <p><a href="{frappe.utils.get_url('/app/student-group/{0}'.format(doc.name))}">View Student Group</a></p>
                                
                                <p>Best regards,<br>
                                <strong>Numero Uno Training Team</strong></p>
                            </div>
                            """
                            
                            frappe.sendmail(
                                recipients=[instructor_email],
                                subject=subject,
                                message=body,
                                now=True
                            )
                            
                            print(f"Instructor assignment notification sent to: {instructor_name} ({instructor_email})")
                        else:
                            print(f"No email found for instructor: {instructor_name}")
                else:
                    print(f"No new instructors added to student group: {doc.student_group_name}")
            else:
                print(f"Could not get previous document state for: {doc.name}")
                
    except Exception as e:
        print(f"Failed to send instructor assignment update notification: {str(e)}")

def handle_cash_assignment(doc, method):
    """Handle cash assignment notification"""
    try:
        if doc.payment_method == "Cash" and method == "after_insert":
            student_name = doc.student_name
            email = doc.email or frappe.db.get_value("User", doc.user, "email")
            program_name = doc.program
            instructor_name = doc.instructor or "Assigned Instructor"
            
            if email:
                NotificationManager.send_cash_assignment_notification(
                    student_name, email, program_name, instructor_name
                )
                
    except Exception as e:
        print(f"Failed to send cash assignment notification: {str(e)}")

def handle_sales_order_creation(doc, method):
    """Handle notifications when sales order is created"""
    try:
        if method == "after_insert":
            print(f"Sales order creation handler triggered for: {doc.name}")
            
            # Send notification to sales team about new order
            sales_emails = NotificationConfig.get_sales_emails()
            print(f"Sales emails found: {sales_emails}")
            
            if sales_emails:
                # Get program details from items
                program_details = []
                total_students = 0
                
                if hasattr(doc, 'items') and doc.items:
                    for item in doc.items:
                        program_details.append({
                            'program_name': item.item_name,
                            'qty': item.qty,
                            'rate': item.rate,
                            'amount': item.amount
                        })
                        total_students += item.qty
                
                # Create program list HTML
                program_list_html = ""
                if program_details:
                    for program in program_details:
                        program_list_html += f"""
                        <li><strong>Program:</strong> {program['program_name']}</li>
                        <li><strong>Students:</strong> {program['qty']}</li>
                        <li><strong>Rate:</strong> {program['rate']}</li>
                        <li><strong>Amount:</strong> {program['amount']}</li>
                        <hr style="margin: 10px 0;">
                        """
                else:
                    program_list_html = "<li><strong>Program:</strong> N/A</li>"
                
                subject = f"New Sales Order Created - {doc.name}"
                
                body = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <div style="background-color: #d1ecf1; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                        <h3 style="color: #0c5460; margin: 0;">🛒 New Sales Order</h3>
                    </div>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h4>Order Details:</h4>
                        <ul>
                            <li><strong>Order Number:</strong> {doc.name}</li>
                            <li><strong>Customer:</strong> {doc.customer}</li>
                            <li><strong>Total Students:</strong> {total_students}</li>
                            <li><strong>Total Amount:</strong> {doc.grand_total}</li>
                            <li><strong>Payment Method:</strong> {doc.payment_method or 'N/A'}</li>
                            <li><strong>Created By:</strong> {doc.owner}</li>
                        </ul>
                        
                        <h4>Program Details:</h4>
                        <ul>
                            {program_list_html}
                        </ul>
                    </div>
                    
                    <p>Please review and process this new sales order.</p>
                    
                    <p>Best regards,<br>
                    <strong>Numero Uno System</strong></p>
                </div>
                """
                
                frappe.sendmail(
                    recipients=sales_emails,
                    subject=subject,
                    message=body,
                    now=True
                )
                
                print(f"Sales order creation notification sent for: {doc.name}")
            else:
                print(f"No sales emails found for sales order: {doc.name}")
                
    except Exception as e:
        print(f"Failed to send sales order creation notification: {str(e)}")
        print(f"Exception details: {frappe.get_traceback()}")

def handle_missing_po(doc, method):
    """Handle missing PO notification"""
    try:
        if method == "on_update":
            # Check if PO is missing
            if not doc.po_no or doc.po_no == "":
                # Get program name from items
                program_names = []
                if hasattr(doc, 'items') and doc.items:
                    for item in doc.items:
                        program_names.append(item.item_name)
                
                program_name = ", ".join(program_names) if program_names else "Training Program"
                customer_name = doc.customer
                sales_order_name = doc.name
                
                NotificationManager.send_missing_po_notification(
                    program_name, customer_name, sales_order_name
                )
                
    except Exception as e:
        print(f"Failed to send missing PO notification: {str(e)}")

def handle_instructor_assignment(doc, method):
    """Handle instructor task assignment notification"""
    try:
        if method == "after_insert":
            instructor_name = doc.instructor_name or doc.instructor
            email = frappe.db.get_value("User", doc.instructor, "email")
            
            if email:
                task_details = {
                    'program_name': doc.program,
                    'course_name': doc.course,
                    'start_date': doc.start_date,
                    'end_date': doc.end_date,
                    'location': doc.location or "Training Center",
                    'student_count': len(doc.students) if hasattr(doc, 'students') else 0
                }
                
                NotificationManager.send_instructor_task_assignment(
                    instructor_name, email, task_details
                )
                
    except Exception as e:
        print(f"Failed to send instructor assignment notification: {str(e)}")

def handle_assessment_pending(doc, method):
    """Handle assessment pending notification"""
    try:
        if method == "on_update":
            # Check if assessment is pending (no grade assigned)
            if not doc.grade and doc.docstatus == 0:
                student_name = doc.student_name
                email = frappe.db.get_value("Student", doc.student, "student_email_id")
                program_name = doc.program
                assessment_plan = doc.assessment_plan
                
                if email:
                    NotificationManager.send_assessment_pending_notification(
                        student_name, email, program_name, assessment_plan
                    )
                    
    except Exception as e:
        print(f"Failed to send assessment pending notification: {str(e)}")

def handle_student_absence(doc, method):
    """Handle student absence notification"""
    try:
        if method == "after_insert":
            print(f"Student absence handler triggered for: {doc.name}")
            print(f"Student status: {doc.status}")
            
            # Check if student is absent
            if doc.status == "Absent":
                student_name = doc.student_name
                email = frappe.db.get_value("Student", doc.student, "student_email_id")
                
                # Get program name from student group or course schedule
                program_name = "Training Program"
                if doc.student_group:
                    program_name = frappe.db.get_value("Student Group", doc.student_group, "program") or "Training Program"
                elif doc.course_schedule:
                    course = frappe.db.get_value("Course Schedule", doc.course_schedule, "course")
                    if course:
                        program_name = frappe.db.get_value("Course", course, "program") or "Training Program"
                
                absent_date = doc.date
                instructor_name = "Instructor"
                
                # Get instructor from student group or course schedule
                if doc.student_group:
                    instructors = frappe.get_all("Student Group Instructor", 
                        filters={"parent": doc.student_group},
                        fields=["instructor"]
                    )
                    if instructors:
                        instructor_name = frappe.db.get_value("Instructor", instructors[0].instructor, "instructor_name") or "Instructor"
                elif doc.course_schedule:
                    instructor = frappe.db.get_value("Course Schedule", doc.course_schedule, "instructor")
                    if instructor:
                        instructor_name = frappe.db.get_value("Instructor", instructor, "instructor_name") or "Instructor"
                
                print(f"Student email found: {email}")
                print(f"Program name: {program_name}")
                print(f"Instructor name: {instructor_name}")
                
                if email:
                    NotificationManager.send_student_absent_notification(
                        student_name, email, program_name, absent_date, instructor_name
                    )
                    print(f"Student absence notification sent for: {student_name}")
                else:
                    print(f"No email found for student: {student_name}")
            else:
                print(f"Student not absent, status: {doc.status}")
                    
    except Exception as e:
        print(f"Failed to send student absence notification: {str(e)}")
        print(f"Exception details: {frappe.get_traceback()}")

def handle_attendance_eligibility(doc, method):
    """Handle attendance eligibility notification"""
    try:
        if method == "on_update":
            # Calculate attendance percentage
            student = doc.student
            student_group = doc.student_group
            
            # Get total sessions and attended sessions
            total_sessions = frappe.db.count("Student Attendance", {
                "student": student,
                "student_group": student_group
            })
            
            attended_sessions = frappe.db.count("Student Attendance", {
                "student": student,
                "student_group": student_group,
                "status": "Present"
            })
            
            if total_sessions > 0:
                attendance_percentage = (attended_sessions / total_sessions) * 100
                required_percentage = 80  # Default requirement
                
                # Check if student is eligible for assessment
                if attendance_percentage < required_percentage:
                    student_name = doc.student_name
                    email = frappe.db.get_value("Student", doc.student, "student_email_id")
                    
                    # Get program name from student group
                    program_name = "Training Program"
                    if student_group:
                        program_name = frappe.db.get_value("Student Group", student_group, "program") or "Training Program"
                    
                    if email:
                        NotificationManager.send_attendance_eligibility_notification(
                            student_name, email, program_name, 
                            round(attendance_percentage, 1), required_percentage
                        )
                        
    except Exception as e:
        print(f"Failed to send attendance eligibility notification: {str(e)}")

def handle_unpaid_students(doc, method):
    """Handle unpaid students notification"""
    try:
        if method == "on_update":
            # Check for unpaid students in the group
            unpaid_students = []
            
            if hasattr(doc, 'students') and doc.students:
                for student in doc.students:
                    if not student.get("custom_invoiced"):
                        unpaid_students.append({
                            "student": student.student,
                            "student_name": student.student_name,
                            "group_roll_number": student.group_roll_number
                        })
            
            if unpaid_students:
                NotificationManager.send_unpaid_student_report(
                    doc.name, doc.student_group_name, unpaid_students
                )
                
    except Exception as e:
        print(f"Failed to send unpaid students notification: {str(e)}")

def handle_assessment_creation(doc, method):
    """Handle notifications when assessment result is created"""
    try:
        if method == "after_insert":
            print(f"Assessment creation handler triggered for: {doc.name}")
            
            # Send notification to instructor about new assessment
            instructor_emails = NotificationConfig.get_instructor_emails()
            print(f"Instructor emails found: {instructor_emails}")
            
            if instructor_emails:
                # Get assessment plan details
                assessment_plan_name = doc.assessment_plan or "N/A"
                assessment_plan_title = frappe.db.get_value("Assessment Plan", doc.assessment_plan, "assessment_name") if doc.assessment_plan else "N/A"
                
                subject = f"New Assessment Result - {doc.student_name}"
                
                body = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                        <h3 style="color: #856404; margin: 0;">📝 New Assessment Result</h3>
                    </div>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h4>Assessment Details:</h4>
                        <ul>
                            <li><strong>Student:</strong> {doc.student_name}</li>
                            <li><strong>Program:</strong> {doc.program or 'N/A'}</li>
                            <li><strong>Course:</strong> {doc.course or 'N/A'}</li>
                            <li><strong>Assessment Plan:</strong> {assessment_plan_title}</li>
                            <li><strong>Total Score:</strong> {doc.total_score or 'N/A'}</li>
                            <li><strong>Grade:</strong> {doc.grade or 'N/A'}</li>
                            <li><strong>Created By:</strong> {doc.owner}</li>
                        </ul>
                    </div>
                    
                    <p>Please review this new assessment result.</p>
                    
                    <p>Best regards,<br>
                    <strong>Numero Uno System</strong></p>
                </div>
                """
                
                frappe.sendmail(
                    recipients=instructor_emails,
                    subject=subject,
                    message=body,
                    now=True
                )
                
                print(f"Assessment creation notification sent for: {doc.student_name}")
            else:
                print(f"No instructor emails found for assessment: {doc.name}")
                
    except Exception as e:
        print(f"Failed to send assessment creation notification: {str(e)}")
        print(f"Exception details: {frappe.get_traceback()}")

# Register event handlers
def register_notification_handlers():
    """Register all notification event handlers"""
    handlers = {
        "Student": [handle_student_welcome],
        "Student Group": [handle_unpaid_students, handle_student_group_creation],
        "Sales Order": [handle_missing_po, handle_sales_order_creation],
        "Assessment Result": [handle_assessment_pending, handle_assessment_creation],
        "Student Attendance": [handle_student_absence, handle_attendance_eligibility],
        "Instructor Assignment": [handle_instructor_assignment],
        "Cash Assignment": [handle_cash_assignment]
    }
    
    return handlers 