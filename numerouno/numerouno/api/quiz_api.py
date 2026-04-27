import frappe
from frappe import _
from frappe.utils import today
from datetime import timedelta
import json
import urllib.parse
import urllib.request


def _log_public_quiz_audit(event_type, quiz_name=None, student=None, student_group=None, attempt_id=None, details=None):
    """Write structured public quiz audit events to a dedicated site log."""
    if isinstance(details, str):
        try:
            details = json.loads(details)
        except Exception:
            details = {"raw": details}

    payload = {
        "event_type": event_type,
        "quiz_name": quiz_name,
        "student": student,
        "student_group": student_group,
        "attempt_id": attempt_id,
        "details": details or {},
        "ip_address": getattr(frappe.local, "request_ip", None),
        "user_agent": frappe.get_request_header("User-Agent"),
        "request_path": getattr(getattr(frappe.local, "request", None), "path", None),
        "timestamp": frappe.utils.now(),
    }
    frappe.logger("public_quiz_audit", allow_site=True).info(json.dumps(payload, default=str))
    return payload


@frappe.whitelist(allow_guest=True, methods=["POST"])
def log_public_quiz_audit(event_type, quiz_name=None, student=None, student_group=None, attempt_id=None, details=None):
    """Capture client-side quiz audit checkpoints before Quiz Activity creation."""
    payload = _log_public_quiz_audit(
        event_type=event_type,
        quiz_name=quiz_name,
        student=student,
        student_group=student_group,
        attempt_id=attempt_id,
        details=details,
    )
    return {
        "status": "success",
        "logged": True,
        "event_type": payload["event_type"],
        "attempt_id": payload["attempt_id"],
    }

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
def get_course_evaluation_prefill(student_group=None, student=None):
    """Return prefill payload for Course Evaluation web form."""
    try:
        if not student_group:
            return {
                "status": "error",
                "message": "Student group is required"
            }

        sg = frappe.get_doc("Student Group", student_group)

        instructor_name = ""
        if getattr(sg, "instructors", None):
            first_instructor = sg.instructors[0]
            instructor_name = (
                getattr(first_instructor, "instructor", None)
                or getattr(first_instructor, "instructor_name", None)
                or ""
            )

        dates = sg.from_date or today()

        company = ""
        possible_company = getattr(sg, "custom_customer", None) or getattr(sg, "company", None)
        if possible_company and frappe.db.exists("Company", possible_company):
            company = possible_company

        email_id = ""
        trainee_mobile = ""
        if student and frappe.db.exists("Student", student):
            student_row = frappe.db.get_value(
                "Student",
                student,
                ["student_email_id", "custom_phone"],
                as_dict=True,
            ) or {}
            email_id = student_row.get("student_email_id") or ""
            trainee_mobile = student_row.get("custom_phone") or ""

        return {
            "status": "success",
            "data": {
                "course_name": sg.course or "",
                "company": company,
                "instructor_name": instructor_name,
                "dates": str(dates),
                "trainee_name": student or "",
                "email_id": email_id,
                "trainee_mobile": trainee_mobile,
                "student_group": sg.name,
            },
        }
    except Exception as e:
        frappe.log_error(f"Error building course evaluation prefill: {str(e)}", "Quiz API")
        return {
            "status": "error",
            "message": "Failed to build prefill values",
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

def _normalize_quiz_language(lang):
    """Normalize incoming language code for quiz content localization."""
    if not lang:
        return "en"
    code = str(lang).strip().lower()
    if code.startswith("zh"):
        return "zh"
    if code.startswith("hi"):
        return "hi"
    if code.startswith("ar"):
        return "ar"
    if code.startswith("ur"):
        return "ur"
    return "en"


def _lookup_translation(text, lang_code):
    """Try direct Translation doctype lookup for runtime content strings."""
    if not text or lang_code == "en":
        return ""

    try:
        translated = frappe.db.get_value(
            "Translation",
            {"language": lang_code, "source_text": text},
            "translated_text",
        )
        if translated:
            return translated

        stripped = text.strip()
        if stripped and stripped != text:
            translated = frappe.db.get_value(
                "Translation",
                {"language": lang_code, "source_text": stripped},
                "translated_text",
            )
            if translated:
                return translated
    except Exception:
        # Ignore lookup failures and fall back to standard translation resolver.
        pass

    return ""


def _google_target_lang(lang_code):
    if lang_code == "zh":
        return "zh-CN"
    return lang_code


def _google_translate_text(text, lang_code, timeout_sec=4):
    """Translate text with Google public translate endpoint."""
    if not text or lang_code == "en":
        return ""

    try:
        q = urllib.parse.quote(text)
        target = urllib.parse.quote(_google_target_lang(lang_code))
        url = (
            "https://translate.googleapis.com/translate_a/single"
            f"?client=gtx&sl=auto&tl={target}&dt=t&q={q}"
        )
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            payload = resp.read().decode("utf-8", errors="ignore")
        data = json.loads(payload)
        if not isinstance(data, list) or not data or not isinstance(data[0], list):
            return ""
        parts = []
        for chunk in data[0]:
            if isinstance(chunk, list) and chunk and chunk[0]:
                parts.append(str(chunk[0]))
        return "".join(parts).strip()
    except Exception:
        return ""


def _save_translation(source_text, translated_text, lang_code):
    if not source_text or not translated_text or lang_code == "en":
        return

    try:
        existing_name = frappe.db.exists(
            "Translation",
            {"language": lang_code, "source_text": source_text},
        )
        if existing_name:
            if frappe.db.get_value("Translation", existing_name, "translated_text") != translated_text:
                frappe.db.set_value("Translation", existing_name, "translated_text", translated_text, update_modified=False)
            return

        doc = frappe.get_doc(
            {
                "doctype": "Translation",
                "language": lang_code,
                "source_text": source_text,
                "translated_text": translated_text,
            }
        )
        doc.insert(ignore_permissions=True)
    except Exception:
        pass


def _enqueue_translation_if_missing(text, lang_code):
    """Queue translation without blocking request latency."""
    if not text or lang_code == "en":
        return

    # Per-request dedupe
    req_cache = getattr(frappe.local, "quiz_translation_cache", None)
    if req_cache is None:
        req_cache = {}
        frappe.local.quiz_translation_cache = req_cache

    cache_key = f"{lang_code}::{text}"
    if cache_key in req_cache:
        return
    req_cache[cache_key] = True

    # Cross-request throttle to avoid enqueue storms for same source text.
    try:
        cache = frappe.cache()
        throttle_key = f"quiz_translate_enqueue::{cache_key}"
        if cache.get_value(throttle_key):
            return
        cache.set_value(throttle_key, 1, expires_in_sec=600)
    except Exception:
        pass

    try:
        frappe.enqueue(
            "numerouno.numerouno.api.quiz_api.translate_and_store_text",
            queue="short",
            timeout=120,
            source_text=text,
            lang_code=lang_code,
            enqueue_after_commit=True,
        )
    except Exception:
        pass


def translate_and_store_text(source_text, lang_code):
    """Background job: translate and persist into Translation doctype."""
    if not source_text or not lang_code or lang_code == "en":
        return

    if _lookup_translation(source_text, lang_code):
        return

    translated = _google_translate_text(source_text, lang_code)
    if translated:
        _save_translation(source_text, translated, lang_code)


def _tr_text(value, lang_code="en"):
    text = value or ""
    if not text:
        return ""

    translated = _lookup_translation(text, lang_code)
    if translated:
        return translated

    # Hybrid mode:
    # 1) Try quick inline translation so first load can show translated text.
    # 2) If it fails, queue background translation and return source text.
    translated = _google_translate_text(text, lang_code, timeout_sec=1.5)
    if translated:
        _save_translation(text, translated, lang_code)
        return translated

    # Non-blocking fallback
    _enqueue_translation_if_missing(text, lang_code)

    return _(text)


@frappe.whitelist(allow_guest=True, methods=['GET', 'POST'])
def get_quiz_questions_from_quiz(quiz_name, lang=None):
    """Get quiz questions from Quiz doctype (Education module)"""
    previous_lang = getattr(frappe.local, "lang", None)
    try:
        lang_code = _normalize_quiz_language(lang)
        frappe.local.lang = lang_code
        print(f"\n{'='*80}")
        print(f"GET QUIZ QUESTIONS - Quiz: {quiz_name}, Lang: {lang_code}")
        print(f"{'='*80}")
        
        if not quiz_name:
            return {
                "status": "error",
                "message": "Quiz name is required"
            }
        
        # Get quiz details
        print(f"Getting Quiz document: {quiz_name}")
        quiz_doc = frappe.get_doc("Quiz", quiz_name)
        quiz_title = _tr_text(quiz_doc.title, lang_code)
        print(f"Quiz found: {quiz_doc.name} - {quiz_title}")
        
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
                    "question": _tr_text(question_doc.question, lang_code),
                    "type": getattr(question_doc, 'question_type', 'Single Correct Answer'),
                    "marks": 1,  # Default to 1 mark since QuizQuestion doesn't have marks
                    "options": []
                }
                
                # Question doctype uses 'options' table (child table)
                # Options table has: 'option' (text) and 'is_correct' (checkbox)
                if hasattr(question_doc, 'options') and question_doc.options:
                    print(f"    Question has {len(question_doc.options)} options")
                    for opt_idx, opt in enumerate(question_doc.options):
                        option_text = _tr_text(getattr(opt, 'option', ''), lang_code)
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
                "title": quiz_title,
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
    finally:
        frappe.local.lang = previous_lang

