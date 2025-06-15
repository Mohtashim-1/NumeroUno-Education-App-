# student_group_students.py

import frappe

def execute(filters=None):
    filters = filters or {}
    conditions = []
    values = {}

    # — your existing filters
    if filters.get("program"):
        conditions.append("sg.program = %(program)s")
        values["program"] = filters["program"]

    if filters.get("course"):
        conditions.append("sg.course = %(course)s")
        values["course"] = filters["course"]

    if filters.get("customer"):
        conditions.append("sg.custom_customer = %(customer)s")
        values["customer"] = filters["customer"]

    # — your date filters
    if filters.get("from_date"):
        conditions.append("sg.from_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("sg.to_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    # build WHERE clause *only* if you have any conditions
    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    data = frappe.db.sql(f"""
        SELECT
            sg.name                   AS id,
            sg.custom_customer        AS customer,
            sg.custom_sales_order     AS sales_order,
            sg.custom_sales_invoice   AS sales_invoice,
            sg.program                AS program,
            sg.course                 AS course,
            sg.from_date       AS from_date,
            sg.to_date         AS to_date,
            st.student                AS student,
            st.student_name           AS student_name,
            st.custom_invoiced        AS invoiced,
            st.custom_sales_invoice   AS student_invoice
        FROM `tabStudent Group` sg
        LEFT JOIN `tabStudent Group Student` st
          ON st.parent = sg.name
         AND st.parentfield = 'students'
        {where_clause}
    """, values, as_dict=True)

    columns = [
        {"label": "ID",               "fieldname": "id",             "fieldtype": "Link",  "options": "Student Group",   "width": 120},
        {"label": "Customer",         "fieldname": "customer",       "fieldtype": "Link",  "options": "Customer",        "width": 150},
        {"label": "Sales Order",      "fieldname": "sales_order",    "fieldtype": "Link",  "options": "Sales Order",     "width": 150},
        {"label": "Sales Invoice",    "fieldname": "sales_invoice",  "fieldtype": "Link",  "options": "Sales Invoice",   "width": 150},
        {"label": "Program",          "fieldname": "program",        "fieldtype": "Data",  "width": 120},
        {"label": "Course",           "fieldname": "course",         "fieldtype": "Data",  "width": 150},
        {"label": "From Date",        "fieldname": "from_date",      "fieldtype": "Date",  "width": 100},
        {"label": "To Date",          "fieldname": "to_date",        "fieldtype": "Date",  "width": 100},
        {"label": "Student",          "fieldname": "student",        "fieldtype": "Link",  "options": "Student",         "width": 150},
        {"label": "Student Name",     "fieldname": "student_name",   "fieldtype": "Data",  "width": 150},
        {"label": "Invoiced",         "fieldname": "invoiced",       "fieldtype": "Check", "width":  80},
        {"label": "Student Invoice",  "fieldname": "student_invoice","fieldtype": "Link",  "options": "Sales Invoice",   "width": 150},
    ]

    # build our pie‐slice values
    total = len(data)
    invoiced_count = sum(1 for d in data if d.get("invoiced"))
    uninvoiced_count = total - invoiced_count

    # chart config
    chart = {
        "data": {
            "labels": ["Invoiced", "Uninvoiced"],
            "datasets": [
                {
                    "name": "Students",
                    "values": [invoiced_count, uninvoiced_count]
                }
            ]
        },
        "type": "pie"
    }

    # return: columns, data, (no message), chart
    return columns, data, None, chart
