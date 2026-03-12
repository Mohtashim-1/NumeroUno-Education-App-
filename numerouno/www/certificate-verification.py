import frappe
from frappe import _

def get_context(context):
    """
    Get context for the certificate verification page
    """
    context.title = "Certificate Verification"
    context.no_cache = 1
    
    # Get certificate number and student name from URL parameters
    certificate_number = frappe.form_dict.get('cert')
    student_name = frappe.form_dict.get('name')
    
    context.certificate_number = certificate_number
    context.student_name = student_name
    
    # If certificate number is provided, try to get certificate details
    if certificate_number:
        try:
            from numerouno.numerouno.api.certificate_verification import get_certificate_by_qr, verify_certificate
            
            # If student name is also provided, use full verification
            if student_name:
                result = verify_certificate(certificate_number, student_name)
            else:
                # Use QR verification (certificate number only)
                result = get_certificate_by_qr(certificate_number)
            
            if result.get('status') == 'success':
                context.certificate = result.get('certificate')
                context.verification_success = True
            else:
                context.verification_error = result.get('message', 'Certificate not found')
                context.verification_success = False
        except Exception as e:
            context.verification_error = "Error loading certificate details"
            context.verification_success = False
    else:
        context.verification_success = False
