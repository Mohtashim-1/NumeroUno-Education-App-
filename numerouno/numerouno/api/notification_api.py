import frappe
from frappe import _
from ..notifications.notification_manager import NotificationManager
from ..notifications.notification_config import NotificationConfig
import json

@frappe.whitelist()
def send_welcome_email_manual(student_name, email, program_name):
    """Manually send welcome email"""
    try:
        if NotificationConfig.is_notification_enabled("welcome_email"):
            NotificationManager.send_welcome_email(student_name, email, program_name)
            return {"status": "success", "message": "Welcome email sent successfully"}
        else:
            return {"status": "disabled", "message": "Welcome email notifications are disabled"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def send_unpaid_student_report_manual(student_group_name):
    """Manually send unpaid student report"""
    try:
        if NotificationConfig.is_notification_enabled("unpaid_student"):
            # Get unpaid students for the group
            unpaid_students = frappe.db.sql("""
                SELECT 
                    sgs.student,
                    sgs.student_name,
                    sgs.group_roll_number
                FROM `tabStudent Group Student` sgs
                WHERE sgs.parent = %s
                AND (sgs.custom_invoiced = 0 OR sgs.custom_invoiced IS NULL)
            """, student_group_name, as_dict=True)
            
            if unpaid_students:
                student_group_title = frappe.db.get_value("Student Group", student_group_name, "student_group_name")
                NotificationManager.send_unpaid_student_report(student_group_name, student_group_title, unpaid_students)
                return {"status": "success", "message": f"Unpaid student report sent for {len(unpaid_students)} students"}
            else:
                return {"status": "no_data", "message": "No unpaid students found"}
        else:
            return {"status": "disabled", "message": "Unpaid student notifications are disabled"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def send_missing_po_report_manual():
    """Manually send missing PO report"""
    try:
        if NotificationConfig.is_notification_enabled("missing_po"):
            # Get all sales orders with missing POs
            missing_pos = frappe.db.sql("""
                SELECT 
                    so.name,
                    so.customer,
                    so.program_name
                FROM `tabSales Order` so
                WHERE (so.po_no IS NULL OR so.po_no = '')
                AND so.docstatus = 1
            """, as_dict=True)
            
            if missing_pos:
                for po in missing_pos:
                    NotificationManager.send_missing_po_notification(
                        po.program_name, po.customer, po.name
                    )
                return {"status": "success", "message": f"Missing PO notifications sent for {len(missing_pos)} orders"}
            else:
                return {"status": "no_data", "message": "No missing POs found"}
        else:
            return {"status": "disabled", "message": "Missing PO notifications are disabled"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def send_assessment_pending_report_manual():
    """Manually send assessment pending report"""
    try:
        if NotificationConfig.is_notification_enabled("assessment_pending"):
            # Get all pending assessments
            pending_assessments = frappe.db.sql("""
                SELECT 
                    ar.name,
                    ar.student,
                    ar.student_name,
                    ar.program,
                    ar.assessment_plan
                FROM `tabAssessment Result` ar
                WHERE ar.docstatus = 0
                AND ar.grade IS NULL
            """, as_dict=True)
            
            if pending_assessments:
                for assessment in pending_assessments:
                    email = frappe.db.get_value("Student", assessment.student, "email")
                    if email:
                        NotificationManager.send_assessment_pending_notification(
                            assessment.student_name, email, assessment.program, assessment.assessment_plan
                        )
                return {"status": "success", "message": f"Assessment pending notifications sent for {len(pending_assessments)} assessments"}
            else:
                return {"status": "no_data", "message": "No pending assessments found"}
        else:
            return {"status": "disabled", "message": "Assessment pending notifications are disabled"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def send_attendance_eligibility_report_manual():
    """Manually send attendance eligibility report"""
    try:
        if NotificationConfig.is_notification_enabled("attendance_eligibility"):
            required_percentage = NotificationConfig.get_attendance_requirement()
            
            # Get students with low attendance
            students_with_low_attendance = frappe.db.sql("""
                SELECT 
                    s.name as student,
                    s.student_name,
                    s.program,
                    COUNT(sa.name) as total_sessions,
                    SUM(CASE WHEN sa.status = 'Present' THEN 1 ELSE 0 END) as attended_sessions
                FROM `tabStudent` s
                LEFT JOIN `tabStudent Attendance` sa ON sa.student = s.name
                WHERE sa.date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                GROUP BY s.name, s.student_name, s.program
                HAVING (attended_sessions / total_sessions * 100) < %s
            """, required_percentage, as_dict=True)
            
            if students_with_low_attendance:
                for student in students_with_low_attendance:
                    attendance_percentage = (student.attended_sessions / student.total_sessions) * 100
                    email = frappe.db.get_value("Student", student.student, "email")
                    if email:
                        NotificationManager.send_attendance_eligibility_notification(
                            student.student_name, email, student.program, 
                            round(attendance_percentage, 1), required_percentage
                        )
                return {"status": "success", "message": f"Attendance eligibility notifications sent for {len(students_with_low_attendance)} students"}
            else:
                return {"status": "no_data", "message": "No students with low attendance found"}
        else:
            return {"status": "disabled", "message": "Attendance eligibility notifications are disabled"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def send_daily_consolidated_report_manual():
    """Manually send daily consolidated report"""
    try:
        if NotificationConfig.is_notification_enabled("daily_consolidated"):
            NotificationManager.send_daily_consolidated_report()
            return {"status": "success", "message": "Daily consolidated report sent"}
        else:
            return {"status": "disabled", "message": "Daily consolidated reports are disabled"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def get_notification_settings():
    """Get current notification settings"""
    try:
        settings = NotificationConfig.get_notification_settings()
        return {"status": "success", "settings": settings}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def update_notification_settings(settings_dict):
    """Update notification settings"""
    try:
        settings = json.loads(settings_dict) if isinstance(settings_dict, str) else settings_dict
        
        # Update system settings
        system_settings = frappe.get_doc("System Settings")
        
        for key, value in settings.items():
            if hasattr(system_settings, f"custom_{key}"):
                setattr(system_settings, f"custom_{key}", value)
        
        system_settings.save()
        
        return {"status": "success", "message": "Notification settings updated successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def get_notification_stats():
    """Get notification statistics"""
    try:
        # Get notification logs for the last 30 days
        from frappe.utils import add_days
        
        thirty_days_ago = add_days(frappe.utils.nowdate(), -30)
        
        stats = frappe.db.sql("""
            SELECT 
                notification_type,
                status,
                COUNT(*) as count
            FROM `tabNotification Log`
            WHERE creation >= %s
            GROUP BY notification_type, status
        """, thirty_days_ago, as_dict=True)
        
        return {"status": "success", "stats": stats}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def test_notification(notification_type, test_email):
    """Test a specific notification type"""
    try:
        if notification_type == "welcome_email":
            NotificationManager.send_welcome_email("Test Student", test_email, "Test Program")
        elif notification_type == "unpaid_students":
            test_data = [{"student": "TEST001", "student_name": "Test Student", "group_roll_number": "001"}]
            NotificationManager.send_unpaid_student_report("TEST_GROUP", "Test Group", test_data)
        elif notification_type == "missing_po":
            NotificationManager.send_missing_po_notification("Test Program", "Test Customer", "TEST-SO-001")
        else:
            return {"status": "error", "message": "Unknown notification type"}
        
        return {"status": "success", "message": f"Test {notification_type} notification sent to {test_email}"}
    except Exception as e:
        return {"status": "error", "message": str(e)} 