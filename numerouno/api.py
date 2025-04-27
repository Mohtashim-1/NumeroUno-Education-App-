import os
import base64
import frappe
from frappe.utils import today

@frappe.whitelist()
def get_challenge():
    """
    This method generates a WebAuthn challenge and stores it in the session.
    """
    # Generate a random challenge (32 bytes)
    challenge = os.urandom(32)
    
    # Store the challenge in session to verify it later during authentication
    frappe.local.session['auth_challenge'] = base64.b64encode(challenge).decode()
    
    # Return the challenge as a base64 string
    return base64.b64encode(challenge).decode()


@frappe.whitelist(allow_guest=True)
def register_fingerprint(credential_data):
    """
    Registers the user's fingerprint by saving the credential ID and public key in the Student Doctype.
    """
    # Decode and parse the WebAuthn response
    credential = frappe.parse_json(credential_data)
    
    # Extract the credential ID and public key
    credential_id = credential['id']
    public_key = credential['response']['attestationObject']  # This is the WebAuthn public key
    frappe.errprint('a')
    # Find the student by user ID (you can use `student_id` or `user_id`)
    student = frappe.get_doc("Student", {"user_id": credential['user']['id']})
    frappe.errprint('a')
    if student:
        # Store the WebAuthn credential ID and public key for future verification
        student.update({
            "custom_credential_id": credential_id,
            "custom_public_key": public_key  # You can store this as base64 encoded for easier use
        })
        student.save()
        frappe.errprint('a')
        
        # Send the base64-encoded credential_id to the frontend
        encoded_credential_id = base64.b64encode(credential_id.encode('utf-8')).decode('utf-8')
        
        return {"message": "Fingerprint registered successfully.", "credential_id": encoded_credential_id}
    else:
        return {"message": "Student not found during registration."}



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
    student = frappe.get_doc("Student", {"credential_id": credential_id})
    
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
