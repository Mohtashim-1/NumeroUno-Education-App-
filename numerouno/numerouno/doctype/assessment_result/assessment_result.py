import frappe

@frappe.whitelist()
def create_bulk_assessment_results(assessment_plan, results_data):
    import json
    

    results_data = json.loads(results_data) if isinstance(results_data, str) else results_data

    if not results_data:
        frappe.throw("No result data found.")

    created = []
    
    # Get company - try multiple sources
    company = None
    try:
        # First try user default
        company = frappe.defaults.get_user_default("Company")
        if not company:
            # Try global default
            company = frappe.db.get_single_value("Global Defaults", "default_company")
        if not company:
            # Try system settings
            company = frappe.db.get_single_value("System Settings", "default_company")
        if not company:
            # Get first available company
            companies = frappe.get_all("Company", fields=["name"], limit=1)
            if companies:
                company = companies[0].name
        
        if not company:
            frappe.throw("No company found. Please set a default company in System Settings.")
            
        print(f"Using company: {company}")
        
    except Exception as e:
        print(f"Error getting company: {str(e)}")
        frappe.throw(f"Error getting company: {str(e)}")

    for row in results_data:
        if not row.get("student") or row.get("score") in [None, '']:
            continue

        try:
            doc = frappe.get_doc({
                "doctype": "Assessment Result",
                "assessment_plan": assessment_plan,
                "student": row.get("student"),
                "student_name": row.get("student_name"),
                "custom_company": company,
                "details": [
        {
            "assessment_criteria": row.get("assessment_criteria"),
            "score": float(row.get("score")),
            "comment": row.get("comment") or ""
        }
    ]
            })
            
            # Validate the document before inserting
            doc.validate()
            doc.insert()
            created.append(doc.name)
            print(f"Created assessment result: {doc.name} for student: {row.get('student')}")
            
        except Exception as e:
            print(f"Error creating assessment result for student {row.get('student')}: {str(e)}")
            frappe.throw(f"Error creating assessment result for student {row.get('student')}: {str(e)}")

    return created  # Return list of created docnames


@frappe.whitelist()
def get_students_for_plan(assessment_plan):
    plan = frappe.get_doc("Assessment Plan", assessment_plan)
    student_group = plan.student_group

    students = frappe.get_all("Student Group Student", 
        filters={"parent": student_group}, 
        fields=["student as name", "student_name"])

    return students