# student_payment_summary.py

import frappe
from frappe import _
from frappe.utils import nowdate, add_days

def execute(filters=None):
    filters = filters or {}
    
    # Get comprehensive payment data
    payment_data = get_payment_summary_data(filters)
    
    # Create columns for detailed breakdown with better alignment
    columns = [
        {"label": "Student Group",       "fieldname": "student_group_name", "fieldtype": "Link", "options": "Student Group", "width": 180, "align": "left"},
        {"label": "Student",             "fieldname": "student",            "fieldtype": "Link", "options": "Student",        "width": 150, "align": "left"},
        {"label": "Student Name",        "fieldname": "student_name",       "fieldtype": "Data",  "width": 180, "align": "left"},
        {"label": "Program",             "fieldname": "program",            "fieldtype": "Data",  "width": 140, "align": "left"},
        {"label": "Course",              "fieldname": "course",             "fieldtype": "Data",  "width": 160, "align": "left"},
        {"label": "Payment Status",      "fieldname": "payment_status",     "fieldtype": "Data",  "width": 120, "align": "center"},
        {"label": "Days Unpaid",         "fieldname": "days_unpaid",        "fieldtype": "Int",   "width": 100, "align": "center"},
        {"label": "Instructor",          "fieldname": "instructor_name",    "fieldtype": "Data",  "width": 160, "align": "left"},
    ]
    
    # Create comprehensive summary with explanations
    summary = f"""
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
        <h2 style="color: #2c3e50; margin-bottom: 15px;">Student Payment Summary - Definitions & Statistics</h2>
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px;">
            <div style="background-color: #ff6b6b; color: white; padding: 20px; border-radius: 10px; text-align: center;">
                <h3 style="margin: 0; font-size: 28px;">{payment_data['total_unpaid']}</h3>
                <p style="margin: 5px 0 0 0; font-weight: bold;">Total Unpaid Students</p>
                <p style="margin: 5px 0 0 0; font-size: 12px;">All unpaid student enrollments across all groups</p>
            </div>
            <div style="background-color: #4ecdc4; color: white; padding: 20px; border-radius: 10px; text-align: center;">
                <h3 style="margin: 0; font-size: 28px;">{payment_data['unique_unpaid_students']}</h3>
                <p style="margin: 5px 0 0 0; font-weight: bold;">Unique Unpaid Students</p>
                <p style="margin: 5px 0 0 0; font-size: 12px;">Individual students who haven't paid (no duplicates)</p>
            </div>
            <div style="background-color: #45b7d1; color: white; padding: 20px; border-radius: 10px; text-align: center;">
                <h3 style="margin: 0; font-size: 28px;">{payment_data['total_paid']}</h3>
                <p style="margin: 5px 0 0 0; font-weight: bold;">Total Paid Students</p>
                <p style="margin: 5px 0 0 0; font-size: 12px;">All paid student enrollments across all groups</p>
            </div>
            <div style="background-color: #96ceb4; color: white; padding: 20px; border-radius: 10px; text-align: center;">
                <h3 style="margin: 0; font-size: 28px;">{payment_data['unique_paid_students']}</h3>
                <p style="margin: 5px 0 0 0; font-weight: bold;">Unique Paid Students</p>
                <p style="margin: 5px 0 0 0; font-size: 12px;">Individual students who have paid (no duplicates)</p>
            </div>
        </div>
        
        <div style="background-color: white; padding: 15px; border-radius: 8px; border-left: 4px solid #3498db;">
            <h3 style="color: #2c3e50; margin-bottom: 10px;">📋 Key Definitions:</h3>
            <ul style="margin: 0; padding-left: 20px;">
                <li><strong>Total Unpaid Students:</strong> Counts every unpaid enrollment. If a student is in 3 groups and unpaid in all, they count as 3.</li>
                <li><strong>Unique Unpaid Students:</strong> Counts individual students who haven't paid, regardless of how many groups they're in.</li>
                <li><strong>Total Paid Students:</strong> Counts every paid enrollment. If a student is in 3 groups and paid in all, they count as 3.</li>
                <li><strong>Unique Paid Students:</strong> Counts individual students who have paid, regardless of how many groups they're in.</li>
            </ul>
        </div>
        
        <div style="background-color: white; padding: 15px; border-radius: 8px; border-left: 4px solid #e74c3c; margin-top: 15px;">
            <h3 style="color: #2c3e50; margin-bottom: 10px;">⚠️ Example Scenario:</h3>
            <p style="margin: 0;">Student "John Doe" is enrolled in 3 different Student Groups:</p>
            <ul style="margin: 5px 0 0 0; padding-left: 20px;">
                <li>Group A: <span style="color: #e74c3c;">Unpaid</span></li>
                <li>Group B: <span style="color: #e74c3c;">Unpaid</span></li>
                <li>Group C: <span style="color: #27ae60;">Paid</span></li>
            </ul>
            <p style="margin: 5px 0 0 0;"><strong>Result:</strong> John contributes 2 to "Total Unpaid", 1 to "Total Paid", 1 to "Unique Unpaid", and 1 to "Unique Paid".</p>
        </div>
    </div>
    
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
        <h3>Payment Statistics</h3>
        <p><strong>Payment Rate:</strong> {payment_data['payment_rate']}% of all enrollments are paid</p>
        <p><strong>Student Groups with Unpaid Students:</strong> {payment_data['groups_with_unpaid']}</p>
        <p><strong>Student Groups with All Paid:</strong> {payment_data['groups_all_paid']}</p>
        <p><strong>Average Days Unpaid:</strong> {payment_data['avg_days_unpaid']} days</p>
    </div>
    """
    
    # Create charts
    charts = [
        {
            "title": "Payment Status Overview",
            "type": "Pie",
            "data": payment_data['payment_overview_chart']
        },
        {
            "title": "Unpaid Students by Student Group",
            "type": "Bar",
            "data": payment_data['unpaid_by_group_chart']
        },
        {
            "title": "Payment Rate by Program",
            "type": "Bar",
            "data": payment_data['payment_rate_by_program_chart']
        }
    ]
    
    return columns, payment_data['detailed_data'], summary, charts

