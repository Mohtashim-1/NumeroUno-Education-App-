import frappe
from frappe import _
from frappe.utils import flt
import json

class UnifiedAssessmentSystem:
    """
    Unified system to handle both LMS Quiz and Practical Assessment results
    Creates one consolidated Assessment Result with proper score scaling
    """
    
    @staticmethod
    def find_or_create_assessment_result(student, assessment_plan, student_group=None):
        """
        Find existing Assessment Result or create a new one
        Returns the Assessment Result document
        """
        # First, try to find existing Assessment Result
        existing_result = frappe.db.get_value(
            "Assessment Result",
            {
                "student": student,
                "assessment_plan": assessment_plan,
                "docstatus": ["<", 2]  # Draft or Submitted, not Cancelled
            }
        )
        
        if existing_result:
            return frappe.get_doc("Assessment Result", existing_result)
        
        # Create new Assessment Result
        student_doc = frappe.get_doc("Student", student)
        assessment_plan_doc = frappe.get_doc("Assessment Plan", assessment_plan)
        
        ar = frappe.new_doc("Assessment Result")
        ar.update({
            "student": student,
            "student_name": student_doc.student_name,
            "assessment_plan": assessment_plan,
            "student_group": student_group or assessment_plan_doc.student_group,
            "academic_year": assessment_plan_doc.academic_year,
            "grading_scale": assessment_plan_doc.grading_scale
        })
        
        # Set company if field exists
        if hasattr(ar, "custom_company"):
            ar.custom_company = frappe.defaults.get_global_default("company")
        
        return ar
    
    @staticmethod
    def get_assessment_criteria_info(assessment_plan, criteria_name):
        """
        Get maximum score for a specific assessment criteria
        """
        assessment_plan_doc = frappe.get_doc("Assessment Plan", assessment_plan)
        
        for criteria in assessment_plan_doc.assessment_criteria:
            if criteria.assessment_criteria == criteria_name:
                return {
                    "maximum_score": criteria.maximum_score or 100,  # Default to 100 if None
                    "weightage": getattr(criteria, "weightage", 0)
                }
        
        return {"maximum_score": 100, "weightage": 0}
    
    @staticmethod
    def scale_score(raw_score, raw_max, target_max):
        """
        Scale score from one range to another
        Example: LMS Quiz 1/1 becomes 80/80 if target_max is 80
        """
        if raw_max == 0:
            return 0
        
        percentage = (raw_score / raw_max) * 100
        scaled_score = (percentage / 100) * target_max
        return round(scaled_score, 2)
    
    @staticmethod
    def update_assessment_result_details(assessment_result, criteria_name, raw_score, raw_max_score, source_type="LMS Quiz"):
        """
        Add or update assessment details in Assessment Result
        """
        # Get the target maximum score from assessment plan
        criteria_info = UnifiedAssessmentSystem.get_assessment_criteria_info(
            assessment_result.assessment_plan, 
            criteria_name
        )
        target_max_score = criteria_info["maximum_score"] or 100  # Ensure not None
        
        # Scale the score properly
        scaled_score = UnifiedAssessmentSystem.scale_score(raw_score, raw_max_score, target_max_score)
        
        # Check if this criteria already exists in details
        existing_detail = None
        for detail in assessment_result.details:
            if detail.assessment_criteria == criteria_name:
                existing_detail = detail
                break
        
        if existing_detail:
            # Update existing detail
            if source_type == "LMS Quiz":
                existing_detail.score = scaled_score
                existing_detail.comment = f"LMS Quiz: {raw_score}/{raw_max_score} (scaled to {scaled_score}/{target_max_score})"
            elif source_type == "Practical Assessment":
                # For practical assessment, we might want to add to existing score or replace
                # Let's replace for now, but you can modify this logic
                existing_detail.score = scaled_score
                existing_detail.comment = f"Practical Assessment: {raw_score}/{raw_max_score} (scaled to {scaled_score}/{target_max_score})"
            # Set maximum_score for existing detail
            if existing_detail.maximum_score in (None, 0):
                existing_detail.maximum_score = target_max_score
        else:
            # Add new detail
            comment = f"{source_type}: {raw_score}/{raw_max_score} (scaled to {scaled_score}/{target_max_score})"
            new_detail = assessment_result.append("details", {
                "assessment_criteria": criteria_name,
                "score": scaled_score,
                "comment": comment
            })
            # Set maximum_score directly on the detail row
            new_detail.maximum_score = target_max_score
        
        # Ensure all details have valid maximum_score (safety check)
        for detail in assessment_result.details:
            if detail.maximum_score in (None, 0):
                detail.maximum_score = target_max_score
        
        # Recalculate total score
        total_score = sum([flt(detail.score) for detail in assessment_result.details])
        assessment_result.total_score = total_score
        
        return scaled_score
    
    @staticmethod
    def ensure_student_in_group(student, student_group):
        """
        Ensure the given student is a member of the specified Student Group.
        Adds the student to the group if missing.
        """
        if not student_group or not student:
            return
        exists = frappe.db.exists(
            "Student Group Student",
            {"parent": student_group, "student": student}
        )
        if not exists:
            sg_doc = frappe.get_doc("Student Group", student_group)
            sg_doc.append("students", {"student": student})
            sg_doc.save(ignore_permissions=True)
    
    @staticmethod
    def ensure_assessment_plan_criteria(assessment_plan_doc, criteria_name, maximum_score):
        """
        Ensure the Assessment Plan has the specified criteria with the given maximum score
        """
        # Check if criteria already exists
        criteria_exists = False
        for criteria in assessment_plan_doc.assessment_criteria:
            if criteria.assessment_criteria == criteria_name:
                criteria_exists = True
                # Update maximum_score if different
                if criteria.maximum_score != maximum_score:
                    criteria.maximum_score = maximum_score
                break
        
        if not criteria_exists:
            # Add the criteria
            assessment_plan_doc.append("assessment_criteria", {
                "assessment_criteria": criteria_name,
                "maximum_score": maximum_score
            })
            print(f"[UNIFIED] Added criteria '{criteria_name}' to Assessment Plan")
        
        assessment_plan_doc.save(ignore_permissions=True)
        print(f"[UNIFIED] Updated Assessment Plan with criteria '{criteria_name}' (max_score: {maximum_score})")
    
    @staticmethod
    def handle_lms_quiz_submission(lms_quiz_doc):
        """
        Handle LMS Quiz submission and update unified Assessment Result
        """
        try:
            print(f"[UNIFIED] Processing LMS Quiz: {lms_quiz_doc.name}")
            
            # Get student from user
            user = lms_quiz_doc.member
            student = frappe.db.get_value("Student", {"user": user})
            if not student:
                student = frappe.db.get_value("Student", {"student_email_id": user})
            
            if not student:
                frappe.log_error(f"No Student found for user: {user}", "Unified Assessment System")
                return
            
            # Get course and assessment plan
            lms_course = lms_quiz_doc.course
            course_name = frappe.db.get_value("LMS Course", lms_course, "title")
            edu_course = frappe.db.get_value("Course", {"course_name": course_name})
            
            if not edu_course:
                frappe.log_error(f"No Education Course found for: {course_name}", "Unified Assessment System")
                return
            
            # Find assessment plan
            assessment_plan = frappe.db.get_value("Assessment Plan", {"course": edu_course})
            if not assessment_plan:
                frappe.log_error(f"No Assessment Plan found for course: {edu_course}", "Unified Assessment System")
                return
            
            # Ensure the student belongs to the assessment plan's student group
            assessment_plan_doc = frappe.get_doc("Assessment Plan", assessment_plan)
            UnifiedAssessmentSystem.ensure_student_in_group(student, assessment_plan_doc.student_group)
            
            # Get assessment criteria from Assessment Settings
            try:
                assessment_settings = frappe.get_single("Assesment Settings")
                criteria_name = assessment_settings.quiz_assesment
                
                if not criteria_name:
                    frappe.log_error("Quiz Assessment criteria not set in Assessment Settings", "Unified Assessment System")
                    return
                
                # Validate that the criteria exists
                if not frappe.db.exists("Assessment Criteria", criteria_name):
                    frappe.log_error(f"Assessment Criteria '{criteria_name}' from Assessment Settings does not exist", "Unified Assessment System")
                    return
                    
                print(f"[UNIFIED] Using quiz assessment criteria from settings: {criteria_name}")
                
                # Ensure the Assessment Plan has this criteria
                UnifiedAssessmentSystem.ensure_assessment_plan_criteria(assessment_plan_doc, criteria_name, 100)
                
            except Exception as e:
                frappe.log_error(f"Failed to get assessment criteria from Assessment Settings: {str(e)}", "Unified Assessment System")
                return
            
            # Get or create unified assessment result
            assessment_result = UnifiedAssessmentSystem.find_or_create_assessment_result(
                student, assessment_plan
            )
            
            # Update with LMS Quiz results
            scaled_score = UnifiedAssessmentSystem.update_assessment_result_details(
                assessment_result,
                criteria_name,
                lms_quiz_doc.score,
                lms_quiz_doc.score_out_of,
                "LMS Quiz"
            )
            
            # DEBUG: Check details before final guard
            print(f"[UNIFIED DEBUG] Details before final guard:")
            for i, d in enumerate(assessment_result.details):
                print(f"  Detail {i}: criteria={d.assessment_criteria}, score={d.score}, max_score={d.maximum_score} (type: {type(d.maximum_score)})")
            
            # Final guard: ensure all details have numeric maximum_score before save
            for d in assessment_result.details:
                if d.maximum_score in (None, 0):
                    d.maximum_score = 100
            
            # DEBUG: Check details after final guard
            print(f"[UNIFIED DEBUG] Details after final guard:")
            for i, d in enumerate(assessment_result.details):
                print(f"  Detail {i}: criteria={d.assessment_criteria}, score={d.score}, max_score={d.maximum_score} (type: {type(d.maximum_score)})")
            
            # DEBUG: Check Assessment Plan criteria
            print(f"[UNIFIED DEBUG] Assessment Plan criteria:")
            assessment_plan_doc = frappe.get_doc("Assessment Plan", assessment_result.assessment_plan)
            for criteria in assessment_plan_doc.assessment_criteria:
                print(f"  Plan criteria: {criteria.assessment_criteria}, max_score={criteria.maximum_score}")
            
            # Save the assessment result
            if assessment_result.docstatus == 0:  # Draft
                print(f"[UNIFIED DEBUG] About to save Assessment Result...")
                assessment_result.save(ignore_permissions=True)
                print(f"[UNIFIED] Updated Assessment Result: {assessment_result.name}")
            
            return assessment_result.name
            
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Unified Assessment System - LMS Quiz Error")
            raise
    
    @staticmethod
    def handle_practical_assessment_submission(practical_assessment_doc):
        """
        Handle Practical Assessment submission and update unified Assessment Result
        """
        try:
            print(f"[UNIFIED] Processing Practical Assessment: {practical_assessment_doc.name}")
            
            # Get or create unified assessment result
            assessment_result = UnifiedAssessmentSystem.find_or_create_assessment_result(
                practical_assessment_doc.student,
                practical_assessment_doc.assessment_plan,
                practical_assessment_doc.student_group
            )
            
            # Calculate practical assessment score
            checked_items = sum(1 for row in practical_assessment_doc.practical_assesment_table if row.mark)
            total_items = len(practical_assessment_doc.practical_assesment_table)
            
            # Get assessment criteria from Assessment Settings
            try:
                assessment_settings = frappe.get_single("Assesment Settings")
                criteria_name = assessment_settings.practical_assesment
                
                if not criteria_name:
                    frappe.log_error("Practical Assessment criteria not set in Assessment Settings", "Unified Assessment System")
                    return
                
                # Validate that the criteria exists
                if not frappe.db.exists("Assessment Criteria", criteria_name):
                    frappe.log_error(f"Assessment Criteria '{criteria_name}' from Assessment Settings does not exist", "Unified Assessment System")
                    return
                    
                print(f"[UNIFIED] Using practical assessment criteria from settings: {criteria_name}")
                
            except Exception as e:
                frappe.log_error(f"Failed to get practical assessment criteria from Assessment Settings: {str(e)}", "Unified Assessment System")
                return
            
            # Update with Practical Assessment results
            scaled_score = UnifiedAssessmentSystem.update_assessment_result_details(
                assessment_result,
                criteria_name,
                checked_items,
                total_items,
                "Practical Assessment"
            )
            
            # Save the assessment result
            if assessment_result.docstatus == 0:  # Draft
                assessment_result.save(ignore_permissions=True)
                print(f"[UNIFIED] Updated Assessment Result: {assessment_result.name}")
            
            return assessment_result.name
            
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Unified Assessment System - Practical Assessment Error")
            raise

