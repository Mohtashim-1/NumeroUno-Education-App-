import frappe

@frappe.whitelist()
def create_assessment_plan(student_group, assessment_data):
    import json

    # Parse and convert to Frappe dict
    assessment_data = frappe._dict(json.loads(assessment_data) if isinstance(assessment_data, str) else assessment_data)

    # Ensure child table exists in the input
    criteria = assessment_data.get("assessment_criteria", [])

    if not criteria:
        frappe.throw("Please provide assessment criteria.")

    total_score = sum([float(c.get("maximum_score", 0)) for c in criteria])

    if total_score != 100:
        frappe.throw("Sum of Scores of Assessment Criteria needs to be exactly 100. Currently it is {}".format(total_score))

    # Create the document
    doc = frappe.get_doc({
        'doctype': 'Assessment Plan',
        'student_group': student_group,
        'assessment_name': assessment_data.assessment_name,
        'assessment_group': assessment_data.assessment_group,
        'grading_scale': assessment_data.grading_scale,
        'examiner': assessment_data.examiner,
        'supervisor': assessment_data.supervisor,
        'schedule_date': assessment_data.schedule_date,
        'from_time': assessment_data.from_time,
        'to_time': assessment_data.to_time,
        'maximum_assessment_score': assessment_data.maximum_assessment_score,
        'assessment_criteria': [
            {
                'assessment_criteria': c.get('assessment_criteria'),
                'maximum_score': float(c.get('maximum_score'))
            } for c in criteria
        ]
    })

    doc.insert()
    return doc.name
