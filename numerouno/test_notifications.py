import frappe
from numerouno.numerouno.notifications.notification_config import NotificationConfig
from numerouno.numerouno.notifications.event_handlers import handle_sales_order_creation, handle_assessment_creation, handle_student_absence

def test_notification_system():
    """Test the notification system"""
    print("Testing notification system...")
    
    # Test 1: Check if sales emails are found
    print("\n1. Testing sales emails...")
    sales_emails = NotificationConfig.get_sales_emails()
    print(f"Sales emails: {sales_emails}")
    
    # Test 2: Check if instructor emails are found
    print("\n2. Testing instructor emails...")
    instructor_emails = NotificationConfig.get_instructor_emails()
    print(f"Instructor emails: {instructor_emails}")
    
    # Test 3: Check if management emails are found
    print("\n3. Testing management emails...")
    management_emails = NotificationConfig.get_management_emails()
    print(f"Management emails: {management_emails}")
    
    # Test 4: Send a test email
    # print("\n4. Testing email sending...")
    # try:
    #     frappe.sendmail(
    #         recipients=management_emails,
    #         subject="Test Notification System",
    #         message="This is a test email from the notification system.",
    #         now=True
    #     )
    #     print("Test email sent successfully!")
    # except Exception as e:
    #     print(f"Failed to send test email: {str(e)}")
    
    # Test 5: Check recent sales orders
    print("\n5. Checking recent sales orders...")
    recent_sales_orders = frappe.get_all("Sales Order", 
        filters={"docstatus": 0}, 
        fields=["name", "customer", "grand_total", "creation"],
        limit=5
    )
    print(f"Recent sales orders: {recent_sales_orders}")
    
    # Test 6: Check recent assessment results
    print("\n6. Checking recent assessment results...")
    recent_assessments = frappe.get_all("Assessment Result", 
        fields=["name", "student_name", "program", "status", "creation"],
        limit=5
    )
    print(f"Recent assessments: {recent_assessments}")
    
    # Test 7: Check recent student attendance
    print("\n7. Checking recent student attendance...")
    recent_attendance = frappe.get_all("Student Attendance", 
        filters={"status": "Absent"},
        fields=["name", "student_name", "program", "status", "date"],
        limit=5
    )
    print(f"Recent absent students: {recent_attendance}")
    
    print("\nNotification system test completed!")

if __name__ == "__main__":
    test_notification_system() 