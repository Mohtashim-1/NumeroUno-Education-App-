import frappe
from frappe import _
from frappe.utils import today

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

@frappe.whitelist(allow_guest=True, methods=['GET', 'POST'])
def get_available_quizzes_from_mcqs(student_group, student):
    """Get available quizzes from MCQS Assignment for a student in a specific group"""
    try:
        print("=" * 80)
        print("MCQS QUIZ API DEBUG START")
        print(f"Input - Student Group: {student_group}, Student: {student}")
        print("=" * 80)
        
        frappe.log_error(f"=== MCQS QUIZ API DEBUG START ===", "MCQS Quiz API")
        frappe.log_error(f"Input - Student Group: {student_group}, Student: {student}", "MCQS Quiz API")
        
        if not student_group or not student:
            print("ERROR: Missing student_group or student")
            return {
                "status": "error",
                "message": "Student group and student are required"
            }
        
        # Get MCQS Assignment records for this student group
        # Try both by name (since autoname is format:{student_group}) and by student_group field
        print(f"\n[STEP 1] Searching for MCQS Assignment by name: {student_group}")
        mcqs_assignments_by_name = frappe.get_all(
            "MCQS Assignment",
            filters={"name": student_group},
            fields=["name", "student_group", "mcqs"]
        )
        print(f"[STEP 1] Found {len(mcqs_assignments_by_name)} assignments by name: {mcqs_assignments_by_name}")
        
        print(f"\n[STEP 2] Searching for MCQS Assignment by student_group field: {student_group}")
        mcqs_assignments_by_field = frappe.get_all(
            "MCQS Assignment",
            filters={"student_group": student_group},
            fields=["name", "student_group", "mcqs"]
        )
        print(f"[STEP 2] Found {len(mcqs_assignments_by_field)} assignments by field: {mcqs_assignments_by_field}")
        
        # Also try to get by partial match in case of naming issues
        all_mcqs_assignments = frappe.get_all(
            "MCQS Assignment",
            fields=["name", "student_group", "mcqs"],
            limit=100
        )
        # Log without truncation by using shorter message
        frappe.log_error(f"Found {len(all_mcqs_assignments)} total MCQS Assignments", "MCQS Quiz API")
        
        # Combine both results and remove duplicates
        print(f"\n[STEP 3] Combining results...")
        all_assignments = {}
        for assignment in mcqs_assignments_by_name + mcqs_assignments_by_field:
            # Handle both dict and object access
            assgn_name = assignment.get('name') if isinstance(assignment, dict) else getattr(assignment, 'name', None)
            if assgn_name:
                all_assignments[assgn_name] = assignment
        
        mcqs_assignments = list(all_assignments.values())
        print(f"[STEP 3] Total unique assignments: {len(mcqs_assignments)}")
        for i, assgn in enumerate(mcqs_assignments):
            assgn_name = assgn.get('name') if isinstance(assgn, dict) else getattr(assgn, 'name', 'N/A')
            assgn_mcqs = assgn.get('mcqs') if isinstance(assgn, dict) else getattr(assgn, 'mcqs', 'N/A')
            print(f"  Assignment {i+1}: name={assgn_name}, mcqs={assgn_mcqs}")
        
        # If still not found, try to get document directly by name
        if not mcqs_assignments:
            try:
                mcqs_doc = frappe.get_doc("MCQS Assignment", student_group)
                mcqs_assignments = [{
                    "name": mcqs_doc.name,
                    "student_group": mcqs_doc.student_group,
                    "mcqs": mcqs_doc.mcqs
                }]
                frappe.log_error(f"Found MCQS Assignment by direct doc access: {mcqs_assignments}", "MCQS Quiz API")
            except frappe.DoesNotExistError:
                frappe.log_error(f"MCQS Assignment document '{student_group}' does not exist", "MCQS Quiz API")
            except Exception as e:
                frappe.log_error(f"Error accessing MCQS Assignment document: {str(e)}", "MCQS Quiz API")
        
        frappe.log_error(f"Found {len(mcqs_assignments)} MCQS Assignment records", "MCQS Quiz API")
        for i, assgn in enumerate(mcqs_assignments[:3]):  # Log first 3 only
            # Handle both dict and object access
            assgn_name = assgn.get('name') if isinstance(assgn, dict) else getattr(assgn, 'name', 'N/A')
            assgn_student_group = assgn.get('student_group') if isinstance(assgn, dict) else getattr(assgn, 'student_group', 'N/A')
            assgn_mcqs = assgn.get('mcqs') if isinstance(assgn, dict) else getattr(assgn, 'mcqs', 'N/A')
            frappe.log_error(f"Assignment {i+1}: name={assgn_name}, student_group={assgn_student_group}, mcqs={assgn_mcqs}", "MCQS Quiz API")
        
        if not mcqs_assignments:
            frappe.log_error(f"No MCQS Assignment found for student group: {student_group}", "MCQS Quiz API")
            return {
                "status": "success",
                "quizzes": [],
                "debug": f"No MCQS Assignment found for student group: {student_group}"
            }
        
        # Get unique quiz names from MCQS Assignment
        print(f"\n[STEP 4] Extracting quiz names from assignments...")
        quiz_names = []
        for assignment in mcqs_assignments:
            # Handle both dict and object access
            mcqs_value = assignment.get('mcqs') if isinstance(assignment, dict) else getattr(assignment, 'mcqs', None)
            print(f"  Assignment mcqs value: {mcqs_value} (type: {type(mcqs_value)})")
            if mcqs_value:
                quiz_names.append(mcqs_value)
        quiz_names = list(set(quiz_names))  # Remove duplicates
        
        print(f"[STEP 4] Found {len(quiz_names)} unique quiz names: {quiz_names}")
        frappe.log_error(f"Found {len(quiz_names)} unique quiz names", "MCQS Quiz API")
        for i, qn in enumerate(quiz_names[:5]):  # Log first 5 only
            frappe.log_error(f"Quiz {i+1}: {qn}", "MCQS Quiz API")
        
        if not quiz_names:
            print("[ERROR] MCQS Assignment found but no quizzes linked!")
            frappe.log_error(f"MCQS Assignment found but no quizzes linked", "MCQS Quiz API")
            return {
                "status": "success",
                "quizzes": [],
                "debug": "MCQS Assignment found but no quizzes are linked. Please check that the 'MCQS' field in MCQS Assignment has a Quiz selected.",
                "debug_details": {
                    "student_group": student_group,
                    "assignments_found": len(mcqs_assignments),
                    "quiz_names": []
                }
            }
        
        # Get quiz details from Quiz doctype (Education module)
        # Try by name first (since Quiz autoname is field:title, name = title)
        print(f"\n[STEP 5] Looking up Quiz records for: {quiz_names}")
        quizzes = []
        for quiz_name in quiz_names:
            quiz_found = False
            print(f"\n  [STEP 5.{len(quizzes)+1}] Looking for Quiz: '{quiz_name}'")
            try:
                # First, try direct document access to see if it exists
                try:
                    print(f"    Trying direct access: frappe.get_doc('Quiz', '{quiz_name}')")
                    quiz_doc = frappe.get_doc("Quiz", quiz_name)
                    print(f"    ✓ Found Quiz by direct access! name={quiz_doc.name}, title={quiz_doc.title}")
                    # If we get here, the quiz exists
                    quizzes.append({
                        "name": quiz_doc.name,
                        "title": quiz_doc.title or quiz_doc.name,
                        "passing_score": getattr(quiz_doc, 'passing_score', 75),
                        "max_attempts": getattr(quiz_doc, 'max_attempts', 0)
                    })
                    frappe.log_error(f"Found Quiz '{quiz_name}' by direct access", "MCQS Quiz API")
                    quiz_found = True
                    continue
                except frappe.DoesNotExistError:
                    print(f"    ✗ Quiz '{quiz_name}' does not exist (DoesNotExistError)")
                    # Quiz doesn't exist with this exact name, try get_all
                    pass
                except Exception as e:
                    print(f"    ✗ Error accessing Quiz directly: {str(e)[:150]}")
                    frappe.log_error(f"Error accessing Quiz '{quiz_name}' directly: {str(e)[:150]}", "MCQS Quiz API")
                
                # Try to get quiz by name using get_all
                if not quiz_found:
                    print(f"    Trying get_all with name filter: name='{quiz_name}'")
                    quiz_list = frappe.get_all(
                        "Quiz",
                        filters={"name": quiz_name},
                        fields=["name", "title", "passing_score", "max_attempts"],
                        limit=1
                    )
                    print(f"    get_all result: {quiz_list}")
                    if quiz_list:
                        quizzes.extend(quiz_list)
                        print(f"    ✓ Found Quiz by get_all with name filter!")
                        frappe.log_error(f"Found Quiz '{quiz_name}' by get_all with name filter", "MCQS Quiz API")
                        quiz_found = True
                        continue
                
                # Try by title as fallback
                if not quiz_found:
                    print(f"    Trying get_all with title filter: title='{quiz_name}'")
                    quiz_list = frappe.get_all(
                        "Quiz",
                        filters={"title": quiz_name},
                        fields=["name", "title", "passing_score", "max_attempts"],
                        limit=1
                    )
                    print(f"    get_all result: {quiz_list}")
                    if quiz_list:
                        quizzes.extend(quiz_list)
                        print(f"    ✓ Found Quiz by get_all with title filter!")
                        frappe.log_error(f"Found Quiz '{quiz_name}' by get_all with title filter", "MCQS Quiz API")
                        quiz_found = True
                        continue
                
                # If still not found, list all quizzes to help debug
                if not quiz_found:
                    all_quizzes = frappe.get_all("Quiz", fields=["name", "title"], limit=20)
                    quiz_info = []
                    for q in all_quizzes[:10]:  # Show first 10
                        quiz_info.append(f"name='{q.get('name', 'N/A')}' title='{q.get('title', 'N/A')}'")
                    frappe.log_error(f"Quiz '{quiz_name}' not found. Available quizzes: {'; '.join(quiz_info)}", "MCQS Quiz API")
                    
                    # Also check if there's a similar quiz name (case-insensitive)
                    similar_quizzes = frappe.get_all(
                        "Quiz",
                        filters={"title": ["like", f"%{quiz_name}%"]},
                        fields=["name", "title"],
                        limit=5
                    )
                    if similar_quizzes:
                        similar_info = [f"'{q.get('name', 'N/A')}' ({q.get('title', 'N/A')})" for q in similar_quizzes]
                        frappe.log_error(f"Similar quiz names found: {', '.join(similar_info)}", "MCQS Quiz API")
                
            except Exception as e:
                frappe.log_error(f"Error looking up quiz '{quiz_name}': {str(e)[:150]}", "MCQS Quiz API")
                continue
        
        # Remove duplicates
        seen = set()
        unique_quizzes = []
        for q in quizzes:
            # Handle both dict and object access
            quiz_name = q.get('name') if isinstance(q, dict) else getattr(q, 'name', None)
            if quiz_name and quiz_name not in seen:
                seen.add(quiz_name)
                unique_quizzes.append(q)
        quizzes = unique_quizzes
        
        frappe.log_error(f"Found {len(quizzes)} Quiz records", "MCQS Quiz API")
        
        print(f"\n[STEP 6] Final quiz count: {len(quizzes)}")
        if not quizzes:
            quiz_names_str = ", ".join(quiz_names[:3])  # Show first 3 only
            print(f"[ERROR] No Quiz records found for: {quiz_names_str}")
            
            # List all available quizzes for debugging
            all_quizzes = frappe.get_all("Quiz", fields=["name", "title"], limit=50)
            print(f"[DEBUG] Available Quizzes in system ({len(all_quizzes)}):")
            for q in all_quizzes[:20]:
                q_name = q.get('name') if isinstance(q, dict) else getattr(q, 'name', 'N/A')
                q_title = q.get('title') if isinstance(q, dict) else getattr(q, 'title', 'N/A')
                print(f"  - name='{q_name}', title='{q_title}'")
            
            frappe.log_error(f"No Quiz records found for: {quiz_names_str}", "MCQS Quiz API")
            return {
                "status": "success",
                "quizzes": [],
                "debug": f"Quiz names found in MCQS Assignment ({quiz_names_str}) but no Quiz records exist. Check if Quiz '{quiz_names[0] if quiz_names else 'N/A'}' exists in Quiz doctype.",
                "debug_details": {
                    "student_group": student_group,
                    "quiz_names_from_mcqs": quiz_names,
                    "quizzes_found": 0
                }
            }
        
        # Calculate total marks for each quiz
        print(f"\n[STEP 7] Processing {len(quizzes)} quizzes to calculate total marks...")
        print(f"[STEP 7] Quizzes list: {quizzes}")
        quiz_list = []
        for idx, quiz in enumerate(quizzes):
            print(f"\n  [STEP 7.{idx+1}] Processing quiz (type: {type(quiz)}): {quiz}")
            try:
                # Handle both dict and object access
                quiz_name = quiz.get('name') if isinstance(quiz, dict) else getattr(quiz, 'name', None)
                quiz_title = quiz.get('title') if isinstance(quiz, dict) else getattr(quiz, 'title', None)
                quiz_passing_score = quiz.get('passing_score') if isinstance(quiz, dict) else getattr(quiz, 'passing_score', 75)
                quiz_max_attempts = quiz.get('max_attempts') if isinstance(quiz, dict) else getattr(quiz, 'max_attempts', 0)
                
                print(f"    Quiz name: {quiz_name}, title: {quiz_title}")
                
                if not quiz_name:
                    print(f"    ✗ ERROR: Quiz record has no name!")
                    frappe.log_error(f"Quiz record has no name: {quiz}", "MCQS Quiz API")
                    continue
                
                # Get total marks from quiz questions
                print(f"    Getting quiz document: frappe.get_doc('Quiz', '{quiz_name}')")
                quiz_doc = frappe.get_doc("Quiz", quiz_name)
                print(f"    Quiz document retrieved: name={quiz_doc.name}, title={quiz_doc.title}")
                
                total_marks = 0
                if hasattr(quiz_doc, 'question') and quiz_doc.question:
                    print(f"    Quiz has {len(quiz_doc.question)} questions")
                    # QuizQuestion table doesn't have marks field
                    # Use default of 1 mark per question, or count questions
                    # Since QuizQuestion doesn't store marks, we'll use 1 mark per question as default
                    total_marks = len(quiz_doc.question)
                    print(f"    Total marks (1 per question): {total_marks}")
                else:
                    print(f"    Quiz has no questions or question attribute doesn't exist")
                    total_marks = 0
                
                print(f"    Total marks calculated: {total_marks}")
                
                quiz_item = {
                    "name": quiz_name,
                    "title": quiz_title or quiz_name,  # Fallback to name if title is None
                    "total_marks": total_marks,
                    "passing_percentage": quiz_passing_score or 75,
                    "max_attempts": quiz_max_attempts or 0
                }
                print(f"    ✓ Adding quiz to list: {quiz_item}")
                quiz_list.append(quiz_item)
            except frappe.DoesNotExistError as e:
                quiz_name = quiz.get('name') if isinstance(quiz, dict) else getattr(quiz, 'name', 'Unknown')
                print(f"    ✗ ERROR: Quiz '{quiz_name}' does not exist: {str(e)}")
                frappe.log_error(f"Quiz '{quiz_name}' does not exist", "MCQS Quiz API")
                continue
            except Exception as e:
                error_msg = str(e)[:200]  # Truncate error message to avoid issues
                quiz_name = quiz.get('name') if isinstance(quiz, dict) else getattr(quiz, 'name', 'Unknown')
                print(f"    ✗ ERROR processing quiz {quiz_name}: {error_msg}")
                print(f"    Full error: {frappe.get_traceback()}")
                frappe.log_error(f"Error processing quiz {quiz_name}: {error_msg}\nTraceback: {frappe.get_traceback()}", "MCQS Quiz API")
                continue
        
        print(f"\n[STEP 7] Returning {len(quiz_list)} quizzes")
        print("=" * 80)
        print("MCQS QUIZ API DEBUG END")
        print("=" * 80)
        
        frappe.log_error(f"=== MCQS QUIZ API DEBUG END - Returning {len(quiz_list)} quizzes ===", "MCQS Quiz API")
        
        return {
            "status": "success",
            "quizzes": quiz_list,
            "debug_info": {
                "student_group": student_group,
                "assignments_found": len(mcqs_assignments),
                "quiz_names_from_mcqs": quiz_names,
                "quizzes_found": len(quiz_list)
            }
        }
    except Exception as e:
        error_msg = f"Error getting quizzes from MCQS Assignment: {str(e)}"
        frappe.log_error(error_msg + f"\nTraceback: {frappe.get_traceback()}", "MCQS Quiz API")
        return {
            "status": "error",
            "message": error_msg
        }

