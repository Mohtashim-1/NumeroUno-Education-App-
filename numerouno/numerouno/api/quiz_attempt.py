import frappe
from frappe import _
import json

@frappe.whitelist(allow_guest=True)
def get_student_groups():
    """Get all student groups for public quiz selection"""
    try:
        student_groups = frappe.get_all(
            "Student Group",
            fields=["name", "title", "course", "from_date", "to_date"],
            filters={"disabled": 0},
            order_by="title"
        )
        
        return {
            "status": "success",
            "student_groups": student_groups
        }
    except Exception as e:
        frappe.log_error(f"Error getting student groups: {str(e)}", "Quiz Attempt API")
        return {
            "status": "error",
            "message": "Failed to load student groups"
        }

@frappe.whitelist(allow_guest=True)
def get_students_by_group(student_group):
    """Get students from a specific student group"""
    try:
        if not student_group:
            return {
                "status": "error",
                "message": "Student group is required"
            }
        
        # Get students from Student Group Student table
        students = frappe.get_all(
            "Student Group Student",
            filters={"parent": student_group},
            fields=["student", "student_name"],
            order_by="student_name"
        )
        
        return {
            "status": "success",
            "students": students
        }
    except Exception as e:
        frappe.log_error(f"Error getting students by group: {str(e)}", "Quiz Attempt API")
        return {
            "status": "error",
            "message": "Failed to load students"
        }

@frappe.whitelist(allow_guest=True)
def get_available_quizzes(student_group, student):
    """Get available quizzes for a student in a specific group"""
    try:
        if not student_group or not student:
            return {
                "status": "error",
                "message": "Student group and student are required"
            }
        
        # Get the student group details
        student_group_doc = frappe.get_doc("Student Group", student_group)
        course_name = student_group_doc.course
        
        if not course_name:
            return {
                "status": "success",
                "quizzes": []
            }
        
        # Find LMS Course with matching title
        lms_courses = frappe.get_all(
            "LMS Course",
            filters={"title": course_name},
            fields=["name"]
        )
        
        if not lms_courses:
            return {
                "status": "success",
                "quizzes": []
            }
        
        lms_course = lms_courses[0].name
        
        # Get quizzes from the LMS course
        quizzes = frappe.get_all(
            "LMS Quiz",
            filters={"course": lms_course},
            fields=["name", "title", "total_marks", "passing_percentage", "max_attempts"],
            order_by="title"
        )
        
        # Filter out quizzes that student has already completed (if max attempts reached)
        available_quizzes = []
        for quiz in quizzes:
            # Check if student has reached max attempts
            if quiz.max_attempts and quiz.max_attempts > 0:
                # Get student's user email for checking submissions
                student_doc = frappe.get_doc("Student", student)
                user_email = student_doc.student_email_id
                
                # Check existing submissions
                existing_submissions = frappe.get_all(
                    "LMS Quiz Submission",
                    filters={
                        "quiz": quiz.name,
                        "member": user_email
                    },
                    fields=["name"]
                )
                
                if len(existing_submissions) >= quiz.max_attempts:
                    continue  # Skip this quiz as max attempts reached
            
            available_quizzes.append(quiz)
        
        return {
            "status": "success",
            "quizzes": available_quizzes
        }
    except Exception as e:
        frappe.log_error(f"Error getting available quizzes: {str(e)}", "Quiz Attempt API")
        return {
            "status": "error",
            "message": "Failed to load quizzes"
        }

