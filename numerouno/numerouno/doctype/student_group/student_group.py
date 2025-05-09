import frappe
from frappe.utils import getdate, add_days, nowdate
from frappe import _
from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
from frappe.model.document import Document



def sync_children(doc, method):
    for row in doc.students:
        # 1) always store the link back to this parent
        row.custom_student_group = doc.name

        # 2) mirror your parent’s date fields
        row.custom_start_date = doc.custom_from_date
        row.custom_end_date   = doc.custom_to_date

        # 3) mirror the course name
        row.custom_course_name = doc.course

        # 4) mirror the invoice if one exists
        row.custom_sales_invoice = doc.custom_sales_invoice or ""

        # 5) flag “invoiced” if you’ve actually set an invoice
        row.custom_invoiced = 1 if doc.custom_sales_invoice else 0


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
    sales_order.delivery_date = add_days(nowdate(), 7)

    sales_order.append("items", {
        "item_code": item_code,
        "qty": qty,
        "rate": rate
    })

    sales_order.insert()
    sales_order.submit()

    # ✅ Update custom field in Student Group
    student_group_doc.custom_sales_order = sales_order.name
    student_group_doc.save(ignore_permissions=True)

    frappe.db.commit()
    return sales_order.name

@frappe.whitelist()
def create_sales_invoice(student_group, sales_order):
    # 1) Load Student Group & validate
    sg = frappe.get_doc("Student Group", student_group)
    if not sg.students:
        frappe.throw(_("No students in the group"))

    # 2) Load the Sales Order and ensure it's submitted
    so = frappe.get_doc("Sales Order", sales_order)
    if so.docstatus == 0:
        so.submit()

    # 3) Build a new Sales Invoice manually (so items + sales_order link are present)
    si = frappe.new_doc("Sales Invoice")
    si.customer = so.customer
    si.company = so.company
    si.due_date = add_days(nowdate(), 7)
    # copy each item, including the sales_order link
    for row in so.get("items"):
        si.append("items", {
            "item_code":      row.item_code,
            "qty":            row.qty,
            "rate":           row.rate,
            "uom":            row.uom,
            "sales_order":    so.name,
            "description":    row.description,
            # add any other fields you need
        })

    # 4) insert & submit
    si.insert()
    si.submit()

    # 5) write back to Student Group
    sg.custom_sales_invoice = si.name
    sg.save(ignore_permissions=True)

    return si.name


@frappe.whitelist()
def create_sales_invoice_from_sales_order(sales_order):
    from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

    if not sales_order:
        frappe.throw("Sales Order is required")

    sales_order_doc = frappe.get_doc("Sales Order", sales_order)

    # ✅ Submit Sales Order if not submitted
    if sales_order_doc.docstatus == 0:
        sales_order_doc.submit()

    # ✅ Create Invoice from Sales Order
    invoice = make_sales_invoice(sales_order)
    invoice.due_date = add_days(nowdate(), 7)

    # 🛑 Handle missing income_account or other required fields if needed
    for item in invoice.items:
        if not item.income_account:
            item.income_account = frappe.db.get_value(
                "Item Default",
                {"parent": item.item_code},
                "income_account"
            ) or frappe.db.get_single_value("Company", invoice.company, "default_income_account")

    # ✅ Insert and Submit Invoice
    invoice.insert()
    invoice.submit()

    # ✅ Update Student Group with Sales Invoice reference
    student_group = sales_order_doc.get("custom_student_group")

    if student_group:
        sg_doc = frappe.get_doc("Student Group", student_group)
        sg_doc.custom_sales_invoice = invoice.name
        sg_doc.save(ignore_permissions=True)
        frappe.db.commit()
    else:
        frappe.log_error(f"❌ Sales Order {sales_order} has no custom_student_group", "Sales Invoice Link Failure")

    frappe.db.commit()
    return invoice.name
