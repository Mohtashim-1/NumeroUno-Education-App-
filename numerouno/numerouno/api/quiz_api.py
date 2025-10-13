import frappe
from frappe import _

@frappe.whitelist(allow_guest=True, methods=['GET', 'POST'])
def get_student_groups(academic_year=None, course=None, from_date=None, to_date=None):
    """Get student groups with optional filters"""
    try:
        filters = {"disabled": 0}
        
        # Add filters based on parameters
        if academic_year:
            filters["academic_year"] = academic_year
        if course:
            filters["course"] = course
        if from_date:
            filters["from_date"] = [">=", from_date]
        if to_date:
            filters["to_date"] = ["<=", to_date]
        
        student_groups = frappe.get_all(
            "Student Group",
            fields=["name", "student_group_name", "course", "from_date", "to_date", "academic_year"],
            filters=filters,
            order_by="student_group_name"
        )
        
        # Convert datetime objects to strings for JSON serialization
        for group in student_groups:
            if group.get('from_date'):
                group['from_date'] = str(group['from_date'])
            if group.get('to_date'):
                group['to_date'] = str(group['to_date'])
        
        return {
            "status": "success",
            "student_groups": student_groups
        }
    except Exception as e:
        frappe.log_error(f"Error getting student groups: {str(e)}", "Quiz API")
        return {
            "status": "error",
            "message": "Failed to load student groups"
        }

@frappe.whitelist(allow_guest=True, methods=['GET', 'POST'])
def get_academic_years():
    """Get all academic years from student groups"""
    try:
        academic_years = frappe.get_all(
            "Student Group",
            fields=["academic_year"],
            filters={"disabled": 0, "academic_year": ["!=", ""]},
            group_by="academic_year",
            order_by="academic_year"
        )
        
        # Format the data
        formatted_years = []
        for year in academic_years:
            if year.get('academic_year'):
                formatted_years.append({
                    "name": year['academic_year'],
                    "academic_year": year['academic_year']
                })
        
        return {
            "status": "success",
            "academic_years": formatted_years
        }
    except Exception as e:
        frappe.log_error(f"Error getting academic years: {str(e)}", "Quiz API")
        return {
            "status": "error",
            "message": "Failed to load academic years"
        }

@frappe.whitelist(allow_guest=True, methods=['GET', 'POST'])
def get_courses():
    """Get all courses from student groups"""
    try:
        courses = frappe.get_all(
            "Student Group",
            fields=["course"],
            filters={"disabled": 0, "course": ["!=", ""]},
            group_by="course",
            order_by="course"
        )
        
        # Format the data
        formatted_courses = []
        for course in courses:
            if course.get('course'):
                formatted_courses.append({
                    "name": course['course'],
                    "course_name": course['course']
                })
        
        return {
            "status": "success",
            "courses": formatted_courses
        }
    except Exception as e:
        frappe.log_error(f"Error getting courses: {str(e)}", "Quiz API")
        return {
            "status": "error",
            "message": "Failed to load courses"
        }

@frappe.whitelist(allow_guest=True, methods=['GET', 'POST'])
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
        frappe.log_error(f"Error getting students by group: {str(e)}", "Quiz API")
        return {
            "status": "error",
            "message": "Failed to load students"
        }

