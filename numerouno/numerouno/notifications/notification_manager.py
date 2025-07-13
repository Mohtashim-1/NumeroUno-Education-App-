import frappe
from frappe import _
from frappe.utils import nowdate, getdate, add_days
from frappe.utils.background_jobs import enqueue
from frappe.utils import get_url
import json

class NotificationManager:
    """Centralized notification manager for all system notifications"""
    
    @staticmethod
    def send_welcome_email(student_name, email, program_name):
        """Send welcome email to new students"""
        try:
            subject = f"Welcome to {program_name} - Numero Uno Training"
            
            body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background-color: #f8f9fa; padding: 20px; text-align: center;">
                    <h2 style="color: #2c3e50;">Welcome to Numero Uno Training!</h2>
                </div>
                
                <div style="padding: 20px;">
                    <p>Dear <strong>{student_name}</strong>,</p>
                    
                    <p>Welcome to <strong>{program_name}</strong>! We're excited to have you join our training program.</p>
                    
                    <div style="background-color: #e8f5e8; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="color: #27ae60; margin-top: 0;">What's Next?</h3>
                        <ul>
                            <li>Complete your registration process</li>
                            <li>Review your course schedule</li>
                            <li>Prepare for your first session</li>
                            <li>Access your student portal</li>
                        </ul>
                    </div>
                    
                    <p>If you have any questions, please don't hesitate to contact us:</p>
                    <ul>
                        <li>Email: training@nutc.ae</li>
                        <li>Phone: 050 500 2620</li>
                        <li>Website: www.nutc.ae</li>
                    </ul>
                    
                    <p>Best regards,<br>
                    <strong>Numero Uno Training Team</strong></p>
                </div>
            </div>
            """
            
            frappe.sendmail(
                recipients=[email],
                subject=subject,
                message=body,
                now=True
            )
            
            frappe.logger().info(f"Welcome email sent to {student_name} ({email})")
            
        except Exception as e:
            frappe.logger().error(f"Failed to send welcome email: {str(e)}")

    @staticmethod
    def send_unpaid_student_report(student_group_name, student_group_title, unpaid_students):
        """Send unpaid student report to accounts team"""
        try:
            # Get accounts team emails
            accounts_users = frappe.get_all(
                "Has Role",
                filters={"role": ["in", ["Accounts User", "Accounts Manager"]]},
                fields=["parent"]
            )
            
            email_addresses = []
            for user in accounts_users:
                email = frappe.db.get_value("User", user.parent, "email")
                if email:
                    email_addresses.append(email)
            
            if not email_addresses:
                return
            
            subject = f"Unpaid Students Report - {student_group_title}"
            
            # Create student list
            student_list = ""
            for student in unpaid_students:
                student_list += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{student.get('student_name', 'N/A')}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{student.get('group_roll_number', 'N/A')}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{student.get('student', 'N/A')}</td>
                </tr>
                """
            
            body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
                <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                    <h3 style="color: #856404; margin: 0;">⚠️ Unpaid Students Alert</h3>
                </div>
                
                <p><strong>Student Group:</strong> {student_group_title}</p>
                <p><strong>Total Unpaid Students:</strong> {len(unpaid_students)}</p>
                
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                    <thead>
                        <tr style="background-color: #f8f9fa;">
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Student Name</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Roll Number</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Student ID</th>
                        </tr>
                    </thead>
                    <tbody>
                        {student_list}
                    </tbody>
                </table>
                
                <p>Please review and take necessary action to ensure proper invoicing.</p>
                
                <p>Best regards,<br>
                <strong>Numero Uno System</strong></p>
            </div>
            """
            
            frappe.sendmail(
                recipients=email_addresses,
                subject=subject,
                message=body,
                now=True
            )
            
            frappe.logger().info(f"Unpaid student report sent for {student_group_title}")
            
        except Exception as e:
            frappe.logger().error(f"Failed to send unpaid student report: {str(e)}")

    @staticmethod
    def send_cash_assignment_notification(student_name, email, program_name, instructor_name):
        """Send notification when student is assigned to cash payment"""
        try:
            subject = f"Cash Payment Assignment - {program_name}"
            
            body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background-color: #d1ecf1; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                    <h3 style="color: #0c5460; margin: 0;">💰 Cash Payment Assignment</h3>
                </div>
                
                <p>Dear <strong>{student_name}</strong>,</p>
                
                <p>You have been assigned to <strong>{program_name}</strong> with cash payment option.</p>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h4>Payment Details:</h4>
                    <ul>
                        <li><strong>Payment Method:</strong> Cash</li>
                        <li><strong>Instructor:</strong> {instructor_name}</li>
                        <li><strong>Program:</strong> {program_name}</li>
                    </ul>
                </div>
                
                <p>Please ensure you have the required payment ready for your first session.</p>
                
                <p>Best regards,<br>
                <strong>Numero Uno Training Team</strong></p>
            </div>
            """
            
            frappe.sendmail(
                recipients=[email],
                subject=subject,
                message=body,
                now=True
            )
            
            frappe.logger().info(f"Cash assignment notification sent to {student_name}")
            
        except Exception as e:
            frappe.logger().error(f"Failed to send cash assignment notification: {str(e)}")

    @staticmethod
    def send_missing_po_notification(program_name, customer_name, sales_order_name):
        """Send notification for missing Purchase Order"""
        try:
            # Get relevant users (Sales, Accounts, Management)
            relevant_users = frappe.get_all(
                "Has Role",
                filters={"role": ["in", ["Sales User", "Sales Manager", "Accounts Manager", "System Manager"]]},
                fields=["parent"]
            )
            
            email_addresses = []
            for user in relevant_users:
                email = frappe.db.get_value("User", user.parent, "email")
                if email:
                    email_addresses.append(email)
            
            if not email_addresses:
                return
            
            subject = f"Missing Purchase Order Alert - {program_name}"
            
            body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto;">
                <div style="background-color: #f8d7da; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                    <h3 style="color: #721c24; margin: 0;">🚨 Missing Purchase Order</h3>
                </div>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h4>Program Details:</h4>
                    <ul>
                        <li><strong>Program:</strong> {program_name}</li>
                        <li><strong>Customer:</strong> {customer_name}</li>
                        <li><strong>Sales Order:</strong> {sales_order_name}</li>
                        <li><strong>Status:</strong> Missing Purchase Order</li>
                    </ul>
                </div>
                
                <p>This program requires a Purchase Order to proceed. Please contact the customer to obtain the necessary PO.</p>
                
                <p>Best regards,<br>
                <strong>Numero Uno System</strong></p>
            </div>
            """
            
            frappe.sendmail(
                recipients=email_addresses,
                subject=subject,
                message=body,
                now=True
            )
            
            frappe.logger().info(f"Missing PO notification sent for {program_name}")
            
        except Exception as e:
            frappe.logger().error(f"Failed to send missing PO notification: {str(e)}")

    @staticmethod
    def send_instructor_task_assignment(instructor_name, email, task_details):
        """Send notification when instructor is assigned to a task"""
        try:
            subject = f"New Task Assignment - {task_details.get('program_name', 'Training Program')}"
            
            body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background-color: #d4edda; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                    <h3 style="color: #155724; margin: 0;">📋 New Task Assignment</h3>
                </div>
                
                <p>Dear <strong>{instructor_name}</strong>,</p>
                
                <p>You have been assigned to a new training task.</p>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h4>Task Details:</h4>
                    <ul>
                        <li><strong>Program:</strong> {task_details.get('program_name', 'N/A')}</li>
                        <li><strong>Course:</strong> {task_details.get('course_name', 'N/A')}</li>
                        <li><strong>Start Date:</strong> {task_details.get('start_date', 'N/A')}</li>
                        <li><strong>End Date:</strong> {task_details.get('end_date', 'N/A')}</li>
                        <li><strong>Location:</strong> {task_details.get('location', 'N/A')}</li>
                        <li><strong>Students:</strong> {task_details.get('student_count', 0)}</li>
                    </ul>
                </div>
                
                <p>Please review the task details and prepare accordingly.</p>
                
                <p>Best regards,<br>
                <strong>Numero Uno Training Team</strong></p>
            </div>
            """
            
            frappe.sendmail(
                recipients=[email],
                subject=subject,
                message=body,
                now=True
            )
            
            frappe.logger().info(f"Instructor task assignment sent to {instructor_name}")
            
        except Exception as e:
            frappe.logger().error(f"Failed to send instructor task assignment: {str(e)}")

    @staticmethod
    def send_assessment_pending_notification(student_name, email, program_name, assessment_plan):
        """Send notification for pending assessment"""
        try:
            subject = f"Assessment Pending - {program_name}"
            
            body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                    <h3 style="color: #856404; margin: 0;">📝 Assessment Pending</h3>
                </div>
                
                <p>Dear <strong>{student_name}</strong>,</p>
                
                <p>You have a pending assessment for <strong>{program_name}</strong>.</p>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h4>Assessment Details:</h4>
                    <ul>
                        <li><strong>Program:</strong> {program_name}</li>
                        <li><strong>Assessment Plan:</strong> {assessment_plan}</li>
                        <li><strong>Status:</strong> Pending</li>
                    </ul>
                </div>
                
                <p>Please complete your assessment to proceed with your certification.</p>
                
                <p>Best regards,<br>
                <strong>Numero Uno Training Team</strong></p>
            </div>
            """
            
            frappe.sendmail(
                recipients=[email],
                subject=subject,
                message=body,
                now=True
            )
            
            frappe.logger().info(f"Assessment pending notification sent to {student_name}")
            
        except Exception as e:
            frappe.logger().error(f"Failed to send assessment pending notification: {str(e)}")

    @staticmethod
    def send_student_absent_notification(student_name, email, program_name, absent_date, instructor_name):
        """Send notification for student absence"""
        try:
            subject = f"Absence Notification - {program_name}"
            
            body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background-color: #f8d7da; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                    <h3 style="color: #721c24; margin: 0;">❌ Absence Recorded</h3>
                </div>
                
                <p>Dear <strong>{student_name}</strong>,</p>
                
                <p>This is to inform you that you were marked absent for <strong>{program_name}</strong> on <strong>{absent_date}</strong>.</p>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h4>Absence Details:</h4>
                    <ul>
                        <li><strong>Program:</strong> {program_name}</li>
                        <li><strong>Date:</strong> {absent_date}</li>
                        <li><strong>Instructor:</strong> {instructor_name}</li>
                    </ul>
                </div>
                
                <p>Please ensure regular attendance to maintain your progress in the program.</p>
                
                <p>Best regards,<br>
                <strong>Numero Uno Training Team</strong></p>
            </div>
            """
            
            frappe.sendmail(
                recipients=[email],
                subject=subject,
                message=body,
                now=True
            )
            
            frappe.logger().info(f"Student absent notification sent to {student_name}")
            
        except Exception as e:
            frappe.logger().error(f"Failed to send student absent notification: {str(e)}")

    @staticmethod
    def send_attendance_eligibility_notification(student_name, email, program_name, attendance_percentage, required_percentage):
        """Send notification when student is not eligible for assessment due to attendance"""
        try:
            subject = f"Assessment Eligibility Alert - {program_name}"
            
            body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background-color: #f8d7da; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                    <h3 style="color: #721c24; margin: 0;">⚠️ Assessment Not Eligible</h3>
                </div>
                
                <p>Dear <strong>{student_name}</strong>,</p>
                
                <p>You are currently not eligible to take the assessment for <strong>{program_name}</strong> due to insufficient attendance.</p>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h4>Attendance Details:</h4>
                    <ul>
                        <li><strong>Program:</strong> {program_name}</li>
                        <li><strong>Your Attendance:</strong> {attendance_percentage}%</li>
                        <li><strong>Required Attendance:</strong> {required_percentage}%</li>
                        <li><strong>Status:</strong> Not Eligible for Assessment</li>
                    </ul>
                </div>
                
                <p>Please improve your attendance to become eligible for the assessment.</p>
                
                <p>Best regards,<br>
                <strong>Numero Uno Training Team</strong></p>
            </div>
            """
            
            frappe.sendmail(
                recipients=[email],
                subject=subject,
                message=body,
                now=True
            )
            
            frappe.logger().info(f"Attendance eligibility notification sent to {student_name}")
            
        except Exception as e:
            frappe.logger().error(f"Failed to send attendance eligibility notification: {str(e)}")

    @staticmethod
    def send_daily_consolidated_report():
        """Send daily consolidated report of all notifications"""
        try:
            # Get all pending notifications for the day
            today = nowdate()
            
            # Collect data for different notification types
            notifications = {
                'unpaid_students': [],
                'missing_pos': [],
                'pending_assessments': [],
                'absent_students': [],
                'ineligible_students': []
            }
            
            # Get unpaid students
            unpaid_students = frappe.db.sql("""
                SELECT 
                    sg.student_group_name,
                    sgs.student_name,
                    sgs.student
                FROM `tabStudent Group` sg
                JOIN `tabStudent Group Student` sgs ON sgs.parent = sg.name
                WHERE sgs.custom_invoiced = 0 OR sgs.custom_invoiced IS NULL
            """, as_dict=True)
            
            notifications['unpaid_students'] = unpaid_students
            
            # Get missing POs
            missing_pos = frappe.db.sql("""
                SELECT 
                    so.name,
                    so.customer,
                    so.program_name
                FROM `tabSales Order` so
                WHERE so.po_no IS NULL OR so.po_no = ''
                AND so.docstatus = 1
            """, as_dict=True)
            
            notifications['missing_pos'] = missing_pos
            
            # Get pending assessments
            pending_assessments = frappe.db.sql("""
                SELECT 
                    ar.student_name,
                    ar.program,
                    ar.assessment_plan
                FROM `tabAssessment Result` ar
                WHERE ar.docstatus = 0
                AND ar.grade IS NULL
            """, as_dict=True)
            
            notifications['pending_assessments'] = pending_assessments
            
            # Send consolidated report
            if any(notifications.values()):
                NotificationManager.send_consolidated_report(notifications)
            
        except Exception as e:
            frappe.logger().error(f"Failed to send daily consolidated report: {str(e)}")

    @staticmethod
    def send_consolidated_report(notifications):
        """Send consolidated daily report"""
        try:
            # Get management team emails
            management_users = frappe.get_all(
                "Has Role",
                filters={"role": ["in", ["System Manager", "Accounts Manager", "Sales Manager"]]},
                fields=["parent"]
            )
            
            email_addresses = []
            for user in management_users:
                email = frappe.db.get_value("User", user.parent, "email")
                if email:
                    email_addresses.append(email)
            
            if not email_addresses:
                return
            
            subject = f"Daily System Report - {nowdate()}"
            
            # Create report content
            report_content = ""
            
            if notifications['unpaid_students']:
                report_content += f"""
                <h3 style="color: #dc3545;">💰 Unpaid Students ({len(notifications['unpaid_students'])})</h3>
                <ul>
                """
                for student in notifications['unpaid_students'][:5]:  # Show first 5
                    report_content += f"<li>{student['student_name']} - {student['student_group_name']}</li>"
                if len(notifications['unpaid_students']) > 5:
                    report_content += f"<li>... and {len(notifications['unpaid_students']) - 5} more</li>"
                report_content += "</ul>"
            
            if notifications['missing_pos']:
                report_content += f"""
                <h3 style="color: #fd7e14;">📋 Missing POs ({len(notifications['missing_pos'])})</h3>
                <ul>
                """
                for po in notifications['missing_pos'][:5]:
                    report_content += f"<li>{po['customer']} - {po['program_name']}</li>"
                if len(notifications['missing_pos']) > 5:
                    report_content += f"<li>... and {len(notifications['missing_pos']) - 5} more</li>"
                report_content += "</ul>"
            
            if notifications['pending_assessments']:
                report_content += f"""
                <h3 style="color: #ffc107;">📝 Pending Assessments ({len(notifications['pending_assessments'])})</h3>
                <ul>
                """
                for assessment in notifications['pending_assessments'][:5]:
                    report_content += f"<li>{assessment['student_name']} - {assessment['program']}</li>"
                if len(notifications['pending_assessments']) > 5:
                    report_content += f"<li>... and {len(notifications['pending_assessments']) - 5} more</li>"
                report_content += "</ul>"
            
            body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px;">
                    <h2 style="color: #2c3e50; margin: 0;">📊 Daily System Report</h2>
                    <p style="margin: 5px 0 0 0; color: #6c757d;">{nowdate()}</p>
                </div>
                
                {report_content}
                
                <p>Best regards,<br>
                <strong>Numero Uno System</strong></p>
            </div>
            """
            
            frappe.sendmail(
                recipients=email_addresses,
                subject=subject,
                message=body,
                now=True
            )
            
            frappe.logger().info(f"Daily consolidated report sent")
            
        except Exception as e:
            frappe.logger().error(f"Failed to send consolidated report: {str(e)}")