@frappe.whitelist(allow_guest=True, methods=['GET', 'POST'])
def submit_quiz_from_mcqs(quiz_name, student, student_group, answers, attempt_id=None):
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
        _log_public_quiz_audit(
            event_type="submit_received",
            quiz_name=quiz_name,
            student=student,
            student_group=student_group,
            attempt_id=attempt_id,
            details={"answer_count": len(answers) if isinstance(answers, list) else 0},
        )
        
        # Calculate raw score first (raw marks), then scale to 100 for UI response
        raw_score = 0
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
            raw_score += score
        
        # Calculate percentage and scaled score out of 100
        percentage = (raw_score / total_marks * 100) if total_marks > 0 else 0
        scaled_score = round(percentage, 2)
        display_score = round(percentage)
        passed = percentage >= (quiz_doc.passing_score or 75)
        
        # Create Assessment Result
        # First, we need to find or create an Assessment Plan
        # For now, we'll create a simple assessment result without assessment plan
        # You may need to adjust this based on your Assessment Plan setup
        
        print(f"\n{'='*80}")
        print(f"QUIZ SUBMISSION - Creating Records")
        print(f"Quiz: {quiz_name}, Student: {student}, Student Group: {student_group}")
        print(f"Score: {display_score}/100 (raw: {raw_score}/{total_marks}, {percentage:.1f}%) - {'Passed' if passed else 'Failed'}")
        print(f"{'='*80}\n")
        
        # Try to find existing assessment plan for this student group and course
        assessment_plan = None
        if student_group_doc.course:
            assessment_plans = frappe.get_all(
                "Assessment Plan",
                filters={
                    "student_group": student_group,
                    "course": student_group_doc.course,
                    "docstatus": ["<", 2]
                },
                fields=["name"],
                order_by="docstatus desc, modified desc",
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
        assessment_result_error = None
        if assessment_plan:
            try:
                print(f"\n[ASSESSMENT RESULT] Creating Assessment Result...")
                assessment_result = frappe.new_doc("Assessment Result")
                assessment_result.assessment_plan = assessment_plan
                assessment_result.student = student
                # Keep explicit student group context to satisfy validations/custom logic.
                if hasattr(assessment_result, "student_group"):
                    assessment_result.student_group = student_group
                assessment_result.total_score = raw_score
                
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
                                "score": raw_score if criteria_max_score >= raw_score else raw_score
                            })
                            print(f"    Added detail: {criteria_name} (max: {criteria_max_score}, score: {raw_score})")
                            written_assessment_found = True
                            break
                    
                    # If "Written Assessment" not found, use the first criteria
                    if not written_assessment_found and plan_doc.assessment_criteria:
                        first_criteria = plan_doc.assessment_criteria[0]
                        assessment_result.append("details", {
                            "assessment_criteria": first_criteria.assessment_criteria,
                            "maximum_score": first_criteria.maximum_score,
                            "score": raw_score
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
                    frappe.db.commit()
                    assessment_result_id = assessment_result.name
                    print(f"  ✓ Assessment Result created: {assessment_result_id}")

                    # Submit by default for public quiz flow
                    try:
                        assessment_result.reload()
                        assessment_result.submit()
                        frappe.db.commit()
                        print(f"  ✓ Assessment Result submitted: {assessment_result_id}")
                    except Exception as submit_error:
                        error_msg = f"Failed to submit Assessment Result {assessment_result_id}: {str(submit_error)}"
                        print(f"  ✗ {error_msg}")
                        frappe.log_error(f"{error_msg}\nTraceback: {frappe.get_traceback()}", "Quiz Submission")
                        assessment_result_error = error_msg
            except Exception as e:
                error_msg = f"Error creating Assessment Result: {str(e)}"
                print(f"  ✗ {error_msg}")
                frappe.log_error(f"{error_msg}\nTraceback: {frappe.get_traceback()}", "Quiz Submission")
                # Store error for later - will be added to Quiz Activity comments
                assessment_result_error = error_msg
        else:
            print(f"[ASSESSMENT RESULT] Skipped - No assessment plan found")
            assessment_result_error = "No Assessment Plan found for this Student Group and Course. Please create an Assessment Plan first."
        
        # Try to create Quiz Activity even if enrollment is missing
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

        activity_id = None
        activity_error = None
        try:
            print(f"\n[QUIZ ACTIVITY] Creating Quiz Activity...")
            quiz_activity = frappe.new_doc("Quiz Activity")
            if enrollment:
                quiz_activity.enrollment = enrollment
            else:
                quiz_activity.flags.ignore_mandatory = True
            quiz_activity.student = student
            quiz_activity.quiz = quiz_name
            quiz_activity.score = f"{raw_score}/{total_marks}"
            quiz_activity.status = "Pass" if passed else "Fail"
            quiz_activity.activity_date = today()
            # Preserve exact context from public quiz submission to avoid fallback guessing.
            if hasattr(quiz_activity, "custom_student_group"):
                quiz_activity.custom_student_group = student_group
            if assessment_plan and hasattr(quiz_activity, "custom_assesment_plan"):
                quiz_activity.custom_assesment_plan = assessment_plan
            
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

            if enrollment:
                quiz_activity.insert(ignore_permissions=True)
                quiz_activity.submit()
            else:
                quiz_activity.insert(ignore_permissions=True, ignore_mandatory=True)

            frappe.db.commit()
            activity_id = quiz_activity.name
            print(f"  ✓ Quiz Activity created: {activity_id}")
            
            # Add error message to Quiz Activity comments if Assessment Result creation failed
            if assessment_result_error:
                try:
                    from frappe.desk.doctype.comment.comment import add_comment
                    comment_text = f"⚠️ Assessment Result Creation Failed:\n{assessment_result_error}\n\nPlease use the 'Create Assessment Result' button to create it manually."
                    add_comment(
                        reference_doctype="Quiz Activity",
                        reference_name=activity_id,
                        content=comment_text,
                        comment_email=frappe.session.user or "system",
                        comment_by=frappe.session.user or "system"
                    )
                    print(f"  ✓ Error message added to Quiz Activity comments")
                except Exception as comment_error:
                    print(f"  ✗ Could not add comment: {str(comment_error)}")
            
        except Exception as e:
            error_msg = f"Error creating Quiz Activity: {str(e)}"
            print(f"  ✗ {error_msg}")
            frappe.log_error(f"{error_msg}\nTraceback: {frappe.get_traceback()}", "Quiz Submission")
            activity_error = error_msg
        
        # Fallback: if Assessment Result wasn't created directly, try creating it from Quiz Activity
        if not assessment_result_id and activity_id:
            try:
                print(f"\n[ASSESSMENT RESULT FALLBACK] Trying creation from Quiz Activity: {activity_id}")
                fallback_result = create_assessment_result_from_quiz_activity(activity_id)
                fallback_status = (fallback_result or {}).get("status")
                fallback_assessment_id = (fallback_result or {}).get("assessment_result_id") or (fallback_result or {}).get("assessment_result")
                if fallback_status in ("success", "info") and fallback_assessment_id:
                    assessment_result_id = fallback_assessment_id
                    assessment_result_error = None
                    print(f"  ✓ Fallback Assessment Result created: {assessment_result_id}")
                else:
                    print(f"  ✗ Fallback failed: {fallback_result}")
                    assessment_result_error = (
                        (fallback_result or {}).get("message")
                        or "Fallback Assessment Result creation failed"
                    )
                    _log_public_quiz_audit(
                        event_type="assessment_result_missing",
                        quiz_name=quiz_name,
                        student=student,
                        student_group=student_group,
                        attempt_id=attempt_id,
                        details={
                            "activity_id": activity_id,
                            "assessment_result_error": assessment_result_error,
                        },
                    )
            except Exception as fallback_err:
                print(f"  ✗ Fallback exception: {str(fallback_err)}")
                frappe.log_error(
                    f"Fallback Assessment Result creation failed: {str(fallback_err)}\nTraceback: {frappe.get_traceback()}",
                    "Quiz Submission"
                )
                assessment_result_error = str(fallback_err)
                _log_public_quiz_audit(
                    event_type="assessment_result_exception",
                    quiz_name=quiz_name,
                    student=student,
                    student_group=student_group,
                    attempt_id=attempt_id,
                    details={
                        "activity_id": activity_id,
                        "assessment_result_error": assessment_result_error,
                    },
                )
        
        print(f"\n{'='*80}")
        print(f"SUBMISSION COMPLETE")
        print(f"Assessment Result: {assessment_result_id or 'Not created'}")
        print(f"Quiz Activity: {activity_id or 'Not created'}")
        print(f"{'='*80}\n")

        frappe.logger().info(
            f"[PUBLIC QUIZ SUBMIT] Completed submission for quiz={quiz_name}, "
            f"student={student}, student_group={student_group}, "
            f"activity_id={activity_id or 'NONE'}, assessment_result_id={assessment_result_id or 'NONE'}"
        )

        if not activity_id:
            message = (
                "Quiz answers were received but Quiz Activity could not be created. "
                "Course Evaluation was not recorded as quiz completion."
            )
            if activity_error:
                message = f"{message} Reason: {activity_error}"
            frappe.logger().error(
                f"[PUBLIC QUIZ SUBMIT] Quiz Activity missing after submission for "
                f"quiz={quiz_name}, student={student}, student_group={student_group}. "
                f"activity_error={activity_error or 'N/A'}"
            )
            _log_public_quiz_audit(
                event_type="quiz_activity_missing",
                quiz_name=quiz_name,
                student=student,
                student_group=student_group,
                attempt_id=attempt_id,
                details={"activity_error": activity_error},
            )
            return {
                "status": "error",
                "message": message,
                "assessment_result_id": assessment_result_id,
                "assessment_result_error": assessment_result_error,
                "activity_id": None,
                "activity_error": activity_error,
                "score": display_score,
                "score_exact": scaled_score,
                "raw_score": raw_score,
                "total_marks": total_marks,
                "percentage": percentage,
                "passed": passed,
            }
        
        # Return result
        response_message = "Quiz submitted successfully"
        if not assessment_result_id:
            response_message = (
                "Quiz submitted and Quiz Activity created, but Assessment Result was not created automatically."
            )
        _log_public_quiz_audit(
            event_type="submission_completed",
            quiz_name=quiz_name,
            student=student,
            student_group=student_group,
            attempt_id=attempt_id,
            details={
                "activity_id": activity_id,
                "assessment_result_id": assessment_result_id,
                "assessment_result_error": assessment_result_error,
                "score": display_score,
                "percentage": percentage,
                "passed": passed,
            },
        )

        return {
            "status": "success",
            "message": response_message,
            "assessment_result_id": assessment_result_id,
            "assessment_result_error": assessment_result_error,
            "activity_id": activity_id,
            "activity_error": activity_error,
            "score": display_score,
            "score_exact": scaled_score,
            "raw_score": raw_score,
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

def _time_to_seconds(time_val):
    if not time_val:
        return 0
    if isinstance(time_val, timedelta):
        return int(time_val.total_seconds())
    if hasattr(time_val, "hour"):
        return time_val.hour * 3600 + time_val.minute * 60 + (time_val.second or 0)
    parts = str(time_val).split(":")
    if len(parts) >= 2:
        try:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2]) if len(parts) > 2 else 0
            return hours * 3600 + minutes * 60 + seconds
        except (ValueError, IndexError):
            return 0
    return 0


def _times_overlap(start1, end1, start2, end2):
    s1 = _time_to_seconds(start1)
    e1 = _time_to_seconds(end1)
    s2 = _time_to_seconds(start2)
    e2 = _time_to_seconds(end2)
    return s1 < e2 and e1 > s2


def _find_reusable_assessment_plan(student_group, course, quiz_name=None):
    if not student_group or not course:
        return None

    candidate_filters = []
    if quiz_name:
        candidate_filters.append({
            "student_group": student_group,
            "course": course,
            "assessment_name": f"Quiz Assessment - {quiz_name}",
            "docstatus": ["<", 2],
        })
    candidate_filters.append({
        "student_group": student_group,
        "course": course,
        "docstatus": ["<", 2],
    })

    for filters in candidate_filters:
        plans = frappe.get_all(
            "Assessment Plan",
            filters=filters,
            fields=["name", "docstatus", "modified"],
            order_by="docstatus desc, modified desc",
            limit=1,
        )
        if plans:
            return plans[0].name

    return None


def _get_time_conflicts(doctype, student_group, schedule_date):
    return frappe.get_all(
        doctype,
        filters={
            "student_group": student_group,
            "schedule_date": schedule_date,
            "docstatus": ["<", 2],
        },
        fields=["name", "from_time", "to_time"],
    )


def _find_available_assessment_slot(student_group, start_date=None, max_days=10):
    start_date = frappe.utils.getdate(start_date or today())
    slot_candidates = [
        ("06:00:00", "08:00:00"),
        ("08:15:00", "10:15:00"),
        ("10:30:00", "12:30:00"),
        ("13:00:00", "15:00:00"),
        ("15:15:00", "17:15:00"),
        ("18:00:00", "20:00:00"),
        ("20:15:00", "22:15:00"),
    ]

    for day_offset in range(max_days):
        schedule_date = frappe.utils.add_days(start_date, day_offset)
        course_schedule_conflicts = _get_time_conflicts("Course Schedule", student_group, schedule_date)
        assessment_plan_conflicts = _get_time_conflicts("Assessment Plan", student_group, schedule_date)

        for from_time, to_time in slot_candidates:
            has_conflict = False
            for conflict in course_schedule_conflicts + assessment_plan_conflicts:
                if _times_overlap(from_time, to_time, conflict.from_time or "00:00:00", conflict.to_time or "23:59:59"):
                    has_conflict = True
                    break
            if not has_conflict:
                return str(schedule_date), from_time, to_time

    return None, None, None


def _update_quiz_activity_plan_link(quiz_activity_name, assessment_plan):
    try:
        quiz_activity_doc = frappe.get_doc("Quiz Activity", quiz_activity_name)
        if hasattr(quiz_activity_doc, "custom_assesment_plan"):
            quiz_activity_doc.custom_assesment_plan = assessment_plan
            quiz_activity_doc.save(ignore_permissions=True)
            frappe.db.commit()
            frappe.logger().info(f"[QUIZ ACTIVITY] Updated custom_assesment_plan: {assessment_plan}")
    except Exception as update_err:
        frappe.logger().error(f"[QUIZ ACTIVITY] Failed to update custom_assesment_plan: {str(update_err)}")


def _auto_create_assessment_plan(student_group_doc, student_group, quiz_name, total_marks, quiz_activity_name, student):
    frappe.logger().info("[ASSESSMENT PLAN] Starting resilient auto-creation of Assessment Plan...")

    course_doc = frappe.get_doc("Course", student_group_doc.course)

    assessment_groups = frappe.get_all("Assessment Group", fields=["name"], limit=1)
    if assessment_groups:
        assessment_group = assessment_groups[0].name
    else:
        ag_doc = frappe.new_doc("Assessment Group")
        ag_doc.assessment_group_name = "Default Assessment Group"
        ag_doc.insert(ignore_permissions=True)
        frappe.db.commit()
        assessment_group = ag_doc.name

    grading_scale = getattr(course_doc, "default_grading_scale", None)
    if not grading_scale:
        grading_scales = frappe.get_all("Grading Scale", fields=["name"], limit=1)
        if grading_scales:
            grading_scale = grading_scales[0].name

    criteria_name = "Written Assessment"
    criteria_list = frappe.get_all(
        "Assessment Criteria",
        filters={"assessment_criteria": criteria_name},
        fields=["name"],
        limit=1,
    )
    if criteria_list:
        assessment_criteria_name = criteria_list[0].name
    else:
        criteria_doc = frappe.new_doc("Assessment Criteria")
        criteria_doc.assessment_criteria = criteria_name
        criteria_doc.insert(ignore_permissions=True)
        frappe.db.commit()
        assessment_criteria_name = criteria_doc.name

    schedule_date, from_time, to_time = _find_available_assessment_slot(student_group)
    if not schedule_date:
        raise frappe.ValidationError(
            f"No non-conflicting Assessment Plan slot found for Student Group {student_group} in the next 10 days."
        )

    frappe.logger().info(
        f"[ASSESSMENT PLAN] Selected slot for auto-create: {schedule_date} {from_time}-{to_time}"
    )

    plan_doc = frappe.new_doc("Assessment Plan")
    plan_doc.student_group = student_group
    plan_doc.course = student_group_doc.course
    plan_doc.assessment_name = f"Quiz Assessment - {quiz_name}"
    plan_doc.assessment_group = assessment_group
    plan_doc.schedule_date = schedule_date
    plan_doc.from_time = from_time
    plan_doc.to_time = to_time
    plan_doc.maximum_assessment_score = total_marks

    if grading_scale:
        plan_doc.grading_scale = grading_scale

    plan_doc.append("assessment_criteria", {
        "assessment_criteria": assessment_criteria_name,
        "maximum_score": total_marks,
    })

    if getattr(student_group_doc, "program", None):
        plan_doc.program = student_group_doc.program
    if getattr(student_group_doc, "academic_year", None):
        plan_doc.academic_year = student_group_doc.academic_year
    if getattr(student_group_doc, "academic_term", None):
        plan_doc.academic_term = student_group_doc.academic_term

    plan_doc.insert(ignore_permissions=True)
    frappe.db.commit()
    assessment_plan = plan_doc.name
    frappe.logger().info(f"[ASSESSMENT PLAN] Auto-created Assessment Plan: {assessment_plan}")

    try:
        plan_doc.submit()
        frappe.db.commit()
        frappe.logger().info(f"[ASSESSMENT PLAN] Auto-created plan submitted: {assessment_plan}")
    except frappe.ValidationError as submit_ve:
        frappe.logger().warning(
            f"[ASSESSMENT PLAN] Auto-created plan kept in draft after submit validation error: {submit_ve}"
        )

    _update_quiz_activity_plan_link(quiz_activity_name, assessment_plan)

    try:
        from frappe.desk.doctype.comment.comment import add_comment
        add_comment(
            reference_doctype="Quiz Activity",
            reference_name=quiz_activity_name,
            content=(
                f"✅ Assessment Plan auto-created: {assessment_plan}\n\n"
                f"Student Group: {student_group}\n"
                f"Course: {student_group_doc.course}\n"
                f"Student: {student}\n"
                f"Slot: {schedule_date} {from_time}-{to_time}"
            ),
            comment_email=frappe.session.user or "system",
            comment_by=frappe.session.user or "system",
        )
        frappe.db.commit()
    except Exception as comment_err:
        frappe.log_error(f"Failed to add plan creation comment: {str(comment_err)}", "Quiz Activity Comment Error")

    return assessment_plan


@frappe.whitelist()
def create_assessment_result_from_quiz_activity(quiz_activity_name):
    """Create Assessment Result from Quiz Activity manually"""
    frappe.logger().info(f"="*80)
    frappe.logger().info(f"[CREATE ASSESSMENT RESULT] Starting for Quiz Activity: {quiz_activity_name}")
    frappe.logger().info(f"="*80)
    
    try:
        # Get Quiz Activity
        frappe.logger().info(f"[CREATE ASSESSMENT RESULT] Step 1: Loading Quiz Activity: {quiz_activity_name}")
        quiz_activity = frappe.get_doc("Quiz Activity", quiz_activity_name)
        frappe.logger().info(f"[CREATE ASSESSMENT RESULT] Quiz Activity loaded: {quiz_activity.name}")
        frappe.logger().info(f"  - Student: {quiz_activity.student}")
        frappe.logger().info(f"  - Quiz: {quiz_activity.quiz}")
        frappe.logger().info(f"  - Enrollment: {quiz_activity.enrollment}")
        frappe.logger().info(f"  - Score: {quiz_activity.score}")
        
        if not quiz_activity.student:
            error_msg = "Student is required in Quiz Activity"
            
            # Add error to Quiz Activity comments
            try:
                from frappe.desk.doctype.comment.comment import add_comment
                comment_text = f"❌ {error_msg}"
                add_comment(
                    reference_doctype="Quiz Activity",
                    reference_name=quiz_activity_name,
                    content=comment_text,
                    comment_email=frappe.session.user or "system",
                    comment_by=frappe.session.user or "system"
                )
            except:
                pass
            
            return {
                "status": "error",
                "message": error_msg
            }
        
        if not quiz_activity.quiz:
            error_msg = "Quiz is required in Quiz Activity"
            
            # Add error to Quiz Activity comments
            try:
                from frappe.desk.doctype.comment.comment import add_comment
                comment_text = f"❌ {error_msg}"
                add_comment(
                    reference_doctype="Quiz Activity",
                    reference_name=quiz_activity_name,
                    content=comment_text,
                    comment_email=frappe.session.user or "system",
                    comment_by=frappe.session.user or "system"
                )
            except:
                pass
            
            return {
                "status": "error",
                "message": error_msg
            }
        
        student = quiz_activity.student
        quiz_name = quiz_activity.quiz
        
        # Prefer explicit student group from Quiz Activity when available.
        student_group = None
        if hasattr(quiz_activity, "custom_student_group") and quiz_activity.custom_student_group:
            if frappe.db.exists("Student Group", quiz_activity.custom_student_group):
                student_group = quiz_activity.custom_student_group

        # Get student group from enrollment if not already resolved.
        if not student_group and quiz_activity.enrollment:
            enrollment_doc = frappe.get_doc("Course Enrollment", quiz_activity.enrollment)
            if enrollment_doc.student_group:
                student_group = enrollment_doc.student_group
        
        # If no student group from enrollment, try to find from student
        if not student_group:
            student_groups = frappe.get_all(
                "Student Group Student",
                filters={"student": student},
                fields=["parent"],
                order_by="creation desc",
                limit=1
            )
            if student_groups:
                student_group = student_groups[0].parent
        
        if not student_group:
            error_msg = "Student Group not found. Please ensure student is assigned to a Student Group."
            
            # Add error to Quiz Activity comments
            try:
                from frappe.desk.doctype.comment.comment import add_comment
                comment_text = f"❌ {error_msg}"
                add_comment(
                    reference_doctype="Quiz Activity",
                    reference_name=quiz_activity_name,
                    content=comment_text,
                    comment_email=frappe.session.user or "system",
                    comment_by=frappe.session.user or "system"
                )
            except:
                pass
            
            return {
                "status": "error",
                "message": error_msg
            }
        
        student_group_doc = frappe.get_doc("Student Group", student_group)
        
        # Update Quiz Activity with Student Group
        try:
            quiz_activity_doc = frappe.get_doc("Quiz Activity", quiz_activity_name)
            if hasattr(quiz_activity_doc, 'custom_student_group'):
                quiz_activity_doc.custom_student_group = student_group
                quiz_activity_doc.save(ignore_permissions=True)
                frappe.db.commit()
                frappe.logger().info(f"[QUIZ ACTIVITY] Updated custom_student_group: {student_group}")
        except Exception as update_err:
            frappe.logger().error(f"[QUIZ ACTIVITY] Failed to update custom_student_group: {str(update_err)}")
        
        # Parse score from Quiz Activity
        score_str = quiz_activity.score or "0/0"
        if "/" in score_str:
            total_score, total_marks = map(int, score_str.split("/"))
        else:
            total_score = 0
            total_marks = 0
        
        # Find or create Assessment Plan
        frappe.logger().info(f"[ASSESSMENT PLAN] Starting Assessment Plan lookup/creation")
        frappe.logger().info(f"[ASSESSMENT PLAN] Student: {student}, Student Group: {student_group}, Course: {student_group_doc.course if student_group_doc.course else 'None'}")

        assessment_plan = None
        if hasattr(quiz_activity, "custom_assesment_plan") and quiz_activity.custom_assesment_plan:
            if frappe.db.exists("Assessment Plan", quiz_activity.custom_assesment_plan):
                assessment_plan = quiz_activity.custom_assesment_plan
                frappe.logger().info(f"[ASSESSMENT PLAN] Using Assessment Plan from Quiz Activity: {assessment_plan}")

        if not assessment_plan and student_group_doc.course:
            assessment_plan = _find_reusable_assessment_plan(student_group, student_group_doc.course, quiz_name)
            if assessment_plan:
                frappe.logger().info(f"[ASSESSMENT PLAN] Reusing existing Assessment Plan: {assessment_plan}")
                _update_quiz_activity_plan_link(quiz_activity_name, assessment_plan)
            else:
                frappe.logger().info("[ASSESSMENT PLAN] No reusable Assessment Plan found. Auto-creating a new one.")
                try:
                    assessment_plan = _auto_create_assessment_plan(
                        student_group_doc=student_group_doc,
                        student_group=student_group,
                        quiz_name=quiz_name,
                        total_marks=total_marks,
                        quiz_activity_name=quiz_activity_name,
                        student=student,
                    )
                except Exception as e:
                    error_msg = str(getattr(e, "message", None) or (e.args[0] if getattr(e, "args", None) else str(e)))
                    frappe.log_error(
                        f"Failed to auto-create Assessment Plan: {error_msg}\n\nTraceback:\n{frappe.get_traceback()}",
                        "Create Assessment Result from Quiz Activity",
                    )

                    try:
                        from frappe.desk.doctype.comment.comment import add_comment
                        add_comment(
                            reference_doctype="Quiz Activity",
                            reference_name=quiz_activity_name,
                            content=(
                                f"❌ Error creating Assessment Plan automatically:\n\n{error_msg}\n\n"
                                f"Student Group: {student_group}\nCourse: {student_group_doc.course}"
                            ),
                            comment_email=frappe.session.user or "system",
                            comment_by=frappe.session.user or "system",
                        )
                        frappe.db.commit()
                    except Exception:
                        pass

                    return {
                        "status": "error",
                        "message": error_msg
                    }
        
        if not assessment_plan:
            error_msg = f"Assessment Plan not found for Student Group '{student_group}' and Course '{student_group_doc.course if student_group_doc.course else 'N/A'}'. Please create an Assessment Plan first."
            
            # Add error to Quiz Activity comments
            try:
                from frappe.desk.doctype.comment.comment import add_comment
                comment_text = f"❌ {error_msg}"
                add_comment(
                    reference_doctype="Quiz Activity",
                    reference_name=quiz_activity_name,
                    content=comment_text,
                    comment_email=frappe.session.user or "system",
                    comment_by=frappe.session.user or "system"
                )
            except:
                pass
            
            return {
                "status": "error",
                "message": error_msg
            }
        
        # Check if Assessment Result already exists
        frappe.logger().info(f"[ASSESSMENT RESULT] Checking for existing Assessment Result...")
        frappe.logger().info(f"  - Student: {student}")
        frappe.logger().info(f"  - Assessment Plan: {assessment_plan}")
        existing_result = frappe.db.exists("Assessment Result", {
            "student": student,
            "assessment_plan": assessment_plan,
            "docstatus": ["<", 2]
        })
        
        if existing_result:
            frappe.logger().info(f"[ASSESSMENT RESULT] Existing Assessment Result found: {existing_result}")

            # Ensure existing result is submitted (not left in draft)
            try:
                existing_result_doc = frappe.get_doc("Assessment Result", existing_result)
                if existing_result_doc.docstatus == 0:
                    frappe.logger().info(f"[ASSESSMENT RESULT] Existing result is draft. Submitting: {existing_result}")
                    existing_result_doc.flags.ignore_permissions = True
                    existing_result_doc.submit()
                    frappe.db.commit()
                    frappe.logger().info(f"[ASSESSMENT RESULT] ✓ Existing draft submitted: {existing_result}")
            except Exception as submit_existing_err:
                error_msg = f"Failed to submit existing Assessment Result {existing_result}: {str(submit_existing_err)}"
                frappe.log_error(f"{error_msg}\nTraceback: {frappe.get_traceback()}", "Assessment Result Submit Error")
                return {
                    "status": "error",
                    "message": error_msg,
                    "assessment_result_id": existing_result
                }
            
            # Update Quiz Activity with existing Assessment Result link and other custom fields
            try:
                quiz_activity_doc = frappe.get_doc("Quiz Activity", quiz_activity_name)
                updated = False
                
                # Set custom_assesment_result (note: typo in field name)
                if hasattr(quiz_activity_doc, 'custom_assesment_result'):
                    quiz_activity_doc.custom_assesment_result = existing_result
                    updated = True
                    frappe.logger().info(f"[ASSESSMENT RESULT] Set custom_assesment_result: {existing_result}")
                # Also try custom_assessment_result (correct spelling)
                elif hasattr(quiz_activity_doc, 'custom_assessment_result'):
                    quiz_activity_doc.custom_assessment_result = existing_result
                    updated = True
                    frappe.logger().info(f"[ASSESSMENT RESULT] Set custom_assessment_result: {existing_result}")
                # Try assessment_result field (if exists)
                elif hasattr(quiz_activity_doc, 'assessment_result'):
                    quiz_activity_doc.assessment_result = existing_result
                    updated = True
                    frappe.logger().info(f"[ASSESSMENT RESULT] Set assessment_result: {existing_result}")
                # If neither exists, try to add via db_set
                else:
                    meta = frappe.get_meta("Quiz Activity")
                    if meta.has_field("custom_assesment_result"):
                        quiz_activity_doc.db_set("custom_assesment_result", existing_result, update_modified=False)
                        updated = True
                        frappe.logger().info(f"[ASSESSMENT RESULT] Set custom_assesment_result via db_set: {existing_result}")
                    elif meta.has_field("custom_assessment_result"):
                        quiz_activity_doc.db_set("custom_assessment_result", existing_result, update_modified=False)
                        updated = True
                        frappe.logger().info(f"[ASSESSMENT RESULT] Set custom_assessment_result via db_set: {existing_result}")
                    elif meta.has_field("assessment_result"):
                        quiz_activity_doc.db_set("assessment_result", existing_result, update_modified=False)
                        updated = True
                        frappe.logger().info(f"[ASSESSMENT RESULT] Set assessment_result via db_set: {existing_result}")
                
                # Also ensure custom_assesment_plan is set
                if hasattr(quiz_activity_doc, 'custom_assesment_plan') and assessment_plan:
                    quiz_activity_doc.custom_assesment_plan = assessment_plan
                    updated = True
                    frappe.logger().info(f"[ASSESSMENT RESULT] Set custom_assesment_plan: {assessment_plan}")
                
                # Also ensure custom_student_group is set
                if hasattr(quiz_activity_doc, 'custom_student_group') and student_group:
                    quiz_activity_doc.custom_student_group = student_group
                    updated = True
                    frappe.logger().info(f"[ASSESSMENT RESULT] Set custom_student_group: {student_group}")
                
                if updated:
                    quiz_activity_doc.save(ignore_permissions=True)
                    frappe.db.commit()
                    frappe.logger().info(f"[ASSESSMENT RESULT] ✓ Quiz Activity updated with all custom fields")
            except Exception as update_err:
                frappe.logger().error(f"[ASSESSMENT RESULT] Failed to update Quiz Activity: {str(update_err)}")
            
            return {
                "status": "info",
                "message": f"Assessment Result already exists: {existing_result}",
                "assessment_result_id": existing_result
            }
        
        # Create Assessment Result
        frappe.logger().info(f"[ASSESSMENT RESULT] Creating new Assessment Result...")
        frappe.logger().info(f"[ASSESSMENT RESULT] Loading Assessment Plan: {assessment_plan}")
        plan_doc = frappe.get_doc("Assessment Plan", assessment_plan)
        frappe.logger().info(f"[ASSESSMENT RESULT] Assessment Plan loaded. Criteria count: {len(plan_doc.assessment_criteria) if plan_doc.assessment_criteria else 0}")
        
        assessment_result = frappe.new_doc("Assessment Result")
        assessment_result.assessment_plan = assessment_plan
        assessment_result.student = student
        assessment_result.student_group = student_group
        assessment_result.total_score = total_score
        frappe.logger().info(f"[ASSESSMENT RESULT] Assessment Result document created with:")
        frappe.logger().info(f"  - assessment_plan: {assessment_result.assessment_plan}")
        frappe.logger().info(f"  - student: {assessment_result.student}")
        frappe.logger().info(f"  - student_group: {assessment_result.student_group}")
        frappe.logger().info(f"  - total_score: {assessment_result.total_score}")
        
        # Add details from Assessment Plan
        written_assessment_found = False
        if plan_doc.assessment_criteria:
            for plan_criteria in plan_doc.assessment_criteria:
                criteria_name = plan_criteria.assessment_criteria
                criteria_max_score = plan_criteria.maximum_score
                
                if "Written Assessment" in criteria_name:
                    assessment_result.append("details", {
                        "assessment_criteria": criteria_name,
                        "maximum_score": criteria_max_score,
                        "score": total_score if criteria_max_score >= total_score else total_score
                    })
                    written_assessment_found = True
                    break
        
        if not written_assessment_found and plan_doc.assessment_criteria:
            first_criteria = plan_doc.assessment_criteria[0]
            assessment_result.append("details", {
                "assessment_criteria": first_criteria.assessment_criteria,
                "maximum_score": first_criteria.maximum_score,
                "score": total_score
            })
        
        if not plan_doc.assessment_criteria:
            error_msg = "Assessment Plan has no criteria. Cannot create Assessment Result."
            
            # Add error to Quiz Activity comments
            try:
                from frappe.desk.doctype.comment.comment import add_comment
                comment_text = f"❌ {error_msg}\n\nPlease add Assessment Criteria to the Assessment Plan '{assessment_plan}'."
                add_comment(
                    reference_doctype="Quiz Activity",
                    reference_name=quiz_activity_name,
                    content=comment_text,
                    comment_email=frappe.session.user or "system",
                    comment_by=frappe.session.user or "system"
                )
            except:
                pass
            
            return {
                "status": "error",
                "message": error_msg
            }
        
        # Set company
        company = frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
        if company and hasattr(assessment_result, 'custom_company'):
            assessment_result.custom_company = company
        
        # Insert Assessment Result
        frappe.logger().info(f"[ASSESSMENT RESULT] Inserting Assessment Result...")
        assessment_result.insert(ignore_permissions=True)
        frappe.db.commit()
        frappe.logger().info(f"[ASSESSMENT RESULT] ✓ Assessment Result created: {assessment_result.name}")
        
        # Submit Assessment Result
        try:
            frappe.logger().info(f"[ASSESSMENT RESULT] Submitting Assessment Result: {assessment_result.name}...")
            # Reload the document to ensure we have the latest version
            assessment_result = frappe.get_doc("Assessment Result", assessment_result.name)
            assessment_result.flags.ignore_permissions = True
            assessment_result.submit()
            frappe.db.commit()
            frappe.logger().info(f"[ASSESSMENT RESULT] ✓ Assessment Result submitted successfully: {assessment_result.name}")
        except Exception as submit_error:
            # Log error but don't fail - Assessment Result is still created in draft
            error_msg = f"Failed to submit Assessment Result {assessment_result.name}: {str(submit_error)}"
            frappe.log_error(f"{error_msg}\nTraceback: {frappe.get_traceback()}", "Assessment Result Submit Error")
            frappe.logger().warning(f"[ASSESSMENT RESULT] ⚠ {error_msg}. Assessment Result is in draft status.")
            
            # Add warning comment to Quiz Activity
            try:
                from frappe.desk.doctype.comment.comment import add_comment
                comment_text = f"⚠️ Assessment Result created but could not be submitted automatically:\n\n" \
                              f"Assessment Result: {assessment_result.name} (Draft)\n" \
                              f"Error: {str(submit_error)}\n\n" \
                              f"Please review and submit the Assessment Result manually."
                add_comment(
                    reference_doctype="Quiz Activity",
                    reference_name=quiz_activity_name,
                    content=comment_text,
                    comment_email=frappe.session.user or "system",
                    comment_by=frappe.session.user or "system"
                )
                frappe.db.commit()
            except Exception as comment_err:
                frappe.log_error(f"Failed to add warning comment: {str(comment_err)}", "Quiz Activity Comment Error")
        
        # Update Quiz Activity with Assessment Result link and other custom fields
        frappe.logger().info(f"[ASSESSMENT RESULT] Updating Quiz Activity with custom fields...")
        try:
            quiz_activity_doc = frappe.get_doc("Quiz Activity", quiz_activity_name)
            updated = False
            
            # Set custom_assesment_result (note: typo in field name - assesment not assessment)
            if hasattr(quiz_activity_doc, 'custom_assesment_result'):
                quiz_activity_doc.custom_assesment_result = assessment_result.name
                updated = True
                frappe.logger().info(f"[ASSESSMENT RESULT] Set custom_assesment_result field: {assessment_result.name}")
            # Also try custom_assessment_result (correct spelling) for backward compatibility
            elif hasattr(quiz_activity_doc, 'custom_assessment_result'):
                quiz_activity_doc.custom_assessment_result = assessment_result.name
                updated = True
                frappe.logger().info(f"[ASSESSMENT RESULT] Set custom_assessment_result field: {assessment_result.name}")
            # Try assessment_result field (if exists)
            elif hasattr(quiz_activity_doc, 'assessment_result'):
                quiz_activity_doc.assessment_result = assessment_result.name
                updated = True
                frappe.logger().info(f"[ASSESSMENT RESULT] Set assessment_result field: {assessment_result.name}")
            # If neither exists, try to add via db_set
            else:
                # Check if field exists in meta
                meta = frappe.get_meta("Quiz Activity")
                if meta.has_field("custom_assesment_result"):
                    quiz_activity_doc.db_set("custom_assesment_result", assessment_result.name, update_modified=False)
                    updated = True
                    frappe.logger().info(f"[ASSESSMENT RESULT] Set custom_assesment_result via db_set: {assessment_result.name}")
                elif meta.has_field("custom_assessment_result"):
                    quiz_activity_doc.db_set("custom_assessment_result", assessment_result.name, update_modified=False)
                    updated = True
                    frappe.logger().info(f"[ASSESSMENT RESULT] Set custom_assessment_result via db_set: {assessment_result.name}")
                elif meta.has_field("assessment_result"):
                    quiz_activity_doc.db_set("assessment_result", assessment_result.name, update_modified=False)
                    updated = True
                    frappe.logger().info(f"[ASSESSMENT RESULT] Set assessment_result via db_set: {assessment_result.name}")
                else:
                    frappe.logger().warning(f"[ASSESSMENT RESULT] No Assessment Result field found in Quiz Activity.")
            
            # Also ensure custom_assesment_plan is set
            if hasattr(quiz_activity_doc, 'custom_assesment_plan') and assessment_plan:
                quiz_activity_doc.custom_assesment_plan = assessment_plan
                updated = True
                frappe.logger().info(f"[ASSESSMENT RESULT] Set custom_assesment_plan: {assessment_plan}")
            
            # Also ensure custom_student_group is set
            if hasattr(quiz_activity_doc, 'custom_student_group') and student_group:
                quiz_activity_doc.custom_student_group = student_group
                updated = True
                frappe.logger().info(f"[ASSESSMENT RESULT] Set custom_student_group: {student_group}")
            
            # Save the Quiz Activity if we modified it
            if updated:
                quiz_activity_doc.save(ignore_permissions=True)
                frappe.db.commit()
                frappe.logger().info(f"[ASSESSMENT RESULT] ✓ Quiz Activity updated with all custom fields")
            
        except Exception as update_err:
            frappe.logger().error(f"[ASSESSMENT RESULT] Failed to update Quiz Activity with custom fields: {str(update_err)}")
            frappe.log_error(f"Failed to update Quiz Activity with custom fields: {str(update_err)}", "Update Quiz Activity Custom Fields")
        
        # Add success comment to Quiz Activity with clear details
        try:
            from frappe.desk.doctype.comment.comment import add_comment
            # Check if Assessment Result is submitted
            assessment_result_doc = frappe.get_doc("Assessment Result", assessment_result.name)
            status_text = "Submitted" if assessment_result_doc.docstatus == 1 else "Draft"
            comment_text = f"✅ Assessment Result created and {status_text.lower()} successfully!\n\n" \
                          f"Assessment Result: {assessment_result.name} ({status_text})\n" \
                          f"Student: {student}\n" \
                          f"Assessment Plan: {assessment_plan} (created for Student Group: {student_group})\n" \
                          f"Score: {total_score}/{total_marks}\n\n" \
                          f"Note: Assessment Plan is shared by all students in the Student Group. Assessment Result is specific to this Student."
            add_comment(
                reference_doctype="Quiz Activity",
                reference_name=quiz_activity_name,
                content=comment_text,
                comment_email=frappe.session.user or "system",
                comment_by=frappe.session.user or "system"
            )
            frappe.db.commit()  # Ensure comment is saved
        except Exception as comment_err:
            frappe.log_error(f"Failed to add success comment: {str(comment_err)}", "Quiz Activity Comment Error")
        
        return {
            "status": "success",
            "message": f"Assessment Result created successfully: {assessment_result.name}",
            "assessment_result_id": assessment_result.name
        }
        
    except Exception as e:
        error_msg = f"Error creating Assessment Result: {str(e)}"
        full_error = f"{error_msg}\n\nTraceback:\n{frappe.get_traceback()}"
        frappe.log_error(full_error, "Create Assessment Result from Quiz Activity")
        
        # Add error comment to Quiz Activity - ALWAYS add error to comments
        try:
            from frappe.desk.doctype.comment.comment import add_comment
            comment_text = f"❌ Failed to create Assessment Result:\n\n{error_msg}\n\nPlease check the error logs for more details or contact support."
            add_comment(
                reference_doctype="Quiz Activity",
                reference_name=quiz_activity_name,
                content=comment_text,
                comment_email=frappe.session.user or "system",
                comment_by=frappe.session.user or "system"
            )
        except Exception as comment_error:
            # If adding comment fails, log it but don't fail the whole operation
            frappe.log_error(f"Failed to add comment to Quiz Activity: {str(comment_error)}", "Create Assessment Result Comment Error")
        
        return {
            "status": "error",
            "message": error_msg
        }

def _get_linked_assessment_result_name(quiz_activity_doc):
    """Resolve linked Assessment Result from known link fields or by student+plan."""
    for fieldname in ("custom_assesment_result", "custom_assessment_result", "assessment_result"):
        value = getattr(quiz_activity_doc, fieldname, None)
        if value and frappe.db.exists("Assessment Result", value):
            return value

    assessment_plan = getattr(quiz_activity_doc, "custom_assesment_plan", None)
    student = getattr(quiz_activity_doc, "student", None)
    if assessment_plan and student:
        return frappe.db.exists("Assessment Result", {
            "student": student,
            "assessment_plan": assessment_plan,
            "docstatus": ["<", 2]
        })
    return None

def _is_admin_or_system_manager():
    roles = set(frappe.get_roles(frappe.session.user))
    return ("Administrator" in roles) or ("System Manager" in roles)

@frappe.whitelist()
def get_quiz_activity_answer_reference(quiz_activity_name):
    """Return question text and correct option(s) for each Quiz Activity row."""
    try:
        if not _is_admin_or_system_manager():
            frappe.throw(_("Only Administrator or System Manager can view answer reference."))

        if not quiz_activity_name:
            return {"status": "error", "message": "Quiz Activity is required"}

        quiz_activity_doc = frappe.get_doc("Quiz Activity", quiz_activity_name)
        reference = {}

        if not hasattr(quiz_activity_doc, "result") or not quiz_activity_doc.result:
            return {"status": "success", "reference": reference}

        question_names = list({row.question for row in quiz_activity_doc.result if row.question})
        for question_name in question_names:
            question_text = question_name
            correct_option = ""
            try:
                question_doc = frappe.get_doc("Question", question_name)
                question_text = getattr(question_doc, "question", None) or question_name

                if hasattr(question_doc, "options") and question_doc.options:
                    correct_options = [
                        (opt.option or "").strip()
                        for opt in question_doc.options
                        if getattr(opt, "is_correct", 0) and (opt.option or "").strip()
                    ]
                    correct_option = ", ".join(correct_options)
            except Exception:
                # Keep fallback values if a question is missing.
                pass

            reference[question_name] = {
                "question_text": question_text,
                "correct_option": correct_option
            }

        return {"status": "success", "reference": reference}
    except Exception as e:
        frappe.log_error(
            f"Failed get_quiz_activity_answer_reference: {str(e)}\nTraceback: {frappe.get_traceback()}",
            "Quiz Activity Answer Reference"
        )
        return {"status": "error", "message": str(e), "reference": {}}

@frappe.whitelist()
def admin_update_quiz_activity_answers(quiz_activity_name, updates, reason=None):
    """Allow Administrator/System Manager to correct Quiz Activity answers and resync score/result."""
    try:
        if not _is_admin_or_system_manager():
            frappe.throw(_("Only Administrator or System Manager can update quiz answers."))

        if not quiz_activity_name:
            return {"status": "error", "message": "Quiz Activity is required"}

        if isinstance(updates, str):
            updates = json.loads(updates or "[]")

        if not isinstance(updates, list) or not updates:
            return {"status": "error", "message": "No answer updates provided"}

        quiz_activity_doc = frappe.get_doc("Quiz Activity", quiz_activity_name)
        if not hasattr(quiz_activity_doc, "result") or not quiz_activity_doc.result:
            return {"status": "error", "message": "Quiz Activity has no answer rows to update"}

        updates_map = {
            str((row or {}).get("row_name")): (row or {})
            for row in updates
            if (row or {}).get("row_name")
        }

        if not updates_map:
            return {"status": "error", "message": "No valid rows selected for update"}

        original_score = quiz_activity_doc.score or "0/0"
        original_status = quiz_activity_doc.status or "Fail"
        total_questions = len(quiz_activity_doc.result)

        pending_row_updates = []
        for row in quiz_activity_doc.result:
            row_update = updates_map.get(str(row.name))
            if not row_update:
                # Keep existing value for score calculation.
                row.quiz_result = "Correct" if (row.quiz_result or "").strip().lower() == "correct" else "Wrong"
                continue

            selected_option = (row_update.get("selected_option") or "").strip()
            normalized_result = "Correct" if (row_update.get("quiz_result") or "").lower() == "correct" else "Wrong"
            current_selected = (row.selected_option or "").strip()
            current_result = "Correct" if (row.quiz_result or "").strip().lower() == "correct" else "Wrong"

            row.selected_option = selected_option
            row.quiz_result = normalized_result

            if selected_option != current_selected or normalized_result != current_result:
                pending_row_updates.append({
                    "doctype": getattr(row, "doctype", "Quiz Result"),
                    "name": row.name,
                    "selected_option": selected_option,
                    "quiz_result": normalized_result
                })

        correct_count = sum(
            1 for row in quiz_activity_doc.result
            if (row.quiz_result or "").strip().lower() == "correct"
        )

        quiz_doc = frappe.get_doc("Quiz", quiz_activity_doc.quiz) if quiz_activity_doc.quiz else None
        passing_percentage = (getattr(quiz_doc, "passing_score", None) or 75) if quiz_doc else 75
        percentage = (correct_count / total_questions * 100.0) if total_questions else 0
        status_value = "Pass" if percentage >= float(passing_percentage) else "Fail"
        score_value = f"{correct_count}/{total_questions}"

        for row_payload in pending_row_updates:
            frappe.db.set_value(
                row_payload["doctype"],
                row_payload["name"],
                {
                    "selected_option": row_payload["selected_option"],
                    "quiz_result": row_payload["quiz_result"]
                },
                update_modified=False
            )

        frappe.db.set_value(
            "Quiz Activity",
            quiz_activity_doc.name,
            {
                "score": score_value,
                "status": status_value
            },
            update_modified=False
        )
        frappe.db.commit()

        assessment_result_name = _get_linked_assessment_result_name(quiz_activity_doc)
        if assessment_result_name:
            assessment_result_doc = frappe.get_doc("Assessment Result", assessment_result_name)

            frappe.db.set_value(
                "Assessment Result",
                assessment_result_name,
                "total_score",
                correct_count,
                update_modified=False
            )

            details_rows = list(getattr(assessment_result_doc, "details", []) or [])
            target_row = None
            for detail in details_rows:
                if "Written Assessment" in (detail.assessment_criteria or ""):
                    target_row = detail
                    break
            if not target_row and details_rows:
                target_row = details_rows[0]
            if target_row:
                frappe.db.set_value(
                    target_row.doctype,
                    target_row.name,
                    "score",
                    correct_count,
                    update_modified=False
                )

            frappe.db.commit()

        reason_text = (reason or "").strip() or "No reason provided."
        comment_text = (
            f"🛠️ Admin answer correction applied.\n"
            f"Reason: {reason_text}\n"
            f"Score: {original_score} → {score_value}\n"
            f"Status: {original_status} → {status_value}"
        )
        quiz_activity_doc.add_comment("Comment", comment_text)

        if assessment_result_name:
            assessment_result_doc = frappe.get_doc("Assessment Result", assessment_result_name)
            assessment_result_doc.add_comment(
                "Comment",
                f"🛠️ Synced from Quiz Activity {quiz_activity_doc.name} after admin correction.\n"
                f"Reason: {reason_text}\n"
                f"Updated total score: {correct_count}"
            )

        frappe.db.commit()
        return {
            "status": "success",
            "message": "Quiz Activity and Assessment Result updated successfully",
            "quiz_activity": quiz_activity_doc.name,
            "assessment_result": assessment_result_name,
            "score": score_value,
            "status_value": status_value
        }
    except Exception as e:
        frappe.log_error(
            f"Failed admin_update_quiz_activity_answers: {str(e)}\nTraceback: {frappe.get_traceback()}",
            "Quiz Activity Admin Update"
        )
        return {
            "status": "error",
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True, methods=['GET'])
def get_quiz_submission_history(student, quiz_name=None, limit=5):
    """Fetch recent quiz submissions with answer history for a student."""
    try:
        if not student:
            return {
                "status": "error",
                "message": "Student is required"
            }

        try:
            limit = int(limit) if limit is not None else 5
        except (TypeError, ValueError):
            limit = 5
        limit = min(max(limit, 1), 50)

        filters = {"student": student}
        if quiz_name:
            filters["quiz"] = quiz_name

        activities = frappe.get_all(
            "Quiz Activity",
            filters=filters,
            fields=["name", "quiz", "score", "status", "activity_date", "creation"],
            order_by="activity_date desc, creation desc",
            limit=limit,
            ignore_permissions=True
        )

        history = []
        for activity in activities:
            answers = []
            try:
                activity_doc = frappe.get_doc("Quiz Activity", activity.name)
                if hasattr(activity_doc, "result") and activity_doc.result:
                    for row in activity_doc.result:
                        answers.append({
                            "question": row.question,
                            "selected_option": row.selected_option,
                            "quiz_result": row.quiz_result
                        })
            except Exception:
                answers = []

            history.append({
                "name": activity.name,
                "quiz": activity.quiz,
                "score": activity.score,
                "status": activity.status,
                "activity_date": activity.activity_date,
                "creation": activity.creation,
                "answers": answers
            })

        return {
            "status": "success",
            "history": history
        }
    except Exception as e:
        frappe.log_error(f"Error fetching quiz submission history: {str(e)}", "Quiz API")
        return {
            "status": "error",
            "message": f"Failed to fetch submission history: {str(e)}"
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