@frappe.whitelist(allow_guest=True, methods=['GET', 'POST'])
def get_available_quizzes(student_group, student):
    """Get available quizzes for a student in a specific group"""
    try:
        print(f"=== QUIZ API DEBUG START ===")
        print(f"Input - Student Group: {student_group}, Student: {student}")
        frappe.log_error(f"=== QUIZ API DEBUG START ===", "Quiz API Debug")
        frappe.log_error(f"Input - Student Group: {student_group}, Student: {student}", "Quiz API Debug")
        
        if not student_group or not student:
            print("ERROR: Missing student_group or student")
            return {
                "status": "error",
                "message": "Student group and student are required"
            }
        
        # Get the student group details
        student_group_doc = frappe.get_doc("Student Group", student_group)
        course_name = student_group_doc.course
        print(f"Student Group Course: {course_name}")
        frappe.log_error(f"Student Group Course: {course_name}", "Quiz API Debug")
        
        if not course_name:
            print("ERROR: No course found for student group")
            frappe.log_error(f"No course found for student group {student_group}", "Quiz API Debug")
            return {
                "status": "success",
                "quizzes": []
            }
        
        # Find LMS Course with matching title
        lms_courses = frappe.get_all(
            "LMS Course",
            filters={"title": course_name},
            fields=["name", "title"]
        )
        print(f"Found LMS Courses: {lms_courses}")
        frappe.log_error(f"Found LMS Courses: {lms_courses}", "Quiz API Debug")
        
        if not lms_courses:
            print(f"ERROR: No LMS Course found with title: {course_name}")
            frappe.log_error(f"No LMS Course found with title: {course_name}", "Quiz API Debug")
            return {
                "status": "success",
                "quizzes": []
            }
        
        lms_course = lms_courses[0].name
        print(f"Using LMS Course: {lms_course}")
        frappe.log_error(f"Using LMS Course: {lms_course}", "Quiz API Debug")
        
        # Get the User ID from the Student record
        student_doc = frappe.get_doc("Student", student)
        user_id = student_doc.student_email_id
        print(f"Student {student} maps to User: {user_id}")
        frappe.log_error(f"Student {student} maps to User: {user_id}", "Quiz API Debug")
        
        if not user_id:
            print(f"ERROR: No User ID found for Student {student}")
            frappe.log_error(f"No User ID found for Student {student}", "Quiz API Debug")
            return {
                "status": "success",
                "quizzes": []
            }
        
        # Check if student is enrolled in the LMS course using User ID
        enrollment = frappe.get_all(
            "LMS Enrollment",
            filters={
                "member": user_id,
                "course": lms_course,
                "member_type": "Student"
            },
            fields=["name", "member", "course", "member_type"]
        )
        print(f"LMS Enrollment check for user {user_id} in course {lms_course}: {enrollment}")
        frappe.log_error(f"Enrollment found: {len(enrollment)} records", "Quiz API Debug")
        
        if not enrollment:
            print(f"ERROR: User {user_id} not enrolled in LMS course {lms_course}")
            frappe.log_error(f"User {user_id} not enrolled in LMS course {lms_course} (Course: {course_name})", "Quiz API Debug")
            # Let's also check all enrollments for this user
            all_enrollments = frappe.get_all(
                "LMS Enrollment",
                filters={"member": user_id},
                fields=["name", "member", "course", "member_type"]
            )
            print(f"All enrollments for user {user_id}: {all_enrollments}")
            frappe.log_error(f"All enrollments: {len(all_enrollments)} records", "Quiz API Debug")
            return {
                "status": "success",
                "quizzes": []
            }
        
        # Get all course lessons for this course
        course_lessons = frappe.get_all(
            "Course Lesson",
            filters={"course": lms_course},
            fields=["name", "title", "content"]
        )
        print(f"Found {len(course_lessons)} course lessons for course {lms_course}")
        frappe.log_error(f"Found {len(course_lessons)} course lessons for course {lms_course}", "Quiz API Debug")
        
        quiz_ids = []
        
        # Extract quiz IDs from course lesson content
        for lesson in course_lessons:
            print(f"Processing lesson: {lesson['name']} - {lesson['title']}")
            frappe.log_error(f"Processing lesson: {lesson['name']} - {lesson['title']}", "Quiz API Debug")
            
            if lesson.get('content'):
                print(f"Lesson has content, length: {len(lesson['content'])}")
                frappe.log_error(f"Lesson has content, length: {len(lesson['content'])}", "Quiz API Debug")
                try:
                    import json
                    content = json.loads(lesson['content'])
                    print(f"Parsed content: {content}")
                    frappe.log_error(f"Content parsed successfully", "Quiz API Debug")
                    
                    # Look for quiz blocks in the content
                    for block in content.get("blocks", []):
                        print(f"Processing block: {block}")
                        frappe.log_error(f"Processing block type: {block.get('type', 'unknown')}", "Quiz API Debug")
                        
                        if block.get("type") == "quiz":
                            quiz_id = block.get("data", {}).get("quiz")
                            print(f"Found quiz block with ID: {quiz_id}")
                            frappe.log_error(f"Found quiz block with ID: {quiz_id}", "Quiz API Debug")
                            if quiz_id:
                                quiz_ids.append(quiz_id)
                        
                        # Also check for quizzes in video uploads
                        if block.get("type") == "upload":
                            quizzes_in_video = block.get("data", {}).get("quizzes", [])
                            print(f"Found upload block with quizzes: {quizzes_in_video}")
                            frappe.log_error(f"Found upload block with {len(quizzes_in_video)} quizzes", "Quiz API Debug")
                            for quiz_row in quizzes_in_video:
                                if quiz_row.get("quiz"):
                                    quiz_ids.append(quiz_row.get("quiz"))
                
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"ERROR parsing lesson content for {lesson['name']}: {str(e)}")
                    frappe.log_error(f"Error parsing lesson content for {lesson['name']}: {str(e)}", "Quiz API Debug")
                    continue
            else:
                print(f"Lesson {lesson['name']} has no content")
                frappe.log_error(f"Lesson {lesson['name']} has no content", "Quiz API Debug")
        
        # Remove duplicates
        quiz_ids = list(set(quiz_ids))
        print(f"Found {len(quiz_ids)} unique quiz IDs: {quiz_ids}")
        frappe.log_error(f"Found {len(quiz_ids)} unique quiz IDs: {quiz_ids}", "Quiz API Debug")
        
        if not quiz_ids:
            print("ERROR: No quiz IDs found in any course lessons")
            frappe.log_error("ERROR: No quiz IDs found in any course lessons", "Quiz API Debug")
            return {
                "status": "success",
                "quizzes": []
            }
        
        # Get quiz details
        print(f"Fetching quiz details for IDs: {quiz_ids}")
        frappe.log_error(f"Fetching quiz details for IDs: {quiz_ids}", "Quiz API Debug")
        
        quizzes = frappe.get_all(
            "LMS Quiz",
            filters={"name": ["in", quiz_ids]},
            fields=["name", "title", "total_marks", "passing_percentage", "max_attempts"],
            order_by="title"
        )
        
        print(f"Found {len(quizzes)} quizzes: {quizzes}")
        frappe.log_error(f"Found {len(quizzes)} quizzes: {quizzes}", "Quiz API Debug")
        
        print(f"=== QUIZ API DEBUG END ===")
        frappe.log_error(f"=== QUIZ API DEBUG END ===", "Quiz API Debug")
        
        return {
            "status": "success",
            "quizzes": quizzes
        }
    except Exception as e:
        print(f"EXCEPTION in quiz API: {str(e)}")
        frappe.log_error(f"Error getting available quizzes: {str(e)}", "Quiz API Debug")
        return {
            "status": "error",
            "message": "Failed to load quizzes"
        }