# Convenience functions for easy calling
def send_welcome_email(student_name, email, program_name):
    """Send welcome email to new student"""
    NotificationManager.send_welcome_email(student_name, email, program_name)

def send_unpaid_student_report(student_group_name, student_group_title, unpaid_students):
    """Send unpaid student report"""
    NotificationManager.send_unpaid_student_report(student_group_name, student_group_title, unpaid_students)

def send_cash_assignment_notification(student_name, email, program_name, instructor_name):
    """Send cash assignment notification"""
    NotificationManager.send_cash_assignment_notification(student_name, email, program_name, instructor_name)

def send_missing_po_notification(program_name, customer_name, sales_order_name):
    """Send missing PO notification"""
    NotificationManager.send_missing_po_notification(program_name, customer_name, sales_order_name)

def send_instructor_task_assignment(instructor_name, email, task_details):
    """Send instructor task assignment notification"""
    NotificationManager.send_instructor_task_assignment(instructor_name, email, task_details)

def send_assessment_pending_notification(student_name, email, program_name, assessment_plan):
    """Send assessment pending notification"""
    NotificationManager.send_assessment_pending_notification(student_name, email, program_name, assessment_plan)

def send_student_absent_notification(student_name, email, program_name, absent_date, instructor_name):
    """Send student absent notification"""
    NotificationManager.send_student_absent_notification(student_name, email, program_name, absent_date, instructor_name)

def send_attendance_eligibility_notification(student_name, email, program_name, attendance_percentage, required_percentage):
    """Send attendance eligibility notification"""
    NotificationManager.send_attendance_eligibility_notification(student_name, email, program_name, attendance_percentage, required_percentage)

def send_daily_consolidated_report():
    """Send daily consolidated report"""
    NotificationManager.send_daily_consolidated_report() 