@frappe.whitelist(allow_guest=True, methods=['GET', 'POST'])
def get_quiz_questions_from_quiz(quiz_name):
    """Get quiz questions from Quiz doctype (Education module)"""
    try:
        print(f"\n{'='*80}")
        print(f"GET QUIZ QUESTIONS - Quiz: {quiz_name}")
        print(f"{'='*80}")
        
        if not quiz_name:
            return {
                "status": "error",
                "message": "Quiz name is required"
            }
        
        # Get quiz details
        print(f"Getting Quiz document: {quiz_name}")
        quiz_doc = frappe.get_doc("Quiz", quiz_name)
        print(f"Quiz found: {quiz_doc.name} - {quiz_doc.title}")
        
        # Reload to ensure we have all child table entries
        quiz_doc.reload()
        print(f"Quiz reloaded. Checking question table...")
        
        # Get questions - use direct database query to ensure we get all questions
        questions_in_db = frappe.get_all(
            "Quiz Question",
            filters={"parent": quiz_name},
            fields=["name", "question_link", "idx"],
            order_by="idx"
        )
        print(f"Direct DB query found {len(questions_in_db)} Quiz Question records")
        for qq in questions_in_db:
            print(f"  DB Record: name={qq.get('name')}, question_link={qq.get('question_link')}, idx={qq.get('idx')}")
        
        # Also check document's child table for comparison
        doc_question_count = len(quiz_doc.question) if quiz_doc.question else 0
        print(f"Quiz document has {doc_question_count} questions in question table")
        
        # Use database query results instead of document child table to ensure we get all questions
        questions = []
        question_links_to_process = [qq.get('question_link') for qq in questions_in_db if qq.get('question_link')]
        
        print(f"Processing {len(question_links_to_process)} questions from database query...")
        for idx, question_link in enumerate(question_links_to_process):
            print(f"\n  Processing question {idx+1} of {len(question_links_to_process)}:")
            print(f"    Question Link: {question_link}")
            
            if not question_link:
                print(f"    ✗ ERROR: QuizQuestion has no question_link")
                continue
                
            try:
                question_doc = frappe.get_doc("Question", question_link)
                print(f"    Question document: {question_doc.name}")
                print(f"    Question type: {getattr(question_doc, 'question_type', 'N/A')}")
                
                question_data = {
                    "name": question_doc.name,
                    "question": question_doc.question or "",
                    "type": getattr(question_doc, 'question_type', 'Single Correct Answer'),
                    "marks": 1,  # Default to 1 mark since QuizQuestion doesn't have marks
                    "options": []
                }
                
                # Question doctype uses 'options' table (child table)
                # Options table has: 'option' (text) and 'is_correct' (checkbox)
                if hasattr(question_doc, 'options') and question_doc.options:
                    print(f"    Question has {len(question_doc.options)} options")
                    for opt_idx, opt in enumerate(question_doc.options):
                        option_text = getattr(opt, 'option', '')
                        is_correct = getattr(opt, 'is_correct', 0)
                        if option_text:
                            question_data["options"].append({
                                "id": opt_idx + 1,
                                "text": option_text,
                                "is_correct": is_correct
                            })
                            print(f"      Option {opt_idx+1}: {option_text} (correct: {is_correct})")
                else:
                    print(f"    ✗ WARNING: Question has no options table")
                
                questions.append(question_data)
                print(f"    ✓ Question {idx+1} added successfully (Total: {len(questions)})")
            except Exception as e:
                print(f"    ✗ ERROR loading question {question_link}: {str(e)}")
                frappe.log_error(f"Error loading question {question_link}: {str(e)}\nTraceback: {frappe.get_traceback()}", "Quiz API")
                continue
        
        if not questions:
            print(f"✗ WARNING: No questions were successfully loaded!")
        
        # Calculate total marks (1 per question since QuizQuestion doesn't store marks)
        total_marks = len(questions)
        print(f"\nTotal questions: {len(questions)}, Total marks: {total_marks}")
        print(f"{'='*80}\n")
        
        return {
            "status": "success",
            "quiz": {
                "name": quiz_doc.name,
                "title": quiz_doc.title,
                "total_marks": total_marks,
                "passing_percentage": quiz_doc.passing_score or 75,
                "max_attempts": quiz_doc.max_attempts or 0
            },
            "questions": questions
        }
    except Exception as e:
        error_msg = f"Error getting quiz questions: {str(e)}"
        print(f"\n✗ ERROR: {error_msg}")
        print(f"Traceback: {frappe.get_traceback()}")
        frappe.log_error(f"{error_msg}\nTraceback: {frappe.get_traceback()}", "Quiz API")
        return {
            "status": "error",
            "message": f"Failed to load quiz questions: {str(e)}"
        }

