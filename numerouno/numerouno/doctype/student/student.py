# frappe-bench/apps/your_app/your_app/student_custom.py

import frappe
from frappe import _
import frappe.utils
from frappe.utils import getdate

@frappe.whitelist()
def create_student_applicant(student, program):
    # Get current academic year from Education Settings
    education_settings = frappe.get_single("Education Settings")
    current_academic_year = education_settings.current_academic_year
    
    # Get student details
    student_doc = frappe.get_doc("Student", student)
    
    # Create new Student Applicant
    applicant = frappe.new_doc("Student Applicant")
    applicant.update({
        "first_name": student_doc.first_name,
        "last_name": student_doc.last_name,
        "student_email_id": student_doc.student_email_id,
        "program": program,
        "academic_year": current_academic_year,
        "application_date": frappe.utils.nowdate(),
        # "source": "Student"
    })
    
    applicant.insert(ignore_permissions=True)
    
    # Return the URL of the newly created applicant
    return {
        "name": applicant.name,
        "url": frappe.utils.get_url_to_form("Student Applicant", applicant.name)
    }
    
    
@frappe.whitelist()
def create_student_group(student, group_name, academic_year, group_based_on, from_date, to_date, coarse_location=None, course=None, batch=None, program=None):
    student_doc = frappe.get_doc("Student", student)

    group = frappe.new_doc("Student Group")
    group.update({
        "student_group_name": group_name,
        "students": [{"student": student_doc.name}],
        "academic_year": academic_year,
        "group_based_on": group_based_on,
        "course": course,
        "batch": batch,
        "program": program,
        "from_date": from_date,
        "to_date": to_date,
        "coarse_location": coarse_location
    })

    group.insert(ignore_permissions=True)
    return {
        "name": group.name,
        "url": frappe.utils.get_url_to_form("Student Group", group.name)
    }


@frappe.whitelist()
def assign_student_group(student, student_group):
    import traceback
    try:
        group = frappe.get_doc("Student Group", student_group)
        if not any(s.student == student for s in group.students):
            group.append("students",{"student": student})
            group.save(ignore_permissions=True)

        # --- LMS ENROLLMENT LOGIC ---
        course_title = group.course
        # frappe.msgprint(f"[DEBUG] course_title: {course_title}")
        if course_title:
            lms_course_filter = {"title": course_title}
            # frappe.msgprint(f"[DEBUG] LMS Course filter: {lms_course_filter}")
            lms_course = frappe.get_all("LMS Course", filters=lms_course_filter)
            # frappe.msgprint(f"[DEBUG] LMS Course found: {lms_course}")
            if not lms_course:
                lms_course_doc = frappe.new_doc("LMS Course")
                lms_course_doc.title = course_title
                lms_course_doc.append("instructors", {"instructor": "Administrator"})
                lms_course_doc.image = "/files/Screenshot from 2025-07-15 08-49-45.png"
                lms_course_doc.short_introduction = course_title
                lms_course_doc.description = course_title
                lms_course_doc.insert(ignore_permissions=True)
                # frappe.msgprint(f"[DEBUG] Created new LMS Course: {lms_course_doc.name}")
            else:
                lms_course_doc = frappe.get_doc("LMS Course", lms_course[0].name)
                # frappe.msgprint(f"[DEBUG] Using existing LMS Course: {lms_course_doc.name}")

            # --- USER & LMS MEMBER LOGIC ---
            student_doc = frappe.get_doc("Student", student)
            user_email = student_doc.student_email_id
            user_first_name = student_doc.first_name
            user_last_name = student_doc.last_name

            # Validate that we have a valid email before creating user
            if not user_email or not user_email.strip():
                # Check if this is a contact type issue
                contact_type = getattr(student_doc, 'custom_contact_type', None)
                if contact_type == "Email":
                    frappe.throw(_("Student {0} has Contact Type 'Email' but no email address is provided. Please add an email address to the student.").format(student_doc.student_name or student))
                else:
                    frappe.throw(_("Student {0} does not have an email address. Please add an email address to the student before assigning to a student group.").format(student_doc.student_name or student))

            # 1. Get or create User
            user = frappe.db.get_value("User", {"email": user_email})
            if not user:
                user_doc = frappe.new_doc("User")
                user_doc.email = user_email.strip()  # Ensure email is properly cleaned
                user_doc.first_name = user_first_name or "Student"  # Provide default if None
                user_doc.last_name = user_last_name or ""  # Provide default if None
                user_doc.enabled = 1
                user_doc.send_welcome_email = 0
                user_doc.insert(ignore_permissions=True)
                user = user_doc.name
                # frappe.msgprint(f"[DEBUG] Created new User: {user}")
            else:
                pass
                # frappe.msgprint(f"[DEBUG] Found existing User: {user}")

            # 2. Use the User as the member
            member = user  # user is the User's name (email or user ID)

            # 3. Enroll User in LMS Course
            enrollment = frappe.get_all("LMS Enrollment", filters={"course": lms_course_doc.name, "member": member})
            # frappe.msgprint(f"[DEBUG] LMS Enrollment found: {enrollment}")
            if not enrollment:
                enrollment_doc = frappe.new_doc("LMS Enrollment")
                enrollment_doc.course = lms_course_doc.name
                enrollment_doc.member = member
                enrollment_doc.insert(ignore_permissions=True)
                # frappe.msgprint(f"[DEBUG] Created new LMS Enrollment: {enrollment_doc.name}")

        return {
            "name": group.name,
            "url": frappe.utils.get_url_to_form("Student Group", group.name)
        }
    except Exception as e:
        # frappe.msgprint(f"[ERROR] Exception in assign_student_group: {str(e)}\nTraceback:\n{traceback.format_exc()}")
        error_title = f"assign_student_group error: {str(e)[:100]}..."  # Limit title length
        frappe.log_error(
            message=f"assign_student_group error: {str(e)}\n{traceback.format_exc()}",
            title=error_title
        )
        raise

