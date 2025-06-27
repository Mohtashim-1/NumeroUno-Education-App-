# unpaid_students_dashboard.py

import frappe
from frappe import _
from frappe.utils import nowdate, add_days

def execute(filters=None):
    filters = filters or {}
    
    # Get summary data
    summary_data = get_summary_data(filters)
    
    # Get chart data
    chart_data = get_chart_data(filters)
    
    # Get recent unpaid students
    recent_data = get_recent_unpaid_students(filters)
    
    # Create columns for recent data
    columns = [
        {"label": "Student Group",       "fieldname": "student_group_name", "fieldtype": "Link", "options": "Student Group", "width": 150},
        {"label": "Student",             "fieldname": "student",            "fieldtype": "Link", "options": "Student",        "width": 150},
        {"label": "Student Name",        "fieldname": "student_name",       "fieldtype": "Data",  "width": 150},
        {"label": "Program",             "fieldname": "program",            "fieldtype": "Data",  "width": 120},
        {"label": "Course",              "fieldname": "course",             "fieldtype": "Data",  "width": 150},
        {"label": "Days Unpaid",         "fieldname": "days_unpaid",        "fieldtype": "Int",   "width": 100},
        {"label": "Instructor",          "fieldname": "instructor_name",    "fieldtype": "Data",  "width": 150},
    ]
    
    # Create summary message
    summary = f"""
    <div style="display: flex; gap: 20px; margin-bottom: 20px;">
        <div style="background-color: #ff6b6b; color: white; padding: 20px; border-radius: 10px; flex: 1; text-align: center;">
            <h3 style="margin: 0; font-size: 24px;">{summary_data['total_unpaid']}</h3>
            <p style="margin: 5px 0 0 0;">Total Unpaid Students</p>
        </div>
        <div style="background-color: #4ecdc4; color: white; padding: 20px; border-radius: 10px; flex: 1; text-align: center;">
            <h3 style="margin: 0; font-size: 24px;">{summary_data['groups_affected']}</h3>
            <p style="margin: 5px 0 0 0;">Student Groups Affected</p>
        </div>
        <div style="background-color: #45b7d1; color: white; padding: 20px; border-radius: 10px; flex: 1; text-align: center;">
            <h3 style="margin: 0; font-size: 24px;">{summary_data['unique_students']}</h3>
            <p style="margin: 5px 0 0 0;">Unique Students</p>
        </div>
        <div style="background-color: #96ceb4; color: white; padding: 20px; border-radius: 10px; flex: 1; text-align: center;">
            <h3 style="margin: 0; font-size: 24px;">{summary_data['avg_days_unpaid']}</h3>
            <p style="margin: 5px 0 0 0;">Avg Days Unpaid</p>
        </div>
    </div>
    
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
        <h3>Quick Actions</h3>
        <p><strong>High Priority:</strong> {summary_data['high_priority']} students unpaid for more than 30 days</p>
        <p><strong>Medium Priority:</strong> {summary_data['medium_priority']} students unpaid for 15-30 days</p>
        <p><strong>Low Priority:</strong> {summary_data['low_priority']} students unpaid for less than 15 days</p>
    </div>
    """
    
    # Create charts
    charts = [
        {
            "title": "Unpaid Students by Student Group",
            "type": "Bar",
            "data": chart_data['by_group']
        },
        {
            "title": "Unpaid Students by Program",
            "type": "Pie",
            "data": chart_data['by_program']
        },
        {
            "title": "Unpaid Students by Days Unpaid",
            "type": "Bar",
            "data": chart_data['by_days']
        }
    ]
    
    return columns, recent_data, summary, charts

def get_summary_data(filters):
    """Get summary statistics"""
    
    # Base conditions
    conditions = ["(sgs.custom_invoiced = 0 OR sgs.custom_invoiced IS NULL)"]
    values = {}
    
    if filters.get("program"):
        conditions.append("sg.program = %(program)s")
        values["program"] = filters["program"]
    
    if filters.get("course"):
        conditions.append("sg.course = %(course)s")
        values["course"] = filters["course"]
    
    where_clause = "WHERE " + " AND ".join(conditions)
    
    # Get all unpaid students with their details
    unpaid_data = frappe.db.sql(f"""
        SELECT 
            sgs.student,
            sgs.student_name,
            sg.student_group_name,
            sg.program,
            sg.course,
            sg.from_date,
            sg.to_date,
            DATEDIFF(CURDATE(), COALESCE(sg.from_date, CURDATE())) as days_unpaid
        FROM `tabStudent Group` sg
        LEFT JOIN `tabStudent Group Student` sgs
          ON sgs.parent = sg.name
         AND sgs.parentfield = 'students'
        {where_clause}
    """, values, as_dict=True)
    
    total_unpaid = len(unpaid_data)
    unique_students = len(set([d.get("student") for d in unpaid_data]))
    groups_affected = len(set([d.get("student_group_name") for d in unpaid_data]))
    
    # Calculate average days unpaid
    total_days = sum([d.get("days_unpaid", 0) for d in unpaid_data])
    avg_days_unpaid = round(total_days / total_unpaid, 1) if total_unpaid > 0 else 0
    
    # Calculate priority levels
    high_priority = len([d for d in unpaid_data if d.get("days_unpaid", 0) > 30])
    medium_priority = len([d for d in unpaid_data if 15 <= d.get("days_unpaid", 0) <= 30])
    low_priority = len([d for d in unpaid_data if d.get("days_unpaid", 0) < 15])
    
    return {
        "total_unpaid": total_unpaid,
        "unique_students": unique_students,
        "groups_affected": groups_affected,
        "avg_days_unpaid": avg_days_unpaid,
        "high_priority": high_priority,
        "medium_priority": medium_priority,
        "low_priority": low_priority
    }