# Hook functions to be called from doctypes
@frappe.whitelist()
def process_lms_quiz_submission(doc, method=None):
    """Hook function for LMS Quiz Submission"""
    return UnifiedAssessmentSystem.handle_lms_quiz_submission(doc)

@frappe.whitelist()  
def process_practical_assessment_submission(doc, method=None):
    """Hook function for Practical Assessment"""
    return UnifiedAssessmentSystem.handle_practical_assessment_submission(doc)

@frappe.whitelist()
def trigger_assessment_result_events(doc, method=None):
    """Hook function for Assessment Result submission to trigger other events"""
    if method == "on_submit":
        # Add any events you want to trigger when Assessment Result is submitted
        frappe.msgprint(f"Assessment Result {doc.name} has been submitted successfully!")
        
        # Example: Send notification email
        if doc.student:
            student_doc = frappe.get_doc("Student", doc.student)
            if student_doc.student_email_id:
                try:
                    frappe.sendmail(
                        recipients=[student_doc.student_email_id],
                        subject=f"Assessment Result Available - {doc.name}",
                        message=f"""
                        <h3>Assessment Result Notification</h3>
                        <p>Dear {student_doc.student_name},</p>
                        <p>Your assessment result for <strong>{doc.assessment_plan}</strong> has been published.</p>
                        <p>Total Score: <strong>{doc.total_score}</strong></p>
                        <p>Please check your student portal for detailed results.</p>
                        <br>
                        <p>Best regards,<br>Numerouno Team</p>
                        """
                    )
                except Exception as e:
                    frappe.log_error(f"Failed to send assessment notification: {str(e)}")

