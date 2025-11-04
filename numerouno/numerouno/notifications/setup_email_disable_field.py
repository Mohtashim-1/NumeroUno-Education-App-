"""
One-time setup script to create the custom_disable_emails_until field in System Settings
Run this once to create the field, or it will be created automatically when needed.
"""

import frappe

def setup_email_disable_field():
    """Create the custom_disable_emails_until field in System Settings if it doesn't exist"""
    try:
        if frappe.db.exists("Custom Field", {"dt": "System Settings", "fieldname": "custom_disable_emails_until"}):
            print("✅ Custom field 'custom_disable_emails_until' already exists")
            return True
        
        # Find a good field to insert after
        insert_after = None
        
        # Try to find custom_attendance_requirement first
        if frappe.db.exists("Custom Field", {"dt": "System Settings", "fieldname": "custom_attendance_requirement"}):
            insert_after = "custom_attendance_requirement"
        # Or try enable_email_queue
        elif frappe.db.exists("DocField", {"parent": "System Settings", "fieldname": "enable_email_queue"}):
            insert_after = "enable_email_queue"
        # Or try any other custom field
        else:
            custom_fields = frappe.get_all(
                "Custom Field",
                filters={"dt": "System Settings"},
                fields=["fieldname"],
                limit=1,
                order_by="creation desc"
            )
            if custom_fields:
                insert_after = custom_fields[0].fieldname
        
        custom_field = frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "System Settings",
            "fieldname": "custom_disable_emails_until",
            "label": "Disable Emails Until",
            "fieldtype": "Date",
            "description": "Disable all email notifications until this date (YYYY-MM-DD format)",
            "insert_after": insert_after
        })
        custom_field.insert(ignore_permissions=True)
        frappe.db.commit()
        
        print("✅ Successfully created custom field 'custom_disable_emails_until' in System Settings")
        print("   You can now use NotificationConfig.disable_emails_until(date) to disable emails")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create custom field: {str(e)}")
        print(f"   Error details: {frappe.get_traceback()}")
        return False

if __name__ == "__main__":
    setup_email_disable_field()