@frappe.whitelist(allow_guest=True, methods=['GET', 'POST'])
def submit_quiz_from_mcqs(quiz_name, student, student_group, answers):
    """Submit quiz attempt and create Assessment Result"""
    import json
    
    try:
        if not quiz_name or not student or not student_group:
            return {
                "status": "error",
                "message": "Quiz name, student, and student group are required"
            }
        
        # Get quiz details
        quiz_doc = frappe.get_doc("Quiz", quiz_name)
        
        # Get student details
        student_doc = frappe.get_doc("Student", student)
        
        # Parse answers
        if isinstance(answers, str):
            answers = json.loads(answers)
        
        # Calculate scores
        total_score = 0
        total_marks = 0
        
        # Get MCQS Assignment for this quiz and student group
        mcqs_assignment = frappe.get_all(
            "MCQS Assignment",
            filters={
                "student_group": student_group,
                "mcqs": quiz_name
            },
            fields=["name"],
            limit=1
        )
        
        if not mcqs_assignment:
            return {
                "status": "error",
                "message": "MCQS Assignment not found for this quiz and student group"
            }
        
        # Get student group details
        student_group_doc = frappe.get_doc("Student Group", student_group)
        
        # Process answers and calculate score
        for answer_data in answers:
            question_name = answer_data.get("question")
            selected_answers = answer_data.get("answers", [])
            marks = answer_data.get("marks", 1)
            total_marks += marks
            
            # Get question details
            question_doc = frappe.get_doc("Question", question_name)
            
            # Check if answer is correct
            is_correct = check_quiz_answer(question_doc, selected_answers)
            score = marks if is_correct else 0
            total_score += score
        
        # Calculate percentage
        percentage = (total_score / total_marks * 100) if total_marks > 0 else 0
        passed = percentage >= (quiz_doc.passing_score or 75)
        
        # Create Assessment Result
        # First, we need to find or create an Assessment Plan
        # For now, we'll create a simple assessment result without assessment plan
        # You may need to adjust this based on your Assessment Plan setup
        
        print(f"\n{'='*80}")
        print(f"QUIZ SUBMISSION - Creating Records")
        print(f"Quiz: {quiz_name}, Student: {student}, Student Group: {student_group}")
        print(f"Score: {total_score}/{total_marks} ({percentage:.1f}%) - {'Passed' if passed else 'Failed'}")
        print(f"{'='*80}\n")
        
        # Try to find existing assessment plan for this student group and course
        assessment_plan = None
        if student_group_doc.course:
            assessment_plans = frappe.get_all(
                "Assessment Plan",
                filters={
                    "student_group": student_group,
                    "course": student_group_doc.course
                },
                fields=["name"],
                limit=1
            )
            if assessment_plans:
                assessment_plan = assessment_plans[0].get('name') if isinstance(assessment_plans[0], dict) else assessment_plans[0].name
                print(f"[ASSESSMENT PLAN] Found: {assessment_plan}")
            else:
                print(f"[ASSESSMENT PLAN] No assessment plan found. Creating new one...")
                
                # Create Assessment Plan if it doesn't exist
                try:
                    # Get course details for defaults
                    course_doc = frappe.get_doc("Course", student_group_doc.course)
                    
                    # Get or create Assessment Group (required field)
                    assessment_group = None
                    assessment_groups = frappe.get_all(
                        "Assessment Group",
                        fields=["name"],
                        limit=1
                    )
                    if assessment_groups:
                        assessment_group = assessment_groups[0].get('name') if isinstance(assessment_groups[0], dict) else assessment_groups[0].name
                    else:
                        # Create a default Assessment Group if none exists
                        try:
                            ag_doc = frappe.new_doc("Assessment Group")
                            ag_doc.assessment_group_name = f"Default Assessment Group"
                            ag_doc.insert(ignore_permissions=True)
                            frappe.db.commit()
                            assessment_group = ag_doc.name
                            print(f"  ✓ Created Assessment Group: {assessment_group}")
                        except Exception as e:
                            print(f"  ✗ Error creating Assessment Group: {str(e)}")
                            # Try to use a default name
                            assessment_group = "Default"
                    
                    # Get grading scale from course or create default
                    grading_scale = getattr(course_doc, 'default_grading_scale', None)
                    if not grading_scale:
                        # Try to find any grading scale
                        grading_scales = frappe.get_all("Grading Scale", fields=["name"], limit=1)
                        if grading_scales:
                            grading_scale = grading_scales[0].get('name') if isinstance(grading_scales[0], dict) else grading_scales[0].name
                        else:
                            grading_scale = None  # Will try to create without it first
                    
                    # Create or get Assessment Criteria - use "Written Assessment"
                    assessment_criteria_name = None
                    criteria_name = "Written Assessment"
                    criteria_list = frappe.get_all(
                        "Assessment Criteria",
                        filters={"assessment_criteria": criteria_name},
                        fields=["name"],
                        limit=1
                    )
                    if criteria_list:
                        assessment_criteria_name = criteria_list[0].get('name') if isinstance(criteria_list[0], dict) else criteria_list[0].name
                        print(f"  ✓ Found Assessment Criteria: {assessment_criteria_name}")
                    else:
                        # Create Assessment Criteria with name "Written Assessment"
                        try:
                            criteria_doc = frappe.new_doc("Assessment Criteria")
                            criteria_doc.assessment_criteria = criteria_name
                            criteria_doc.insert(ignore_permissions=True)
                            frappe.db.commit()
                            assessment_criteria_name = criteria_doc.name
                            print(f"  ✓ Created Assessment Criteria: {assessment_criteria_name} ({criteria_name})")
                        except Exception as e:
                            print(f"  ✗ Error creating Assessment Criteria: {str(e)}")
                            # Use criteria name directly
                            assessment_criteria_name = criteria_name
                    
                    # Create Assessment Plan
                    plan_doc = frappe.new_doc("Assessment Plan")
                    plan_doc.student_group = student_group
                    plan_doc.course = student_group_doc.course
                    plan_doc.assessment_name = f"Quiz Assessment - {quiz_name}"
                    plan_doc.assessment_group = assessment_group
                    plan_doc.schedule_date = today()
                    plan_doc.from_time = "09:00:00"  # Default time
                    plan_doc.to_time = "17:00:00"    # Default time
                    plan_doc.maximum_assessment_score = total_marks
                    
                    if grading_scale:
                        plan_doc.grading_scale = grading_scale
                    
                    # Add assessment criteria to the plan
                    if assessment_criteria_name:
                        plan_doc.append("assessment_criteria", {
                            "assessment_criteria": assessment_criteria_name,
                            "maximum_score": total_marks
                        })
                    
                    # Set program and academic year from student group if available
                    if hasattr(student_group_doc, 'program') and student_group_doc.program:
                        plan_doc.program = student_group_doc.program
                    if hasattr(student_group_doc, 'academic_year') and student_group_doc.academic_year:
                        plan_doc.academic_year = student_group_doc.academic_year
                    if hasattr(student_group_doc, 'academic_term') and student_group_doc.academic_term:
                        plan_doc.academic_term = student_group_doc.academic_term
                    
                    plan_doc.insert(ignore_permissions=True)
                    plan_doc.submit()
                    frappe.db.commit()
                    assessment_plan = plan_doc.name
                    print(f"  ✓ Created Assessment Plan: {assessment_plan}")
                    
                except Exception as e:
                    error_msg = f"Error creating Assessment Plan: {str(e)}"
                    print(f"  ✗ {error_msg}")
                    frappe.log_error(f"{error_msg}\nTraceback: {frappe.get_traceback()}", "Quiz Submission")
                    assessment_plan = None
        else:
            print(f"[ASSESSMENT PLAN] Skipped - No course found in student group")
        
        # Create Assessment Result if assessment plan exists
        assessment_result_id = None
        if assessment_plan:
            try:
                print(f"\n[ASSESSMENT RESULT] Creating Assessment Result...")
                assessment_result = frappe.new_doc("Assessment Result")
                assessment_result.assessment_plan = assessment_plan
                assessment_result.student = student
                assessment_result.total_score = total_score
                
                # Assessment Result requires details table with Assessment Result Detail
                # Get criteria from the Assessment Plan's assessment_criteria table
                plan_doc = frappe.get_doc("Assessment Plan", assessment_plan)
                
                if hasattr(plan_doc, 'assessment_criteria') and plan_doc.assessment_criteria:
                    # Use the criteria from the plan - look for "Written Assessment"
                    written_assessment_found = False
                    for plan_criteria in plan_doc.assessment_criteria:
                        criteria_name = plan_criteria.assessment_criteria
                        criteria_max_score = plan_criteria.maximum_score
                        
                        # Prefer "Written Assessment" criteria
                        if "Written Assessment" in criteria_name:
                            assessment_result.append("details", {
                                "assessment_criteria": criteria_name,
                                "maximum_score": criteria_max_score,
                                "score": total_score if criteria_max_score >= total_score else total_score
                            })
                            print(f"    Added detail: {criteria_name} (max: {criteria_max_score}, score: {total_score})")
                            written_assessment_found = True
                            break
                    
                    # If "Written Assessment" not found, use the first criteria
                    if not written_assessment_found and plan_doc.assessment_criteria:
                        first_criteria = plan_doc.assessment_criteria[0]
                        assessment_result.append("details", {
                            "assessment_criteria": first_criteria.assessment_criteria,
                            "maximum_score": first_criteria.maximum_score,
                            "score": total_score
                        })
                        print(f"    Added first criteria: {first_criteria.assessment_criteria}")
                else:
                    print(f"  ✗ WARNING: Assessment Plan has no criteria. Cannot create Assessment Result without details.")
                    assessment_result = None
                
                if assessment_result:
                    # Set custom_company field (required)
                    company = None
                    try:
                        # Try to get company from various sources
                        # First try user default
                        company = frappe.defaults.get_user_default("Company")
                        if not company:
                            # Try global default
                            company = frappe.defaults.get_global_default("company")
                        if not company:
                            # Try system settings
                            company = frappe.db.get_single_value("System Settings", "default_company")
                        if not company:
                            # Get first available company
                            companies = frappe.get_all("Company", fields=["name"], limit=1)
                            if companies:
                                company = companies[0].get('name') if isinstance(companies[0], dict) else companies[0].name
                        
                        if company:
                            assessment_result.custom_company = company
                            print(f"    Set company: {company}")
                        else:
                            print(f"    ✗ WARNING: No company found. Assessment Result may fail validation.")
                    except Exception as e:
                        print(f"    ✗ WARNING: Error getting company: {str(e)}")
                    
                    assessment_result.insert(ignore_permissions=True)
                    # Don't submit - keep in draft status
                    frappe.db.commit()
                    assessment_result_id = assessment_result.name
                    print(f"  ✓ Assessment Result created (Draft): {assessment_result_id}")
            except Exception as e:
                error_msg = f"Error creating Assessment Result: {str(e)}"
                print(f"  ✗ {error_msg}")
                frappe.log_error(f"{error_msg}\nTraceback: {frappe.get_traceback()}", "Quiz Submission")
        else:
            print(f"[ASSESSMENT RESULT] Skipped - No assessment plan found")
        
        # Try to create Quiz Activity if enrollment exists
        # Quiz Activity requires enrollment, so we'll try to find it
        enrollment = None
        if student_group_doc.course:
            enrollments = frappe.get_all(
                "Course Enrollment",
                filters={
                    "student": student,
                    "course": student_group_doc.course
                },
                fields=["name"],
                limit=1
            )
            if enrollments:
                enrollment = enrollments[0].get('name') if isinstance(enrollments[0], dict) else enrollments[0].name
                print(f"[ENROLLMENT] Found: {enrollment}")
            else:
                print(f"[ENROLLMENT] No enrollment found for student={student}, course={student_group_doc.course}")
        
        # Try to create Quiz Activity if enrollment exists
        activity_id = None
        if enrollment:
            try:
                print(f"\n[QUIZ ACTIVITY] Creating Quiz Activity...")
                quiz_activity = frappe.new_doc("Quiz Activity")
                quiz_activity.enrollment = enrollment
                quiz_activity.student = student
                quiz_activity.quiz = quiz_name
                quiz_activity.score = f"{total_score}/{total_marks}"
                quiz_activity.status = "Pass" if passed else "Fail"
                quiz_activity.activity_date = today()
                
                # Add result details
                for answer_data in answers:
                    question_name = answer_data.get("question")
                    selected_answers = answer_data.get("answers", [])
                    
                    question_doc = frappe.get_doc("Question", question_name)
                    is_correct = check_quiz_answer(question_doc, selected_answers)
                    
                    # Format selected option text
                    # Question doctype uses 'question_type' and 'options' table
                    selected_option_text = ""
                    question_type = getattr(question_doc, 'question_type', 'Single Correct Answer')
                    
                    if question_type in ["Single Correct Answer", "Multiple Correct Answer"]:
                        # Get option text from options table
                        if hasattr(question_doc, 'options') and question_doc.options:
                            option_texts = []
                            for opt_id in selected_answers:
                                # Options are 1-indexed, so subtract 1 for array index
                                opt_idx = opt_id - 1
                                if 0 <= opt_idx < len(question_doc.options):
                                    opt = question_doc.options[opt_idx]
                                    opt_text = getattr(opt, 'option', '')
                                    if opt_text:
                                        option_texts.append(opt_text)
                            selected_option_text = ", ".join(option_texts)
                    else:
                        selected_option_text = ", ".join(map(str, selected_answers))
                    
                    quiz_activity.append("result", {
                        "question": question_name,
                        "selected_option": selected_option_text,
                        "quiz_result": "Correct" if is_correct else "Wrong"
                    })
                
                quiz_activity.insert(ignore_permissions=True)
                quiz_activity.submit()
                frappe.db.commit()
                activity_id = quiz_activity.name
                print(f"  ✓ Quiz Activity created: {activity_id}")
            except Exception as e:
                error_msg = f"Error creating Quiz Activity: {str(e)}"
                print(f"  ✗ {error_msg}")
                frappe.log_error(f"{error_msg}\nTraceback: {frappe.get_traceback()}", "Quiz Submission")
        else:
            print(f"[QUIZ ACTIVITY] Skipped - No enrollment found")
        
        print(f"\n{'='*80}")
        print(f"SUBMISSION COMPLETE")
        print(f"Assessment Result: {assessment_result_id or 'Not created'}")
        print(f"Quiz Activity: {activity_id or 'Not created'}")
        print(f"{'='*80}\n")
        
        # Return result
        return {
            "status": "success",
            "message": "Quiz submitted successfully",
            "assessment_result_id": assessment_result_id,
            "activity_id": activity_id,
            "score": total_score,
            "total_marks": total_marks,
            "percentage": percentage,
            "passed": passed
        }
        
    except Exception as e:
        frappe.log_error(f"Error submitting quiz: {str(e)}", "Quiz API")
        return {
            "status": "error",
            "message": f"Failed to submit quiz: {str(e)}"
        }