#  run this function when document created it is custom app so i guess it will run on student application created through hooks.py


def validate_student_contact_type(doc, method):
    """Validate student contact type, email requirements, and customer name"""
    
    # Validate customer_name is mandatory
    if not doc.customer_name:
        frappe.throw(_("Customer Name is mandatory for all students"))
    
    # Check if custom_contact_type field exists and has a value
    if hasattr(doc, 'custom_contact_type') and doc.custom_contact_type:
        
        if doc.custom_contact_type == "Email":
            # Make student_email_id mandatory
            if not doc.student_email_id or not doc.student_email_id.strip():
                frappe.throw(_("Student Email Address is mandatory when Contact Type is 'Email'"))
        
        elif doc.custom_contact_type == "Without Email":
            # Auto-generate email if not provided
            if not doc.student_email_id:
                # Generate a system email using student name and ID
                student_name_part = ""
                if doc.first_name:
                    student_name_part = doc.first_name.lower().replace(" ", "")
                
                if doc.name:
                    # Use the student ID in the email
                    generated_email = f"{student_name_part}_{doc.name.lower().replace('-', '_')}@numerouno.local"
                else:
                    # Fallback if name is not available yet
                    import uuid
                    unique_id = str(uuid.uuid4())[:8]
                    generated_email = f"{student_name_part}_{unique_id}@numerouno.local"
                
                doc.student_email_id = generated_email
                frappe.msgprint(_("Auto-generated email address: {0}").format(generated_email))


@frappe.whitelist()
def send_email_notification_to_accountant(doc, method):
    frappe.msgprint(f"Student {doc.student_name} created")
    # send email notification to accountant
    if doc.custom_mode_of_payment == "Cash":
        # get all the users who have the role of "Accounts User"
        accountant_users = frappe.get_all("User", filters={"role": "Accounts User"}, fields=["email"])
        recipient_emails = [user.email for user in accountant_users]
        
        # send email notification to accountant
        frappe.sendmail(
            recipients=recipient_emails,
            subject=f"Cash Payment for {doc.student_name}",
            message=f"Payment for the student {doc.student_name} Payment Mode is Cash and joining date is {doc.joining_date}\n\nView Student: {frappe.utils.get_url_to_form('Student', doc.name)}"
        )
    elif doc.custom_mode_of_payment == "Service Order":
        # get all the users who have the role of "Accounts User"
        accountant_users = frappe.get_all("User", filters={"role": "Accounts User"}, fields=["email"])
        recipient_emails = [user.email for user in accountant_users]
        
        # send email notification to accountant
        frappe.sendmail(
            recipients=recipient_emails,
            subject=f"Service Order Payment for {doc.student_name}",
            message=f"Service Order for the student {doc.student_name} Payment Mode is Service Order and joining date is {doc.joining_date}\n\nView Student: {frappe.utils.get_url_to_form('Student', doc.name)}"
        )


