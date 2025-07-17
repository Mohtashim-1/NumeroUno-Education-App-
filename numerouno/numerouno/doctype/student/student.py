# frappe-bench/apps/your_app/your_app/student_custom.py

import frappe
from frappe import _
import frappe.utils

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

            # 1. Get or create User
            user = frappe.db.get_value("User", {"email": user_email})
            if not user:
                user_doc = frappe.new_doc("User")
                user_doc.email = user_email
                user_doc.first_name = user_first_name
                user_doc.last_name = user_last_name
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
        frappe.log_error(f"assign_student_group error: {str(e)}\n{traceback.format_exc()}")
        raise

#  run this function when document created it is custom app so i guess it will run on student application created through hooks.py


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