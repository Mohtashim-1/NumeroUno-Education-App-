"""
Script to temporarily disable or enable email notifications
Usage:
    # Disable emails until a specific date (YYYY-MM-DD format)
    python -c "from numerouno.numerouno.notifications.disable_emails import disable_emails_until; disable_emails_until('2025-01-15')"
    
    # Re-enable emails immediately
    python -c "from numerouno.numerouno.notifications.disable_emails import enable_emails; enable_emails()"
"""

import frappe
from numerouno.numerouno.notifications.notification_config import NotificationConfig

def disable_emails_until(date):
    """
    Disable all email notifications until a specific date
    
    Args:
        date (str): Date in YYYY-MM-DD format (e.g., '2025-01-15')
    
    Example:
        disable_emails_until('2025-01-15')  # Disable until January 15, 2025
    """
    try:
        # Ensure custom field exists (will be created by NotificationConfig if needed)
        from numerouno.numerouno.notifications.notification_config import NotificationConfig
        NotificationConfig.ensure_custom_field_exists()
        
        # Set the date
        NotificationConfig.disable_emails_until(date)
        print(f"✅ Emails disabled until {date}")
        return True
    except Exception as e:
        print(f"❌ Failed to disable emails: {str(e)}")
        return False

def enable_emails():
    """
    Re-enable all email notifications immediately
    
    Example:
        enable_emails()
    """
    try:
        NotificationConfig.enable_emails()
        print("✅ Emails re-enabled")
        return True
    except Exception as e:
        print(f"❌ Failed to enable emails: {str(e)}")
        return False

def check_email_status():
    """
    Check current email status (enabled or disabled)
    """
    try:
        settings = NotificationConfig.get_notification_settings()
        disable_until = settings.get("disable_emails_until")
        
        if not disable_until:
            print("📧 Status: Emails are ENABLED")
            return True
        else:
            from frappe.utils import getdate, today
            current_date = getdate(today())
            disable_date = getdate(disable_until)
            
            if current_date <= disable_date:
                print(f"📧 Status: Emails are DISABLED until {disable_until}")
                print(f"   Current date: {current_date}")
                print(f"   Disable until: {disable_date}")
                return False
            else:
                print(f"📧 Status: Emails are ENABLED (disable period ended on {disable_until})")
                return True
    except Exception as e:
        print(f"❌ Failed to check email status: {str(e)}")
        return None

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python disable_emails.py disable YYYY-MM-DD  # Disable until date")
        print("  python disable_emails.py enable               # Re-enable emails")
        print("  python disable_emails.py status                # Check status")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "disable":
        if len(sys.argv) < 3:
            print("❌ Please provide a date in YYYY-MM-DD format")
            print("   Example: python disable_emails.py disable 2025-01-15")
            sys.exit(1)
        date = sys.argv[2]
        disable_emails_until(date)
    elif command == "enable":
        enable_emails()
    elif command == "status":
        check_email_status()
    else:
        print(f"❌ Unknown command: {command}")
        print("   Use 'disable', 'enable', or 'status'")
        sys.exit(1)

