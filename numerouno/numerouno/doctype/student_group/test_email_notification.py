# Test script for email notification system
import frappe

def test_email_notification():
    """Test the email notification system"""
    
    # Test data
    test_student_group_name = "TEST-SG-001"
    test_student_group_title = "Test Student Group"
    test_unpaid_students = [
        {
            "student": "STU-001",
            "student_name": "John Doe",
            "group_roll_number": 1
        },
        {
            "student": "STU-002", 
            "student_name": "Jane Smith",
            "group_roll_number": 2
        }
    ]
    
    try:
        # Import and call the notification function
        from numerouno.numerouno.doctype.student_group.student_group import send_unpaid_student_notification
        
        send_unpaid_student_notification(
            test_student_group_name,
            test_student_group_title,
            test_unpaid_students
        )
        
        print("✅ Email notification test completed successfully")
        
    except Exception as e:
        print(f"❌ Email notification test failed: {str(e)}")
        frappe.log_error(f"Email notification test failed: {str(e)}")

def test_daily_notification():
    """Test the daily notification system"""
    
    try:
        # Import and call the daily notification function
        from numerouno.numerouno.doctype.student_group.student_group import send_daily_unpaid_notifications
        
        send_daily_unpaid_notifications()
        
        print("✅ Daily notification test completed successfully")
        
    except Exception as e:
        print(f"❌ Daily notification test failed: {str(e)}")
        frappe.log_error(f"Daily notification test failed: {str(e)}")

if __name__ == "__main__":
    test_email_notification()
    test_daily_notification() 