import frappe
from frappe.utils import getdate, add_days
from frappe import _

@frappe.whitelist()
def create_coarse_schedule(student_group, from_time, to_time):
    doc = frappe.get_doc("Student Group", student_group)

    # Ensure both custom_from_date and custom_to_date are present
    if not doc.custom_from_date or not doc.custom_to_date:
        frappe.throw(_("Please set both 'From Date' and 'To Date' in the Student Group."))

    from_date = getdate(doc.custom_from_date)
    to_date = getdate(doc.custom_to_date)

    # Loop through instructors
    for i in doc.instructors:
        instructor = i.instructor

        # Loop through date range
        current_date = from_date
        while current_date <= to_date:
            cs = frappe.new_doc("Course Schedule")
            cs.student_group = doc.name
            cs.course = doc.course
            cs.instructor = instructor
            cs.schedule_date = current_date
            cs.room = doc.custom_coarse_location
            cs.from_time = from_time
            cs.to_time = to_time
            cs.save()

            current_date = add_days(current_date, 1)

    frappe.msgprint(_("Coarse Schedule created from {0} to {1}").format(from_date, to_date))


@frappe.whitelist()
def create_academic_term(doc, method):
    at = frappe.new_doc("Academic Term")
    education_settings = frappe.get_single("Education Settings")
    academic_year = education_settings.academic_year
    at.academic_year = academic_year
    at.term_start_date = doc.custom_from_date
    at.term_end_date = doc.custom_to_date
    at.save()