def send_lms_welcome_email_to_user(doc, method):
    """Send LMS welcome email to users with LMS Student role"""
    
    # Check if user has LMS Student role
    user_roles = [role.role for role in doc.roles]
    
    if "LMS Student" in user_roles and doc.email:
        # Get the site domain for LMS URL
        site_domain = frappe.utils.get_url()
        lms_url = f"{site_domain}/lms"
        
        # Email template
        subject = "Welcome to Numerouno LMS - Start Your Learning Journey!"
        
        message = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
            <div style="background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #2e86ab; margin-bottom: 10px;">🎓 Welcome to Numerouno LMS!</h1>
                    <p style="color: #666; font-size: 16px;">Your learning journey starts here</p>
                </div>
                
                <div style="margin-bottom: 25px;">
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">
                        Hello <strong>{doc.first_name or 'Student'}</strong>,
                    </p>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">
                        Congratulations! Your account has been created and you now have access to our Learning Management System (LMS).
                    </p>
                </div>
                
                <div style="background-color: #f0f8ff; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
                    <h3 style="color: #2e86ab; margin-bottom: 15px;">📚 Your Learning Portal</h3>
                    <p style="color: #333; margin-bottom: 15px;">Access your courses, track progress, and start learning:</p>
                    <div style="text-align: center;">
                        <a href="{lms_url}" style="background-color: #2e86ab; color: white; padding: 12px 30px; text-decoration: none; border-radius: 25px; font-weight: bold; display: inline-block;">
                            🚀 Access LMS Portal
                        </a>
                    </div>
                </div>
                
                <div style="background-color: #f9f9f9; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
                    <h3 style="color: #333; margin-bottom: 15px;">🔐 Login Information</h3>
                    <p style="color: #333; margin-bottom: 10px;"><strong>Email:</strong> {doc.email}</p>
                    <p style="color: #333; margin-bottom: 10px;"><strong>LMS URL:</strong> <a href="{lms_url}" style="color: #2e86ab;">{lms_url}</a></p>
                    <p style="color: #666; font-size: 14px; font-style: italic;">
                        If this is your first login, you may need to reset your password using the "Forgot Password" link.
                    </p>
                </div>
                
                <div style="background-color: #e8f5e8; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
                    <h3 style="color: #2d5a2d; margin-bottom: 15px;">✨ What You Can Do</h3>
                    <ul style="color: #333; margin: 0; padding-left: 20px;">
                        <li style="margin-bottom: 8px;">📖 Access your enrolled courses</li>
                        <li style="margin-bottom: 8px;">📊 Track your learning progress</li>
                        <li style="margin-bottom: 8px;">📝 Take quizzes and assessments</li>
                        <li style="margin-bottom: 8px;">💬 Interact with instructors and peers</li>
                        <li style="margin-bottom: 8px;">🏆 Earn certificates upon completion</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                    <p style="color: #666; font-size: 14px;">
                        Need help? Contact us at <a href="mailto:support@numerouno.com" style="color: #2e86ab;">support@numerouno.com</a>
                    </p>
                    <p style="color: #999; font-size: 12px; margin-top: 15px;">
                        Happy Learning! 🌟<br>
                        The Numerouno Team
                    </p>
                </div>
            </div>
        </div>
        """
        
        try:
            frappe.sendmail(
                recipients=[doc.email],
                subject=subject,
                message=message,
                header=['Welcome to Numerouno LMS', 'green']
            )
            frappe.msgprint(f"LMS welcome email sent to {doc.email}")
        except Exception as e:
            frappe.log_error(f"Failed to send LMS welcome email to {doc.email}: {str(e)}", "LMS Welcome Email Error")


@frappe.whitelist()
def send_lms_email_to_user(user_email):
    """Manual function to send LMS welcome email to a specific user"""
    
    user_doc = frappe.get_doc("User", user_email)
    send_lms_welcome_email_to_user(user_doc, None)
    return f"LMS welcome email sent to {user_email}"


@frappe.whitelist()
def send_welcome_email_to_student(doc, method):
    # send welcome email to student andd a welcome message to student and good message to student
    if doc.student_email_id:
        frappe.msgprint(f"Email sent to {doc.student_name}")
        frappe.sendmail(
            recipients=[doc.student_email_id],
            subject="Welcome to Numerouno",
            message="Welcome to Numerouno and good luck for your future studies"
        )