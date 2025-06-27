# Debug script for email notification system
import frappe
from frappe.utils import get_url, nowdate

def debug_email_notification_system():
    """Comprehensive debugging of the email notification system"""
    
    print("🔍 Starting Email Notification System Debug...")
    print("=" * 50)
    
    # 1. Check if users with required roles exist
    print("\n1. Checking Users with Required Roles:")
    accounts_users = frappe.get_all(
        "Has Role",
        filters={"role": ["in", ["Accounts User", "Accounts Manager"]]},
        fields=["parent", "role"]
    )
    
    if not accounts_users:
        print("❌ No users found with Accounts User or Accounts Manager roles")
        print("   Please create users with these roles first")
        return False
    else:
        print(f"✅ Found {len(accounts_users)} users with required roles:")
        for user in accounts_users:
            email = frappe.db.get_value("User", user.parent, "email")
            print(f"   - {user.parent} ({user.role}): {email}")
    
    # 2. Check email configuration
    print("\n2. Checking Email Configuration:")
    email_settings = frappe.get_doc("Email Settings")
    if email_settings.smtp_server:
        print(f"✅ SMTP Server configured: {email_settings.smtp_server}")
    else:
        print("❌ SMTP Server not configured")
        print("   Go to Setup > Email Settings to configure email")
        return False
    
    # 3. Check if Student Groups exist with unpaid students
    print("\n3. Checking Student Groups with Unpaid Students:")
    unpaid_data = frappe.db.sql("""
        SELECT 
            sg.name as student_group_name,
            sg.student_group_name as student_group_title,
            COUNT(sgs.name) as unpaid_count
        FROM `tabStudent Group` sg
        JOIN `tabStudent Group Student` sgs ON sgs.parent = sg.name
        WHERE sgs.custom_invoiced = 0 OR sgs.custom_invoiced IS NULL
        GROUP BY sg.name, sg.student_group_name
        ORDER BY sg.student_group_name
    """, as_dict=True)
    
    if not unpaid_data:
        print("❌ No Student Groups found with unpaid students")
        print("   Create a Student Group with students having custom_invoiced = 0")
        return False
    else:
        print(f"✅ Found {len(unpaid_data)} Student Groups with unpaid students:")
        for group in unpaid_data:
            print(f"   - {group.student_group_title}: {group.unpaid_count} unpaid students")
    
    # 4. Test individual notification function
    print("\n4. Testing Individual Notification Function:")
    try:
        test_student_group = unpaid_data[0]  # Use first group with unpaid students
        
        # Get unpaid students for this group
        unpaid_students = frappe.db.sql("""
            SELECT 
                sgs.student,
                sgs.student_name,
                sgs.group_roll_number
            FROM `tabStudent Group Student` sgs
            WHERE sgs.parent = %s AND (sgs.custom_invoiced = 0 OR sgs.custom_invoiced IS NULL)
        """, test_student_group.student_group_name, as_dict=True)
        
        print(f"   Testing with Student Group: {test_student_group.student_group_title}")
        print(f"   Unpaid students found: {len(unpaid_students)}")
        
        # Import and test the function
        from numerouno.numerouno.doctype.student_group.student_group import send_unpaid_student_notification
        
        send_unpaid_student_notification(
            test_student_group.student_group_name,
            test_student_group.student_group_title,
            unpaid_students
        )
        
        print("   ✅ Individual notification function executed successfully")
        
    except Exception as e:
        print(f"   ❌ Individual notification function failed: {str(e)}")
        frappe.log_error(f"Individual notification test failed: {str(e)}")
        return False
    
    # 5. Test daily notification function
    print("\n5. Testing Daily Notification Function:")
    try:
        from numerouno.numerouno.doctype.student_group.student_group import send_daily_unpaid_notifications
        
        send_daily_unpaid_notifications()
        
        print("   ✅ Daily notification function executed successfully")
        
    except Exception as e:
        print(f"   ❌ Daily notification function failed: {str(e)}")
        frappe.log_error(f"Daily notification test failed: {str(e)}")
        return False
    
    # 6. Check hooks configuration
    print("\n6. Checking Hooks Configuration:")
    try:
        # Check if the hooks are properly loaded
        from numerouno import hooks
        
        if hasattr(hooks, 'doc_events') and 'Student Group' in hooks.doc_events:
            print("   ✅ Student Group doc_events found in hooks")
            print(f"   Events: {hooks.doc_events['Student Group']}")
        else:
            print("   ❌ Student Group doc_events not found in hooks")
            return False
            
        if hasattr(hooks, 'scheduler_events') and 'daily' in hooks.scheduler_events:
            print("   ✅ Daily scheduler_events found in hooks")
            print(f"   Events: {hooks.scheduler_events['daily']}")
        else:
            print("   ❌ Daily scheduler_events not found in hooks")
            return False
            
    except Exception as e:
        print(f"   ❌ Hooks check failed: {str(e)}")
        return False
    
    print("\n" + "=" * 50)
    print("✅ Email Notification System Debug Complete!")
    print("If all checks passed, the system should be working.")
    print("Check your email inbox for test notifications.")
    
    return True