# Helper function to setup Assessment Settings
@frappe.whitelist()
def setup_assessment_settings(quiz_criteria=None, practical_criteria=None):
    """
    Helper function to setup Assessment Settings with proper criteria
    """
    try:
        # Get or create Assessment Settings
        try:
            settings = frappe.get_single("Assesment Settings")
        except frappe.DoesNotExistError:
            settings = frappe.new_doc("Assesment Settings")
        
        if quiz_criteria:
            if frappe.db.exists("Assessment Criteria", quiz_criteria):
                settings.quiz_assesment = quiz_criteria
            else:
                return f"Assessment Criteria '{quiz_criteria}' does not exist"
        
        if practical_criteria:
            if frappe.db.exists("Assessment Criteria", practical_criteria):
                settings.practical_assesment = practical_criteria
            else:
                return f"Assessment Criteria '{practical_criteria}' does not exist"
        
        settings.save(ignore_permissions=True)
        
        return f"Assessment Settings updated successfully. Quiz: {settings.quiz_assesment}, Practical: {settings.practical_assesment}"
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Setup Assessment Settings Error")
        return f"Error setting up Assessment Settings: {str(e)}"

@frappe.whitelist()
def get_assessment_settings_status():
    """
    Check the current status of Assessment Settings
    """
    try:
        settings = frappe.get_single("Assesment Settings")
        
        status = {
            "quiz_criteria": settings.quiz_assesment,
            "practical_criteria": settings.practical_assesment,
            "quiz_criteria_exists": frappe.db.exists("Assessment Criteria", settings.quiz_assesment) if settings.quiz_assesment else False,
            "practical_criteria_exists": frappe.db.exists("Assessment Criteria", settings.practical_assesment) if settings.practical_assesment else False
        }
        
        return status
        
    except Exception as e:
        return {"error": str(e)}

