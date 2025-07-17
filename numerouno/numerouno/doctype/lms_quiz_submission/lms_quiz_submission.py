import frappe
from frappe.model.document import Document
from frappe.utils import cint
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import make_notification_logs



def on_submit(doc, method=None):
    try:
        print(_("[DEBUG] on_submit called for LMS Quiz Submission: {}".format(doc.name)))
        # 1. Find the Student linked to this User (member)
        user = doc.member
        print(_(f"[DEBUG] member/user: {user}"))
        student = frappe.db.get_value("Student", {"user": user})
        print(_(f"[DEBUG] student by user: {student}"))
        if not student:
            # Try by email if user field is not set
            student = frappe.db.get_value("Student", {"student_email_id": user})
            print(_(f"[DEBUG] student by email: {student}"))
        if not student:
            msg = f"No Student found for user/member: {user}"
            print(_(f"[DEBUG] {msg}"))
            frappe.log_error(msg, "LMSQuizSubmission on_submit error")
            return

        # 2. Find or create Assessment Plan for the course (Education Course, not LMS Course)
        lms_course = doc.course
        course_name = None
        edu_course = None
        if lms_course:
            course_name = frappe.db.get_value("LMS Course", lms_course, "title")
            print(_(f"[DEBUG] lms_course: {lms_course}, course_name: {course_name}"))
            # Try to find Education Course with this name
            edu_course = frappe.db.get_value("Course", {"course_name": course_name})
            print(_(f"[DEBUG] edu_course: {edu_course}"))
        assessment_plan = None
        if edu_course:
            # Get the latest submitted Assessment Plan for this course
            plans = frappe.get_all(
                "Assessment Plan",
                filters={"course": edu_course, "docstatus": 1},
                order_by="creation desc",
                limit=1
            )
            print(_(f"[DEBUG] assessment plans found: {plans}"))
            if plans:
                assessment_plan = plans[0].name
        if not assessment_plan:
            print(_("[DEBUG] No Assessment Plan found, creating one..."))
            # Find or create Assessment Group
            assessment_group = frappe.db.get_value("Assessment Group", {"assessment_group_name": "Default"})
            if not assessment_group:
                ag_doc = frappe.new_doc("Assessment Group")
                ag_doc.assessment_group_name = "Default"
                ag_doc.parent_assessment_group = "All Assessment Groups"  # root group
                ag_doc.save(ignore_permissions=True)
                assessment_group = ag_doc.name
                print(_(f"[DEBUG] Created Assessment Group: {assessment_group}"))
            # Find or create Grading Scale
            grading_scale = frappe.db.get_value("Grading Scale", {"grading_scale_name": "PASS OR FAIL"})
            if not grading_scale:
                gs_doc = frappe.new_doc("Grading Scale")
                gs_doc.grading_scale_name = "Default"
                gs_doc.save(ignore_permissions=True)
                grading_scale = gs_doc.name
                print(_(f"[DEBUG] Created Grading Scale: {grading_scale}"))
            # Find or create Student Group for the course
            student_group = frappe.db.get_value("Student Group", {"course": edu_course})
            if not student_group:
                sg_doc = frappe.new_doc("Student Group")
                sg_doc.course = edu_course
                sg_doc.student_group_name = f"Auto-{edu_course}"
                sg_doc.save(ignore_permissions=True)
                student_group = sg_doc.name
                print(_(f"[DEBUG] Created Student Group: {student_group}"))
            # Create Assessment Plan
            ap_doc = frappe.new_doc("Assessment Plan")
            ap_doc.course = edu_course
            ap_doc.student_group = student_group
            ap_doc.assessment_group = assessment_group
            ap_doc.grading_scale = grading_scale
            ap_doc.maximum_assessment_score = doc.score_out_of or 0
            ap_doc.assessment_name = doc.quiz_title or "Quiz Assessment"
            ap_doc.append("assessment_criteria", {
                "assessment_criteria": "Practical Assessment",
                "maximum_score": doc.score_out_of or 0
            })
            ap_doc.schedule_date = frappe.utils.nowdate()
            ap_doc.from_time = "09:00:00"
            ap_doc.to_time = "10:00:00"
            ap_doc.save(ignore_permissions=True)
            ap_doc.submit()
            assessment_plan = ap_doc.name
            print(_(f"[DEBUG] Created Assessment Plan: {assessment_plan}"))

        # 3. Prepare details table (single row, as quiz is one criteria)
        details = []
        # Try to get assessment criteria from plan
        criteria = frappe.get_all(
            "Assessment Plan Criteria",
            filters={"parent": assessment_plan},
            fields=["assessment_criteria", "maximum_score"],
            order_by="idx"
        )
        print(_(f"[DEBUG] assessment plan criteria: {criteria}"))
        if criteria:
            # If multiple, just use the first for now
            details.append({
                "assessment_criteria": criteria[0].assessment_criteria,
                "maximum_score": criteria[0].maximum_score,
                "score": doc.score,
            })
        else:
            # Fallback: create a dummy criteria
            details.append({
                "assessment_criteria": _(doc.quiz_title or "Quiz"),
                "maximum_score": doc.score_out_of or 0,
                "score": doc.score,
            })
        print(_(f"[DEBUG] details for Assessment Result: {details}"))

        # 4. Create Assessment Result
        ar = frappe.new_doc("Assessment Result")
        ar.assessment_plan = assessment_plan
        ar.student = student
        ar.total_score = doc.score
        for d in details:
            ar.append("details", d)
        # Set custom_company from global defaults if the field exists
        if hasattr(ar, "custom_company"):
            ar.custom_company = frappe.defaults.get_global_default("company")
        print(_(f"[DEBUG] Saving Assessment Result for student: {student}, plan: {assessment_plan}"))
        assessment_result = frappe.get_list(
            "Assessment Result",
            filters={"assessment_plan": assessment_plan, "student": student},
            ignore_permissions=True
        )
        if assessment_result:
            ar.name = assessment_result[0].name
            print(_(f"[DEBUG] Assessment Result already exists, updating: {ar.name}"))
        else:
            ar.save(ignore_permissions=True)
            ar.submit()
            print(_(f"[DEBUG] Assessment Result created: {ar.name}"))
    except Exception as e:
        print(_(f"[DEBUG] Exception: {frappe.get_traceback()}"))
        frappe.log_error(frappe.get_traceback(), "LMSQuizSubmission on_submit error")