def fix_common_issues():
    """Fix common issues with the email notification system"""
    
    print("\n🔧 Fixing Common Issues...")
    print("=" * 50)
    
    # 1. Ensure proper imports in student_group.py
    print("\n1. Checking imports in student_group.py:")
    try:
        # Check if all required imports are present
        import frappe
        from frappe.utils import get_url, nowdate
        from frappe.utils.background_jobs import enqueue
        
        print("   ✅ All required imports are available")
        
    except ImportError as e:
        print(f"   ❌ Import error: {str(e)}")
        return False
    
    # 2. Test email sending directly
    print("\n2. Testing Direct Email Sending:")
    try:
        # Get a test email address
        test_user = frappe.get_all("Has Role", filters={"role": "Accounts User"}, fields=["parent"], limit=1)
        if test_user:
            test_email = frappe.db.get_value("User", test_user[0].parent, "email")
            if test_email:
                frappe.sendmail(
                    recipients=[test_email],
                    subject="Test Email - Email Notification System",
                    message="This is a test email to verify the email system is working.",
                    now=True
                )
                print(f"   ✅ Test email sent to {test_email}")
            else:
                print("   ❌ No email address found for test user")
        else:
            print("   ❌ No Accounts User found for testing")
            
    except Exception as e:
        print(f"   ❌ Direct email test failed: {str(e)}")
        return False
    
    # 3. Check if custom_invoiced field exists
    print("\n3. Checking custom_invoiced field:")
    try:
        # Check if the field exists in the database
        field_exists = frappe.db.sql("""
            SELECT COUNT(*) as count 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'tabStudent Group Student' 
            AND COLUMN_NAME = 'custom_invoiced'
        """)
        
        if field_exists[0][0] > 0:
            print("   ✅ custom_invoiced field exists in database")
        else:
            print("   ❌ custom_invoiced field not found in database")
            print("   Run: bench migrate")
            return False
            
    except Exception as e:
        print(f"   ❌ Field check failed: {str(e)}")
        return False
    
    print("\n" + "=" * 50)
    print("✅ Common Issues Fix Complete!")
    
    return True

def create_test_data():
    """Create test data for email notification testing"""
    
    print("\n📝 Creating Test Data...")
    print("=" * 50)
    
    try:
        # 1. Create a test Student Group if none exists
        existing_groups = frappe.get_all("Student Group", limit=1)
        if not existing_groups:
            print("   Creating test Student Group...")
            sg = frappe.new_doc("Student Group")
            sg.student_group_name = "Test Group for Email Notifications"
            sg.academic_year = frappe.get_all("Academic Year", limit=1)[0].name if frappe.get_all("Academic Year") else None
            sg.group_based_on = "Activity"
            sg.insert()
            print(f"   ✅ Created test Student Group: {sg.name}")
        else:
            print(f"   Using existing Student Group: {existing_groups[0].name}")
            sg = frappe.get_doc("Student Group", existing_groups[0].name)
        
        # 2. Add test students with custom_invoiced = 0
        if not sg.students:
            print("   Adding test students...")
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
            print(f"   ✅ Added {len(test_students)} test students with custom_invoiced = 0")
        
        # 3. Create test user with Accounts User role if none exists
        accounts_users = frappe.get_all("Has Role", filters={"role": "Accounts User"}, limit=1)
        if not accounts_users:
            print("   Creating test user with Accounts User role...")
            user = frappe.new_doc("User")
            user.email = "test-accounts@example.com"
            user.first_name = "Test"
            user.last_name = "Accounts User"
            user.send_welcome_email = 0
            user.insert()
            
            # Add role
            user.add_roles("Accounts User")
            print(f"   ✅ Created test user: {user.email}")
        else:
            print(f"   Using existing Accounts User: {accounts_users[0].parent}")
        
        print("\n" + "=" * 50)
        print("✅ Test Data Creation Complete!")
        print("You can now test the email notification system.")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Test data creation failed: {str(e)}")
        frappe.log_error(f"Test data creation failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Email Notification System Debug and Fix Tool")
    print("=" * 60)
    
    # Run all debugging and fixing functions
    success = True
    
    success &= debug_email_notification_system()
    success &= fix_common_issues()
    success &= create_test_data()
    
    if success:
        print("\n🎉 All checks passed! The email notification system should be working.")
        print("Check your email inbox for test notifications.")
    else:
        print("\n⚠️  Some issues were found. Please review the output above and fix the problems.") 