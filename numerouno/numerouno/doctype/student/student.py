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
    # assign student group 
    group = frappe.get_doc("Student Group", student_group)
    
    if not any(s.student == student for s in group.students):
        group.append("students",{
            "student": student
        })
        group.save(ignore_permissions=True)
        
    return {
        "name":group.name,
        "url":frappe.utils.get_url_to_form("Student Group",group.name)
    }