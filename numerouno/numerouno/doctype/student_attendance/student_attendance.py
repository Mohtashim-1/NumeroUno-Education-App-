import frappe
import os
import base64
from frappe.utils import today, getdate
from frappe import _
from education.education.doctype.student_attendance.student_attendance import StudentAttendance

class StudentAttendance(StudentAttendance):
    """Custom Student Attendance class that overrides the standard validation"""
    
    def validate_date(self):
        """Override the standard validate_date to allow future dates"""
        
        # We're removing the future date restriction
        # Original code was: if not self.leave_application and getdate(self.date) > getdate():
        #                       frappe.throw(_("Attendance cannot be marked for future dates."))
        
        # Keep the academic year validation but remove future date restriction
        if self.student_group:
            academic_year = frappe.db.get_value(
                "Student Group", self.student_group, "academic_year"
            )
            if academic_year:
                year_start_date, year_end_date = frappe.db.get_value(
                    "Academic Year", academic_year, ["year_start_date", "year_end_date"]
                )
                if year_start_date and year_end_date:
                    if not (getdate(year_start_date) <= getdate(self.date) <= getdate(year_end_date)):
                        frappe.throw(
                            _("Attendance date {0} is not within the Academic Year {1}").format(
                                self.date, academic_year
                            )
                        )

# @frappe.whitelist()
# def attendance_restriction(doc, method):
#     if not doc.custom_student_signature:
#         frappe.throw("""
#             <div style="text-align:center; padding: 10px;">
#                         <img src="https://cdn-icons-png.flaticon.com/512/463/463612.png" width="60" style="margin-bottom: 10px;" />
#                         <h3 style="color:#d9534f;">Signature Missing</h3>
#                         <p style="font-size:14px;">Please provide your signature in the <b>Signature</b> field before submitting the attendance.</p>
#                     </div>
#         """)
        


@frappe.whitelist()
def get_challenge():
    """
    This method generates a WebAuthn challenge and stores it in the session.
    """
    # print(f"\n\n\nprint\n\n\n\n\n")
    # Generate a random challenge (32 bytes)
    challenge = os.urandom(32)
    
    # Store the challenge in session to verify it later during authentication
    frappe.local.session['auth_challenge'] = base64.b64encode(challenge).decode()
    
    # Return the challenge as a base64 string
    return base64.b64encode(challenge).decode()

# @frappe.whitelist(allow_guest=True)
# def register_fingerprint(credential_data):
#     print(f"\n\n\nprint1111\n\n\n\n\n")
#     try:
#         # Decode the incoming JSON data from the frontend
#         credential = frappe.parse_json(credential_data)
        
#         # Extract necessary data from the credential
#         credential_id = credential['id']
#         public_key = base64.b64encode(credential['response']['attestationObject']).decode('utf-8')

#         # Log the received data for debugging purposes
#         frappe.logger().info("Received Credential ID: {}".format(credential_id))
#         frappe.logger().info("Received Public Key: {}".format(public_key))

#         # Search for the student by user ID (or any other unique identifier)
#         # Use 'student_id' or 'user_id' to find the right student record
#         student = frappe.get_doc("Student", "EDU-STU-2025-00012")  # Example, update with dynamic student fetching logic

#         if student:
#             # Log before updating the student record
#             frappe.logger().info("Student Found: {}".format(student.name))

#             # Update the student record with the credential information
#             student.custom_credential_id = credential_id
#             student.custom_public_key = public_key  # Store the public key as base64

#             # Save the student document after update
#             student.save()

#             # Log the success of the operation
#             frappe.logger().info("Successfully saved fingerprint data for student: {}".format(student.name))

#             # Send the encoded credential ID back to the frontend (for local storage)
#             encoded_credential_id = base64.b64encode(credential_id.encode('utf-8')).decode('utf-8')
#             return {"message": "Fingerprint registered successfully.", "credential_id": encoded_credential_id}
#         else:
#             # If student is not found, log and return error
#             frappe.logger().error("Student not found with the given ID.")
#             return {"message": "Student not found."}
#     except Exception as e:
#         # If any error occurs, log the exception for debugging
#         frappe.logger().error("Error in fingerprint registration: {}".format(str(e)))
#         return {"message": "An error occurred during fingerprint registration."}

@frappe.whitelist(allow_guest=True)
def register_fingerprint(credential_data):
    # If Frappe passed us a JSON‐string, parse it; otherwise assume it's already a dict
    if isinstance(credential_data, str):
        cred = frappe.parse_json(credential_data)
    else:
        cred = credential_data

    # Now we can safely do .get()
    credential_id = cred.get('id')
    public_key_b64 = cred.get('response', {}).get('attestationObject')

    if not credential_id or not public_key_b64:
        frappe.throw("Invalid credential data")

    # Find your student (use real logic here!)
    student = frappe.get_doc("Student", "EDU-STU-2025-00012")

    student.custom_credential_id = credential_id
    student.custom_public_key    = public_key_b64
    student.save()

    # Return the base64-encoded credential_id for localStorage
    encoded = base64.b64encode(credential_id.encode()).decode()
    return {
        "message":       "Fingerprint registered successfully.",
        "credential_id": encoded
    }
@frappe.whitelist(allow_guest=True)
def mark_attendance(credential_data):
    """
    Marks the attendance for the student by verifying the fingerprint via WebAuthn.
    """
    
    # Decode the WebAuthn assertion response
    credential = frappe.parse_json(credential_data)
    
    # Get the credential ID from the response
    credential_id = credential['id']
    
    # Retrieve the stored credential from the database
    student = frappe.get_doc("Student", {"custom_credential_id": credential_id})
    
    if student:
        # Create an attendance record for the student
        attendance = frappe.get_doc({
            "doctype": "Student Attendance",
            "student": student.name,
            "student_name": student.student_name,
            "attendance_date": today(),
            "status": "Present"
        })
        attendance.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return {"message": f"Attendance marked for {student.student_name}"}
    else:
        return {"message": "Student not found or invalid fingerprint."}