import frappe
from frappe.utils import getdate, add_days
from frappe import _


@frappe.whitelist()
def create_coarse_schedule(student_group, from_time, to_time):
    doc = frappe.get_doc("Student Group", student_group)

    if not doc.custom_from_date or not doc.custom_to_date:
        frappe.throw(_("Please set both 'From Date' and 'To Date' in the Student Group."))

    from_date = getdate(doc.custom_from_date)
    to_date = getdate(doc.custom_to_date)

    for i in doc.instructors:
        instructor = i.instructor
        current_date = from_date

        while current_date <= to_date:
            # Create the course schedule
            cs = frappe.new_doc("Course Schedule")
            cs.student_group = doc.name
            cs.course = doc.course
            cs.program = doc.program
            cs.instructor = instructor
            cs.schedule_date = current_date
            cs.room = doc.custom_coarse_location
            cs.from_time = from_time
            cs.to_time = to_time
            cs.save()

            # Create student attendance for this schedule
            for s in doc.students:
                sa = frappe.new_doc("Student Attendance")
                sa.student = s.student
                sa.date = current_date
                sa.course_schedule = cs.name
                sa.student_group = doc.name
                sa.status = "Present"  # or set as "Not Marked" initially
                sa.insert()
            
            # Create Student Card only once per student
            if not frappe.db.exists("Student Card", {"student": s.student, "student_group": doc.name}):
                sc = frappe.new_doc("Student Card")
                sc.student = s.student
                sc.student_group = doc.name
                # Add other fields if needed here
                sc.insert()

            current_date = add_days(current_date, 1)

    frappe.msgprint(_("Course Schedule, Student Attendance, and Student Cards created from {0} to {1}").format(from_date, to_date))


def create_academic_term(doc, method):
    if not (doc.custom_from_date and doc.custom_to_date and doc.academic_year):
        return  # Exit silently if any required field is missing

    if not doc.academic_term:
        existing_term = frappe.get_value(
            "Academic Term",
            {
                "term_start_date": doc.custom_from_date,
                "term_end_date": doc.custom_to_date,
                "academic_year": doc.academic_year
            }
        )

        if existing_term:
            doc.academic_term = existing_term
            return

        term_name = f"{doc.custom_from_date} to {doc.custom_to_date}"
        at = frappe.new_doc("Academic Term")
        at.academic_year = doc.academic_year
        at.term_name = term_name
        at.term_start_date = doc.custom_from_date
        at.term_end_date = doc.custom_to_date
        at.save()

        doc.academic_term = at.name