def get_payment_summary_data(filters):
    """Get comprehensive payment statistics"""
    
    # Base conditions
    conditions = []
    values = {}
    
    if filters.get("program"):
        conditions.append("sg.program = %(program)s")
        values["program"] = filters["program"]
    
    if filters.get("course"):
        conditions.append("sg.course = %(course)s")
        values["course"] = filters["course"]
    
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    # Get all student enrollments with payment status
    all_data = frappe.db.sql(f"""
        SELECT 
            sgs.student,
            sgs.student_name,
            sgs.custom_invoiced,
            sg.student_group_name,
            sg.program,
            sg.course,
            sg.from_date,
            sg.to_date,
            DATEDIFF(CURDATE(), COALESCE(sg.from_date, CURDATE())) as days_unpaid,
            sgi.instructor_name
        FROM `tabStudent Group` sg
        LEFT JOIN `tabStudent Group Student` sgs
          ON sgs.parent = sg.name
         AND sgs.parentfield = 'students'
        LEFT JOIN `tabStudent Group Instructor` sgi
          ON sgi.parent = sg.name
         AND sgi.parentfield = 'instructors'
        {where_clause}
    """, values, as_dict=True)
    
    # Separate paid and unpaid data
    unpaid_data = [d for d in all_data if not d.get("custom_invoiced")]
    paid_data = [d for d in all_data if d.get("custom_invoiced")]
    
    # Calculate statistics
    total_unpaid = len(unpaid_data)
    total_paid = len(paid_data)
    total_enrollments = len(all_data)
    
    unique_unpaid_students = len(set([d.get("student") for d in unpaid_data]))
    unique_paid_students = len(set([d.get("student") for d in paid_data]))
    
    # Calculate payment rate
    payment_rate = round((total_paid / total_enrollments) * 100, 1) if total_enrollments > 0 else 0
    
    # Calculate groups affected
    groups_with_unpaid = len(set([d.get("student_group_name") for d in unpaid_data]))
    groups_all_paid = len(set([d.get("student_group_name") for d in all_data])) - groups_with_unpaid
    
    # Calculate average days unpaid
    total_days = sum([d.get("days_unpaid", 0) for d in unpaid_data])
    avg_days_unpaid = round(total_days / total_unpaid, 1) if total_unpaid > 0 else 0
    
    # Prepare detailed data for the table
    detailed_data = []
    for row in all_data:
        payment_status = "Paid" if row.get("custom_invoiced") else "Unpaid"
        days_unpaid = row.get("days_unpaid", 0) if not row.get("custom_invoiced") else 0
        
        detailed_data.append({
            "student_group_name": row.get("student_group_name"),
            "student": row.get("student"),
            "student_name": row.get("student_name"),
            "program": row.get("program"),
            "course": row.get("course"),
            "payment_status": payment_status,
            "days_unpaid": days_unpaid,
            "instructor_name": row.get("instructor_name")
        })
    
    # Sort by payment status (unpaid first) then by days unpaid
    detailed_data.sort(key=lambda x: (x["payment_status"] == "Paid", x["days_unpaid"]), reverse=True)
    
    # Create chart data
    payment_overview_chart = {
        "labels": ["Paid Students", "Unpaid Students"],
        "datasets": [{"name": "Students", "values": [total_paid, total_unpaid]}]
    }
    
    # Unpaid by group chart
    unpaid_by_group = {}
    for row in unpaid_data:
        group = row.get("student_group_name", "Unknown")
        unpaid_by_group[group] = unpaid_by_group.get(group, 0) + 1
    
    unpaid_by_group_chart = {
        "labels": list(unpaid_by_group.keys())[:10],
        "datasets": [{"name": "Unpaid Students", "values": list(unpaid_by_group.values())[:10]}]
    }
    
    # Payment rate by program
    program_stats = {}
    for row in all_data:
        program = row.get("program", "No Program")
        if program not in program_stats:
            program_stats[program] = {"total": 0, "paid": 0}
        program_stats[program]["total"] += 1
        if row.get("custom_invoiced"):
            program_stats[program]["paid"] += 1
    
    payment_rate_by_program_chart = {
        "labels": list(program_stats.keys()),
        "datasets": [{"name": "Payment Rate %", "values": [round((stats["paid"] / stats["total"]) * 100, 1) for stats in program_stats.values()]}]
    }
    
    return {
        "total_unpaid": total_unpaid,
        "total_paid": total_paid,
        "unique_unpaid_students": unique_unpaid_students,
        "unique_paid_students": unique_paid_students,
        "payment_rate": payment_rate,
        "groups_with_unpaid": groups_with_unpaid,
        "groups_all_paid": groups_all_paid,
        "avg_days_unpaid": avg_days_unpaid,
        "detailed_data": detailed_data,
        "payment_overview_chart": payment_overview_chart,
        "unpaid_by_group_chart": unpaid_by_group_chart,
        "payment_rate_by_program_chart": payment_rate_by_program_chart
    } 