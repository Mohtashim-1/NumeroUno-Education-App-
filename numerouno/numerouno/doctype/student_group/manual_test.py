# Manual test script for email notification system
import frappe

def test_step_by_step():
    """Test the email notification system step by step"""
    
    print("🧪 Manual Test for Email Notification System")
    print("=" * 50)
    
    # Step 1: Check if we have users with required roles
    print("\nStep 1: Checking for users with Accounts User/Manager roles...")
    accounts_users = frappe.get_all(
        "Has Role",
        filters={"role": ["in", ["Accounts User", "Accounts Manager"]]},
        fields=["parent", "role"]
    )
    
    if not accounts_users:
        print("❌ No users found with required roles!")
        print("Please create a user with 'Accounts User' or 'Accounts Manager' role first.")
        return False
    
    print(f"✅ Found {len(accounts_users)} users with required roles")
    for user in accounts_users:
        email = frappe.db.get_value("User", user.parent, "email")
        print(f"   - {user.parent} ({user.role}): {email}")
    
    # Step 2: Check email settings
    print("\nStep 2: Checking email settings...")
    try:
        email_settings = frappe.get_doc("Email Settings")
        if email_settings.smtp_server:
            print(f"✅ SMTP Server: {email_settings.smtp_server}")
        else:
            print("❌ SMTP Server not configured!")
            print("Go to Setup > Email Settings to configure email")
            return False
    except Exception as e:
        print(f"❌ Error checking email settings: {str(e)}")
        return False
    
    # Step 3: Find or create a Student Group with unpaid students
    print("\nStep 3: Finding Student Group with unpaid students...")
    
    # First, check if any existing groups have unpaid students
    unpaid_groups = frappe.db.sql("""
        SELECT DISTINCT sg.name, sg.student_group_name
        FROM `tabStudent Group` sg
        JOIN `tabStudent Group Student` sgs ON sgs.parent = sg.name
        WHERE sgs.custom_invoiced = 0 OR sgs.custom_invoiced IS NULL
        LIMIT 1
    """, as_dict=True)
    
    if unpaid_groups:
        student_group_name = unpaid_groups[0].name
        student_group_title = unpaid_groups[0].student_group_name
        print(f"✅ Found existing Student Group: {student_group_title}")
    else:
        print("No existing groups with unpaid students found.")
        print("Creating a test Student Group...")
        
        # Create a test Student Group
        try:
            sg = frappe.new_doc("Student Group")
            sg.student_group_name = "Test Group for Email Notifications"
            
            # Get academic year if exists
            academic_years = frappe.get_all("Academic Year", limit=1)
            if academic_years:
                sg.academic_year = academic_years[0].name
            
            sg.group_based_on = "Activity"
            sg.insert()
            
            # Add test students
            test_students = [
                {"student": "TEST-STU-001", "student_name": "Test Student 1"},
                {"student": "TEST-STU-002", "student_name": "Test Student 2"}
            ]
            
            for i, student_data in enumerate(test_students, 1):
                sg.append("students", {
                    "student": student_data["student"],
                    "student_name": student_data["student_name"],
                    "group_roll_number": i,
                    "active": 1,
                    "custom_invoiced": 0  # This is the key field
                })
            
            sg.save()
            student_group_name = sg.name
            student_group_title = sg.student_group_name
            print(f"✅ Created test Student Group: {student_group_title}")
            
        except Exception as e:
            print(f"❌ Error creating test Student Group: {str(e)}")
            return False
    
    # Step 4: Get unpaid students from the group
    print("\nStep 4: Getting unpaid students...")
    unpaid_students = frappe.db.sql("""
        SELECT 
            sgs.student,
            sgs.student_name,
            sgs.group_roll_number
        FROM `tabStudent Group Student` sgs
        WHERE sgs.parent = %s AND (sgs.custom_invoiced = 0 OR sgs.custom_invoiced IS NULL)
    """, student_group_name, as_dict=True)
    
    if not unpaid_students:
        print("❌ No unpaid students found in the group!")
        return False
    
    print(f"✅ Found {len(unpaid_students)} unpaid students:")
    for student in unpaid_students:
        print(f"   - {student.student_name} (Roll: {student.group_roll_number})")
    
    # Step 5: Test the email notification function
    print("\nStep 5: Testing email notification function...")
    try:
        from numerouno.numerouno.doctype.student_group.student_group import send_unpaid_student_notification
        
        send_unpaid_student_notification(
            student_group_name,
            student_group_title,
            unpaid_students
        )
        
        print("✅ Email notification function executed successfully!")
        print("Check the email inboxes of the users listed in Step 1.")
        
    except Exception as e:
        print(f"❌ Email notification function failed: {str(e)}")
        frappe.log_error(f"Email notification test failed: {str(e)}")
        return False
    
    # Step 6: Test the daily notification function
    print("\nStep 6: Testing daily notification function...")
    try:
        from numerouno.numerouno.doctype.student_group.student_group import send_daily_unpaid_notifications
        
        send_daily_unpaid_notifications()
        
        print("✅ Daily notification function executed successfully!")
        print("Check the email inboxes for the daily report.")
        
    except Exception as e:
        print(f"❌ Daily notification function failed: {str(e)}")
        frappe.log_error(f"Daily notification test failed: {str(e)}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All tests completed successfully!")
    print("If you received emails, the system is working correctly.")
    print("If no emails were received, check:")
    print("1. Email settings configuration")
    print("2. Spam/junk folders")
    print("3. Error logs: bench --site your-site.com logs")
    
    return True

def quick_test():
    """Quick test to send a simple email"""
    print("\n📧 Quick Email Test...")
    
    try:
        # Get first user with email
        users = frappe.get_all("User", filters={"email": ["!=", ""]}, fields=["name", "email"], limit=1)
        
        if not users:
            print("❌ No users with email addresses found")
            return False
        
        test_user = users[0]
        print(f"Testing email to: {test_user.email}")
        
        # Send test email
        frappe.sendmail(
            recipients=[test_user.email],
            subject="Test Email - Numero Uno System",
            message="This is a test email to verify the email system is working correctly.",
            now=True
        )
        
        print("✅ Test email sent successfully!")
        print(f"Check the inbox of: {test_user.email}")
        return True
        
    except Exception as e:
        print(f"❌ Quick email test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Email Notification System Manual Test")
    print("=" * 50)
    
    # Run quick test first
    quick_test()
    
    # Run full test
    test_step_by_step() 