@frappe.whitelist(allow_guest=True, methods=['GET', 'POST'])
def submit_quiz_attempt(quiz_name, student, student_group, answers):
    """Submit quiz attempt for a student"""
    try:
        print(f"=== QUIZ SUBMISSION DEBUG ===")
        print(f"Method: {frappe.request.method}")
        print(f"URL: {frappe.request.url}")
        print(f"Headers: {dict(frappe.request.headers)}")
        print(f"Quiz: {quiz_name}, Student: {student}, Group: {student_group}")
        print(f"Answers: {answers}")
        print(f"Form Dict: {frappe.form_dict}")
        
        if not quiz_name or not student or not student_group:
            return {
                "status": "error",
                "message": "Quiz name, student, and student group are required"
            }
        
        # Get student details
        student_doc = frappe.get_doc("Student", student)
        user_email = student_doc.student_email_id
        
        if not user_email:
            return {
                "status": "error",
                "message": "Student email not found"
            }
        
        # Get quiz details
        quiz_doc = frappe.get_doc("LMS Quiz", quiz_name)
        
        # Check if student has reached max attempts
        if quiz_doc.max_attempts and quiz_doc.max_attempts > 0:
            existing_submissions = frappe.get_all(
                "LMS Quiz Submission",
                filters={
                    "quiz": quiz_name,
                    "member": user_email
                },
                fields=["name"]
            )
            
            if len(existing_submissions) >= quiz_doc.max_attempts:
                return {
                    "status": "error",
                    "message": f"Maximum attempts ({quiz_doc.max_attempts}) reached for this quiz"
                }
        
        # Create quiz submission
        submission = frappe.new_doc("LMS Quiz Submission")
        submission.quiz = quiz_name
        submission.member = user_email
        submission.course = quiz_doc.course
        submission.passing_percentage = quiz_doc.passing_percentage or 80  # Add missing field
        submission.max_attempts = quiz_doc.max_attempts or 0  # Add max attempts
        submission.attempt = 1  # Set attempt number
        
        # Parse answers and calculate score
        if isinstance(answers, str):
            answers = json.loads(answers)
        
        total_score = 0
        total_marks = 0
        
        # Process each answer
        for answer_data in answers:
            question_name = answer_data.get("question")
            selected_answers = answer_data.get("answers", [])
            
            if not question_name:
                continue
            
            # Get question details
            question_doc = frappe.get_doc("LMS Question", question_name)
            marks = answer_data.get("marks", 1)
            total_marks += marks
            
            # Check if answer is correct
            is_correct = check_answer(question_doc, selected_answers)
            score = marks if is_correct else 0
            total_score += score
            
            # Add to submission result
            submission.append("result", {
                "question": question_name,
                "answer": json.dumps(selected_answers),
                "marks": score,
                "marks_out_of": marks
            })
        
        # Set submission details
        submission.score = total_score
        submission.score_out_of = total_marks
        submission.percentage = (total_score / total_marks * 100) if total_marks > 0 else 0
        
        # Save submission
        try:
            submission.insert(ignore_permissions=True)
            submission.submit()
        except Exception as e:
            frappe.log_error(f"Error saving quiz submission: {str(e)}", "Quiz Submission Error")
            return {
                "status": "error",
                "message": f"Failed to save quiz submission: {str(e)}"
            }
        
        # Return JSON response
        passed = submission.percentage >= (submission.passing_percentage or 80)
        
        return {
            "status": "success",
            "message": "Quiz submitted successfully",
            "submission_id": submission.name,
            "score": total_score,
            "total_marks": total_marks,
            "percentage": submission.percentage,
            "passed": passed
        }
    except Exception as e:
        frappe.log_error(f"Error submitting quiz attempt: {str(e)}", "Quiz Attempt API")
        return {
            "status": "error",
            "message": "Failed to submit quiz"
        }

def check_answer(question_doc, selected_answers):
    """Check if the selected answers are correct"""
    try:
        if question_doc.type == "Choices":
            # For multiple choice questions
            correct_answers = []
            for i in range(1, 5):
                if getattr(question_doc, f"is_correct_{i}", 0):
                    correct_answers.append(i)
            
            # Check if selected answers match correct answers
            if len(selected_answers) != len(correct_answers):
                return False
            
            return set(selected_answers) == set(correct_answers)
        
        elif question_doc.type == "True/False":
            # For True/False questions
            correct_answer = 1 if question_doc.is_correct_1 else 2
            return len(selected_answers) == 1 and selected_answers[0] == correct_answer
        
        elif question_doc.type == "Fill in the blanks":
            # For fill in the blanks - basic check
            # This is a simplified implementation
            return len(selected_answers) > 0
        
        else:
            # For other types, assume correct if answered
            return len(selected_answers) > 0
    
    except Exception as e:
        frappe.log_error(f"Error checking answer: {str(e)}", "Quiz Attempt API")
        return False

@frappe.whitelist(allow_guest=True)
def get_quiz_questions(quiz_name):
    """Get quiz questions for attempting"""
    try:
        if not quiz_name:
            return {
                "status": "error",
                "message": "Quiz name is required"
            }
        
        # Get quiz details
        quiz_doc = frappe.get_doc("LMS Quiz", quiz_name)
        
        # Get questions
        questions = frappe.get_all(
            "LMS Quiz Question",
            filters={"parent": quiz_name},
            fields=["question", "marks"],
            order_by="idx"
        )
        
        quiz_questions = []
        for q in questions:
            question_doc = frappe.get_doc("LMS Question", q.question)
            
            question_data = {
                "name": question_doc.name,
                "question": question_doc.question,
                "type": question_doc.type,
                "marks": q.marks,
                "options": []
            }
            
            # Add options for multiple choice questions
            if question_doc.type == "Choices":
                for i in range(1, 5):
                    option_text = getattr(question_doc, f"option_{i}", "")
                    if option_text:
                        question_data["options"].append({
                            "id": i,
                            "text": option_text,
                            "is_correct": getattr(question_doc, f"is_correct_{i}", 0)
                        })
            
            quiz_questions.append(question_data)
        
        return {
            "status": "success",
            "quiz": {
                "name": quiz_doc.name,
                "title": quiz_doc.title,
                "total_marks": quiz_doc.total_marks,
                "passing_percentage": quiz_doc.passing_percentage,
                "max_attempts": quiz_doc.max_attempts,
                "show_answers": quiz_doc.show_answers
            },
            "questions": quiz_questions
        }
    except Exception as e:
        frappe.log_error(f"Error getting quiz questions: {str(e)}", "Quiz Attempt API")
        return {
            "status": "error",
            "message": "Failed to load quiz questions"
        }