# Manual function to fix existing assessment results
@frappe.whitelist()
def consolidate_existing_assessment_results(assessment_plan=None):
    """
    Consolidate existing separate assessment results into unified ones
    """
    filters = {}
    if assessment_plan:
        filters["assessment_plan"] = assessment_plan
    
    # Get all assessment results
    assessment_results = frappe.get_all(
        "Assessment Result",
        filters=filters,
        fields=["name", "student", "assessment_plan", "student_group"]
    )
    
    consolidated = 0
    
    for result in assessment_results:
        # Group by student and assessment_plan
        similar_results = frappe.get_all(
            "Assessment Result",
            filters={
                "student": result["student"],
                "assessment_plan": result["assessment_plan"],
                "name": ["!=", result["name"]]
            },
            fields=["name"]
        )
        
        if similar_results:
            # Consolidate these results
            main_result = frappe.get_doc("Assessment Result", result["name"])
            
            for similar in similar_results:
                similar_doc = frappe.get_doc("Assessment Result", similar["name"])
                
                # Move details from similar to main
                for detail in similar_doc.details:
                    main_result.append("details", {
                        "assessment_criteria": detail.assessment_criteria,
                        "score": detail.score,
                        "maximum_score": detail.maximum_score,
                        "comment": detail.comment
                    })
                
                # Cancel the similar result
                if similar_doc.docstatus == 1:
                    similar_doc.cancel()
                elif similar_doc.docstatus == 0:
                    similar_doc.delete()
            
            # Recalculate total score
            main_result.total_score = sum([flt(detail.score) for detail in main_result.details])
            main_result.save(ignore_permissions=True)
            consolidated += 1
    
    return f"Consolidated {consolidated} assessment results" 