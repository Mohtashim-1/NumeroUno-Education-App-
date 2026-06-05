import frappe
from frappe import _
from frappe.utils import cint

from numerouno.numerouno.utils.student_invoice_sync import (
	backfill_invoiced_students_from_sales_invoices,
)


def _log_fetch_students(message, level="info"):
    try:
        getattr(frappe.logger(), level)(message)
    except Exception:
        pass


@frappe.whitelist()
def fetch_students_group(customer):
    """Fetch Student Groups for a specific customer"""
    try:
        # Get all Student Groups for the customer
        student_groups = frappe.get_all(
            "Student Group",
            filters={"custom_customer": customer},
            fields=["name"]
        )
        
        return [sg.name for sg in student_groups]
        
    except Exception:
        frappe.log_error(
            title="fetch_students_group failed",
            message=f"customer: {customer}\n{frappe.get_traceback()}",
        )
        return []

@frappe.whitelist()
def fetch_students_from_sg(customer, student_group, exclude_invoiced=True, current_invoice=None):
    """Fetch students from selected Student Groups
    
    Args:
        customer: Customer name
        student_group: Student group name(s) - can be string, list, or JSON string
        exclude_invoiced: If True, exclude students already in draft/submitted invoices (default: True)
        current_invoice: Sales Invoice name to ignore while refetching an existing draft
    """
    try:
        exclude_invoiced = cint(exclude_invoiced)
        students_data = []
        
        # Debug logging
        _log_fetch_students(f"fetch_students_from_sg called with customer: {customer}")
        _log_fetch_students(f"fetch_students_from_sg called with student_group: {student_group}")
        _log_fetch_students(f"student_group type: {type(student_group)}")
        
        # Handle different input formats
        if isinstance(student_group, str):
            # If it's a string, try to parse it as JSON or split by comma
            import json
            try:
                # Try to parse as JSON first
                student_group = json.loads(student_group)
            except Exception:
                # If not JSON, split by comma and clean up
                student_group = [sg.strip().replace('"', '').replace('[', '').replace(']', '') 
                               for sg in student_group.split(',') if sg.strip()]
        
        # Ensure student_group is a list
        if not isinstance(student_group, list):
            student_group = [student_group]
        
        student_group = [
            str(sg).strip().replace('"', '').replace('[', '').replace(']', '')
            for sg in student_group
            if sg
        ]
        
        _log_fetch_students(f"Processed student_group list: {student_group}")
        
        # Pending for invoicing means the student/group pair is not on another
        # draft or submitted Sales Invoice. Ignore the current invoice so a saved
        # draft can be rebuilt without losing its own rows.
        invoiced_students_by_group = set()
        if exclude_invoiced and student_group:
            exclude_current_invoice = ""
            values = {"student_groups": tuple(student_group)}
            if (
                current_invoice
                and not str(current_invoice).startswith("new-")
                and frappe.db.get_value("Sales Invoice", current_invoice, "docstatus") == 0
            ):
                exclude_current_invoice = "AND si.name != %(current_invoice)s"
                values["current_invoice"] = current_invoice

            invoiced_student_records = frappe.db.sql(
                f"""
                SELECT sis.student, sis.student_group
                FROM `tabSales Invoice Student` sis
                INNER JOIN `tabSales Invoice` si
                    ON si.name = sis.parent
                    AND si.docstatus IN (0, 1)
                    {exclude_current_invoice}
                WHERE sis.student_group IN %(student_groups)s
                    AND sis.student IS NOT NULL
                    AND sis.student_group IS NOT NULL
                    AND sis.student_group != ''
                GROUP BY sis.student, sis.student_group
                """,
                values,
                as_dict=True,
            )
            
            invoiced_students_by_group = {
                (record.student, record.student_group)
                for record in invoiced_student_records
                if record.student and record.student_group
            }
            _log_fetch_students(
                f"Found {len(invoiced_students_by_group)} non-pending student-group combinations"
            )
        
        for sg_name in student_group:
            if not sg_name:
                continue
                
            _log_fetch_students(f"Processing student group: {sg_name}")
            
            # Check if the Student Group exists
            if not frappe.db.exists("Student Group", sg_name):
                _log_fetch_students(f"Student Group {sg_name} does not exist!", "error")
                continue
                
            # Get the Student Group
            sg_doc = frappe.get_doc("Student Group", sg_name)
            
            # Get students from the Student Group
            for student_row in sg_doc.students:
                # Skip if student is already in another draft/submitted invoice for this student group.
                if exclude_invoiced and (student_row.student, sg_name) in invoiced_students_by_group:
                    _log_fetch_students(f"Skipping non-pending student: {student_row.student} for group: {sg_name}")
                    continue
                
                student_data = {
                    "student": student_row.student,
                    "student_name": student_row.student_name,
                    "course_name": sg_doc.course,
                    "student_group": sg_name,
                    "start_date": sg_doc.from_date,
                    "end_date": sg_doc.to_date
                }
                students_data.append(student_data)
        
        _log_fetch_students(f"Returning {len(students_data)} students (after excluding invoiced)")
        return students_data
        
    except Exception as e:
        _log_fetch_students(f"Error fetching students from student groups: {str(e)}", "error")
        frappe.throw(f"Error fetching students: {str(e)}")
        return []


@frappe.whitelist()
def run_student_invoice_backfill():
	"""Sync Student Group Student invoice flags from all submitted Sales Invoices."""
	frappe.only_for(("System Manager", "Administrator"))
	return backfill_invoiced_students_from_sales_invoices()
