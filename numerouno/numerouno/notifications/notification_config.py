import frappe
from frappe import _
from frappe.utils import getdate, today

class NotificationConfig:
    """Configuration class for notification settings"""
    
    @staticmethod
    def get_notification_settings():
        """Get notification settings from system"""
        try:
            settings = frappe.get_doc("System Settings")
            
            # Default settings
            default_settings = {
                "welcome_email_enabled": True,
                "unpaid_student_notifications": True,
                "missing_po_notifications": True,
                "instructor_assignment_notifications": True,
                "assessment_pending_notifications": True,
                "student_absence_notifications": True,
                "attendance_eligibility_notifications": True,
                "daily_consolidated_reports": True,
                "attendance_requirement_percentage": 80,
                "notification_retention_days": 30,
                "email_template_language": "en",
                "disable_emails_until": None
            }
            
            # Override with custom settings if available
            if hasattr(settings, 'custom_welcome_email_enabled'):
                default_settings["welcome_email_enabled"] = settings.custom_welcome_email_enabled
                
            if hasattr(settings, 'custom_attendance_requirement'):
                default_settings["attendance_requirement_percentage"] = settings.custom_attendance_requirement or 80
            
            # Check for disable emails until date
            disable_until = frappe.db.get_single_value("System Settings", "custom_disable_emails_until")
            if disable_until:
                default_settings["disable_emails_until"] = disable_until
                
            return default_settings
            
        except Exception as e:
            print(f"Failed to get notification settings: {str(e)}")
            return {
                "welcome_email_enabled": True,
                "unpaid_student_notifications": True,
                "missing_po_notifications": True,
                "instructor_assignment_notifications": True,
                "assessment_pending_notifications": True,
                "student_absence_notifications": True,
                "attendance_eligibility_notifications": True,
                "daily_consolidated_reports": True,
                "attendance_requirement_percentage": 80,
                "notification_retention_days": 30,
                "email_template_language": "en",
                "disable_emails_until": None
            }
    
    @staticmethod
    def is_notification_enabled(notification_type):
        """Check if a specific notification type is enabled"""
        # First check if emails are disabled temporarily
        if not NotificationConfig.should_send_emails():
            return False
            
        settings = NotificationConfig.get_notification_settings()
        return settings.get(f"{notification_type}_enabled", True)
    
    @staticmethod
    def should_send_emails():
        """Check if emails should be sent (not disabled temporarily)"""
        try:
            settings = NotificationConfig.get_notification_settings()
            disable_until = settings.get("disable_emails_until")
            
            if not disable_until:
                return True
            
            # Convert to date if it's a string
            if isinstance(disable_until, str):
                disable_until = getdate(disable_until)
            
            current_date = getdate(today())
            
            # If current date is before or equal to disable_until date, emails are disabled
            if current_date <= disable_until:
                print(f"📧 Emails are disabled until {disable_until}. Current date: {current_date}")
                return False
            
            # If current date is after disable_until, emails are enabled
            print(f"📧 Emails are enabled. Disable period ended on {disable_until}")
            return True
            
        except Exception as e:
            print(f"Failed to check email disable status: {str(e)}")
            # Default to allowing emails if check fails
            return True
    
    @staticmethod
    def get_attendance_requirement():
        """Get attendance requirement percentage"""
        settings = NotificationConfig.get_notification_settings()
        return settings.get("attendance_requirement_percentage", 80)
    
    @staticmethod
    def get_email_recipients(role_list):
        """Get email recipients based on roles"""
        try:
            users = frappe.get_all(
                "Has Role",
                filters={"role": ["in", role_list]},
                fields=["parent"]
            )
            
            email_addresses = []
            for user in users:
                email = frappe.db.get_value("User", user.parent, "email")
                if email:
                    email_addresses.append(email)
            
            return email_addresses
            
        except Exception as e:
            print(f"Failed to get email recipients: {str(e)}")
            return []
    
    @staticmethod
    def get_management_emails():
        """Get management team emails"""
        return NotificationConfig.get_email_recipients([
            "System Manager", 
            "Accounts Manager", 
            "Sales Manager"
        ])
    
    @staticmethod
    def get_accounts_emails():
        """Get accounts team emails"""
        return NotificationConfig.get_email_recipients([
            "Accounts User", 
            "Accounts Manager"
        ])
    
    @staticmethod
    def get_sales_emails():
        """Get sales team emails"""
        emails = NotificationConfig.get_email_recipients([
            "Sales User", 
            "Sales Manager"
        ])
        
        # If no sales emails found, add admin email as fallback
        if not emails:
            admin_email = frappe.db.get_single_value("System Settings", "support_email")
            if admin_email:
                emails.append(admin_email)
        
        print(f"Sales emails returned: {emails}")
        return emails
    
    @staticmethod
    def get_instructor_emails():
        """Get instructor team emails"""
        emails = NotificationConfig.get_email_recipients([
            "Instructor", 
            "Trainer",
            "System Manager"
        ])
        
        # If no instructor emails found, add admin email as fallback
        if not emails:
            admin_email = frappe.db.get_single_value("System Settings", "support_email")
            if admin_email:
                emails.append(admin_email)
        
        print(f"Instructor emails returned: {emails}")
        return emails
    
    @staticmethod
    def log_notification(notification_type, recipient, subject, status="sent"):
        """Log notification for tracking"""
        try:
            frappe.get_doc({
                "doctype": "Notification Log",
                "subject": subject,
                "for_user": recipient,
                "type": "Alert",
                "notification_type": notification_type,
                "status": status
            }).insert(ignore_permissions=True)
            
        except Exception as e:
            print(f"Failed to log notification: {str(e)}")
    
    @staticmethod
    def get_email_template(template_name, language="en"):
        """Get email template content"""
        try:
            # You can create email templates in Frappe and reference them here
            template = frappe.get_doc("Email Template", template_name)
            return template.response
        except:
            # Return default template if not found
            return NotificationConfig.get_default_template(template_name)
    
    @staticmethod
    def get_default_template(template_name):
        """Get default email template content"""
        templates = {
            "welcome_email": """
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>Welcome to Numero Uno Training!</h2>
                <p>Dear {student_name},</p>
                <p>Welcome to {program_name}! We're excited to have you join our training program.</p>
                <p>Best regards,<br>Numero Uno Training Team</p>
            </div>
            """,
            "unpaid_students": """
            <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
                <h3>Unpaid Students Report</h3>
                <p>Please review the following unpaid students:</p>
                {student_list}
                <p>Best regards,<br>Numero Uno System</p>
            </div>
            """,
            "missing_po": """
            <div style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto;">
                <h3>Missing Purchase Order Alert</h3>
                <p>Program: {program_name}</p>
                <p>Customer: {customer_name}</p>
                <p>Please obtain the necessary PO to proceed.</p>
                <p>Best regards,<br>Numero Uno System</p>
            </div>
            """
        }
        
        return templates.get(template_name, "")
    
    @staticmethod
    def format_notification_content(template, **kwargs):
        """Format notification content with variables"""
        try:
            return template.format(**kwargs)
        except Exception as e:
            print(f"Failed to format notification content: {str(e)}")
            return template
    
    @staticmethod
    def disable_emails_until(date):
        """Disable all email notifications until a specific date (YYYY-MM-DD format)"""
        try:
            frappe.db.set_value("System Settings", "System Settings", "custom_disable_emails_until", date)
            frappe.db.commit()
            print(f"📧 Emails disabled until {date}")
            return True
        except Exception as e:
            print(f"Failed to disable emails: {str(e)}")
            return False
    
    @staticmethod
    def enable_emails():
        """Re-enable all email notifications"""
        try:
            frappe.db.set_value("System Settings", "System Settings", "custom_disable_emails_until", None)
            frappe.db.commit()
            print("📧 Emails re-enabled")
            return True
        except Exception as e:
            print(f"Failed to enable emails: {str(e)}")
            return False 