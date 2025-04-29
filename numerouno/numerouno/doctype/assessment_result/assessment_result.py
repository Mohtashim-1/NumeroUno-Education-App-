import frappe

@frappe.whitelist()
def create_bulk_assessment_results(assessment_plan, results_data):
    import json
    

    results_data = json.loads(results_data) if isinstance(results_data, str) else results_data

    if not results_data:
        frappe.throw("No result data found.")

    created = []
    
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")

    for row in results_data:
        if not row.get("student") or row.get("score") in [None, '']:
            continue

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
        doc.insert()
        created.append(doc.name)

    return created  # Return list of created docnames


@frappe.whitelist()
def get_students_for_plan(assessment_plan):
    plan = frappe.get_doc("Assessment Plan", assessment_plan)
    student_group = plan.student_group

    students = frappe.get_all("Student Group Student", 
        filters={"parent": student_group}, 
        fields=["student as name", "student_name"])

    return students