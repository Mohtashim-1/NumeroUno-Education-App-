import frappe
from frappe.utils import getdate, add_days, nowdate
from frappe import _



@frappe.whitelist()
def create_coarse_schedule(student_group, from_time, to_time):
    try:
        if not student_group:
            frappe.throw(_("❌ Student Group is missing"))

        doc = frappe.get_doc("Student Group", student_group)

        if not doc.custom_from_date or not doc.custom_to_date:
            frappe.throw(_("❌ Please set both 'From Date' and 'To Date' in the Student Group."))

        if not doc.custom_coarse_location:
            frappe.throw(_(" ❌ Please set the 'Room' (Coarse Location) in the Student Group."))

        if not doc.instructors:
            frappe.throw(_("❌ No instructors found in this Student Group."))

        # Ensure every instructor child row has instructor selected
        for i in doc.instructors:
            if not i.instructor:
                frappe.throw(_(" ❌ Each row in 'Instructors' must have an Instructor selected."))

        if not doc.students:
            frappe.throw(_("❌ No students found in this Student Group."))

        from_date = getdate(doc.custom_from_date)
        to_date = getdate(doc.custom_to_date)

        for i in doc.instructors:
            instructor = i.instructor
            current_date = from_date

            while current_date <= to_date:
                # Create Course Schedule
                cs = frappe.new_doc("Course Schedule")
                cs.student_group = doc.name
                cs.course = doc.course
                cs.program = doc.program
                cs.instructor = instructor
                cs.schedule_date = current_date
                cs.room = doc.custom_coarse_location
                cs.from_time = from_time
                cs.to_time = to_time
                cs.flags.ignore_permissions = True
                cs.insert()

                for s in doc.students:
                    student = s.student

                    # Student Attendance
                    sa = frappe.new_doc("Student Attendance")
                    sa.student = student
                    sa.date = current_date
                    sa.course_schedule = cs.name
                    sa.student_group = doc.name
                    sa.status = "Present"
                    sa.flags.ignore_permissions = True
                    sa.insert()

                    # Student Card - only once
                    if not frappe.db.exists("Student Card", {"student": student, "student_group": doc.name}):
                        sc = frappe.new_doc("Student Card")
                        sc.student = student
                        sc.student_group = doc.name
                        sc.flags.ignore_permissions = True
                        sc.insert()

                frappe.db.commit()
                current_date = add_days(current_date, 1)

        frappe.msgprint(_("✅ All Course Schedule, Attendance, and Cards created from {0} to {1}").format(from_date, to_date))

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "❌ Error in create_coarse_schedule")
        frappe.throw(_("An error occurred while creating schedule. Please check error logs."))


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


@frappe.whitelist()
def create_sales_order(student_group, item_code, rate):
    student_group_doc = frappe.get_doc("Student Group", student_group)
    students = student_group_doc.students

    if not students:
        frappe.throw("No students in the group")

    qty = len(students)

    sales_order = frappe.new_doc("Sales Order")
    sales_order.customer = student_group_doc.custom_customer

    # ✅ Set delivery date to 7 days from now (or today, if preferred)
    sales_order.delivery_date = add_days(nowdate(), 7)

    sales_order.append("items", {
        "item_code": item_code,
        "qty": qty,
        "rate": rate
    })

    sales_order.insert()
    frappe.db.commit()

    return sales_order.name