def check_quiz_answer(question_doc, selected_answers):
    """Check if the selected answers are correct for Quiz (Education module)"""
    try:
        # Question doctype uses 'question_type' field, not 'type'
        question_type = getattr(question_doc, 'question_type', 'Single Correct Answer')
        
        print(f"\n[CHECK ANSWER] Question: {question_doc.name}, Type: {question_type}")
        print(f"  Selected answers: {selected_answers}")
        
        if question_type in ["Single Correct Answer", "Multiple Correct Answer"]:
            # Question doctype uses 'options' table (child table) with 'option' and 'is_correct' fields
            correct_answers = []
            if hasattr(question_doc, 'options') and question_doc.options:
                for idx, opt in enumerate(question_doc.options):
                    if getattr(opt, 'is_correct', 0):
                        correct_answers.append(idx + 1)  # Options are 1-indexed
            
            print(f"  Correct answers: {correct_answers}")
            
            # Check if selected answers match correct answers
            if len(selected_answers) != len(correct_answers):
                print(f"  ✗ Answer count mismatch: selected={len(selected_answers)}, correct={len(correct_answers)}")
                return False
            
            is_correct = set(selected_answers) == set(correct_answers)
            print(f"  {'✓' if is_correct else '✗'} Answer is {'correct' if is_correct else 'incorrect'}")
            return is_correct
        else:
            # For other types, assume correct if answered
            print(f"  Unknown question type, assuming correct if answered")
            return len(selected_answers) > 0
    
    except Exception as e:
        error_msg = f"Error checking answer: {str(e)}"
        print(f"  ✗ ERROR: {error_msg}")
        frappe.log_error(f"{error_msg}\nTraceback: {frappe.get_traceback()}", "Quiz API")
        return False