def get_chart_data(filters):
    """Get data for charts"""
    
    # Base conditions
    conditions = ["(sgs.custom_invoiced = 0 OR sgs.custom_invoiced IS NULL)"]
    values = {}
    
    if filters.get("program"):
        conditions.append("sg.program = %(program)s")
        values["program"] = filters["program"]
    
    if filters.get("course"):
        conditions.append("sg.course = %(course)s")
        values["course"] = filters["course"]
    
    where_clause = "WHERE " + " AND ".join(conditions)
    
    # Chart 1: By Student Group
    by_group_data = frappe.db.sql(f"""
        SELECT 
            sg.student_group_name,
            COUNT(sgs.name) as count
        FROM `tabStudent Group` sg
        LEFT JOIN `tabStudent Group Student` sgs
          ON sgs.parent = sg.name
         AND sgs.parentfield = 'students'
        {where_clause}
        GROUP BY sg.student_group_name
        ORDER BY count DESC
        LIMIT 10
    """, values, as_dict=True)
    
    by_group = {
        "labels": [d.get("student_group_name") for d in by_group_data],
        "datasets": [{"name": "Unpaid Students", "values": [d.get("count") for d in by_group_data]}]
    }
    
    # Chart 2: By Program
    by_program_data = frappe.db.sql(f"""
        SELECT 
            COALESCE(sg.program, 'No Program') as program,
            COUNT(sgs.name) as count
        FROM `tabStudent Group` sg
        LEFT JOIN `tabStudent Group Student` sgs
          ON sgs.parent = sg.name
         AND sgs.parentfield = 'students'
        {where_clause}
        GROUP BY sg.program
        ORDER BY count DESC
        LIMIT 8
    """, values, as_dict=True)
    
    by_program = {
        "labels": [d.get("program") for d in by_program_data],
        "datasets": [{"name": "Unpaid Students", "values": [d.get("count") for d in by_program_data]}]
    }
    
    # Chart 3: By Days Unpaid
    by_days_data = frappe.db.sql(f"""
        SELECT 
            CASE 
                WHEN DATEDIFF(CURDATE(), COALESCE(sg.from_date, CURDATE())) <= 7 THEN '0-7 days'
                WHEN DATEDIFF(CURDATE(), COALESCE(sg.from_date, CURDATE())) <= 15 THEN '8-15 days'
                WHEN DATEDIFF(CURDATE(), COALESCE(sg.from_date, CURDATE())) <= 30 THEN '16-30 days'
                WHEN DATEDIFF(CURDATE(), COALESCE(sg.from_date, CURDATE())) <= 60 THEN '31-60 days'
                ELSE '60+ days'
            END as days_range,
            COUNT(sgs.name) as count
        FROM `tabStudent Group` sg
        LEFT JOIN `tabStudent Group Student` sgs
          ON sgs.parent = sg.name
         AND sgs.parentfield = 'students'
        {where_clause}
        GROUP BY days_range
        ORDER BY 
            CASE days_range
                WHEN '0-7 days' THEN 1
                WHEN '8-15 days' THEN 2
                WHEN '16-30 days' THEN 3
                WHEN '31-60 days' THEN 4
                ELSE 5
            END
    """, values, as_dict=True)
    
    by_days = {
        "labels": [d.get("days_range") for d in by_days_data],
        "datasets": [{"name": "Unpaid Students", "values": [d.get("count") for d in by_days_data]}]
    }
    
    return {
        "by_group": by_group,
        "by_program": by_program,
        "by_days": by_days
    }

def get_recent_unpaid_students(filters):
    """Get recent unpaid students for the table"""
    
    # Base conditions
    conditions = ["(sgs.custom_invoiced = 0 OR sgs.custom_invoiced IS NULL)"]
    values = {}
    
    if filters.get("program"):
        conditions.append("sg.program = %(program)s")
        values["program"] = filters["program"]
    
    if filters.get("course"):
        conditions.append("sg.course = %(course)s")
        values["course"] = filters["course"]
    
    where_clause = "WHERE " + " AND ".join(conditions)
    
    # Get recent unpaid students
    recent_data = frappe.db.sql(f"""
        SELECT 
            sg.student_group_name,
            sgs.student,
            sgs.student_name,
            sg.program,
            sg.course,
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
        ORDER BY days_unpaid DESC, sg.student_group_name
        LIMIT 50
    """, values, as_dict=True)
    
    return recent_data