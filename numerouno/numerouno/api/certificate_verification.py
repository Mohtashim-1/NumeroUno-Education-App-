import frappe
from frappe import _
from frappe.utils import getdate, add_days
import json

@frappe.whitelist(allow_guest=True)
def verify_certificate(certificate_number, student_name):
    """
    Verify a certificate by certificate number and student name
    """
    try:
        # Get certificate details
        certificate = frappe.get_doc("Assessment Result", certificate_number)
        
        # Check if certificate exists and is submitted
        if not certificate or certificate.docstatus != 1:
            return {
                "status": "error",
                "message": "Certificate not found or invalid"
            }
        
        # Verify student name matches (case insensitive)
        if not certificate.student_name or certificate.student_name.lower() != student_name.lower():
            return {
                "status": "error", 
                "message": "Student name does not match certificate"
            }
        
        # Check if certificate is eligible for verification (PASS grade)
        if certificate.grade != "PASS":
            return {
                "status": "error",
                "message": "Certificate is not valid (Grade: {})".format(certificate.grade)
            }
        
        # Calculate expiry information
        expiry_info = calculate_certificate_expiry(certificate)
        
        # Prepare certificate data for response
        certificate_data = {
            "name": certificate.name,
            "student_name": certificate.student_name,
            "course": certificate.course,
            "program": certificate.program,
            "total_score": certificate.total_score,
            "maximum_score": certificate.maximum_score,
            "grade": certificate.grade,
            "creation": certificate.creation,
            "certificate_validity_date": getattr(certificate, 'certificate_validity_date', None),
            "validity_period": getattr(certificate, 'validity_period', None),
            "course_start_date": getattr(certificate, 'course_start_date', None),
            **expiry_info
        }
        
        return {
            "status": "success",
            "message": "Certificate verified successfully",
            "certificate": certificate_data
        }
        
    except frappe.DoesNotExistError:
        return {
            "status": "error",
            "message": "Certificate not found"
        }
    except Exception as e:
        frappe.log_error(f"Certificate verification error: {str(e)}", "Certificate Verification")
        return {
            "status": "error",
            "message": "Error verifying certificate. Please try again."
        }

def calculate_certificate_expiry(certificate):
    """
    Calculate certificate expiry information using certificate_validity_date
    """
    try:
        # Use certificate_validity_date if available
        certificate_validity_date = getattr(certificate, 'certificate_validity_date', None)
        
        if certificate_validity_date:
            # Use the actual certificate validity date
            expiry_date = getdate(certificate_validity_date)
            current_date = getdate()
            
            is_expired = current_date > expiry_date
            days_until_expiry = (expiry_date - current_date).days
            
            # Certificate needs renewal if expired or within 30 days of expiry
            needs_renewal = is_expired or days_until_expiry <= 30
            
            return {
                "is_expired": is_expired,
                "expiry_date": expiry_date.strftime("%Y-%m-%d"),
                "days_until_expiry": days_until_expiry,
                "needs_renewal": needs_renewal
            }
        
        # Fallback to old calculation method if certificate_validity_date is not available
        validity_period = getattr(certificate, 'validity_period', None)
        course_start_date = getattr(certificate, 'course_start_date', None)
        
        if validity_period and validity_period != "NA" and course_start_date:
            # Calculate expiry date based on course start date
            expiry_date = add_days(course_start_date, int(validity_period))
            current_date = getdate()
            
            is_expired = current_date > expiry_date
            days_until_expiry = (expiry_date - current_date).days
            
            # Certificate needs renewal if expired or within 30 days of expiry
            needs_renewal = is_expired or days_until_expiry <= 30
            
            return {
                "is_expired": is_expired,
                "expiry_date": expiry_date.strftime("%Y-%m-%d"),
                "days_until_expiry": days_until_expiry,
                "needs_renewal": needs_renewal
            }
        
        return {
            "is_expired": False,
            "expiry_date": None,
            "days_until_expiry": None,
            "needs_renewal": False
        }
        
    except Exception as e:
        frappe.log_error(f"Error calculating certificate expiry: {str(e)}", "Certificate Verification")
        return {
            "is_expired": False,
            "expiry_date": None,
            "days_until_expiry": None,
            "needs_renewal": False
        }

@frappe.whitelist(allow_guest=True)
def get_certificate_by_qr(certificate_number):
    """
    Get certificate details by QR code (certificate number only)
    """
    try:
        # Get certificate details
        certificate = frappe.get_doc("Assessment Result", certificate_number)
        
        # Check if certificate exists and is submitted
        if not certificate or certificate.docstatus != 1:
            return {
                "status": "error",
                "message": "Certificate not found or invalid"
            }
        
        # Check if certificate is eligible for verification (PASS grade)
        if certificate.grade != "PASS":
            return {
                "status": "error",
                "message": "Certificate is not valid (Grade: {})".format(certificate.grade)
            }
        
        # Calculate expiry information
        expiry_info = calculate_certificate_expiry(certificate)
        
        # Prepare certificate data for response
        certificate_data = {
            "name": certificate.name,
            "student_name": certificate.student_name,
            "course": certificate.course,
            "program": certificate.program,
            "total_score": certificate.total_score,
            "maximum_score": certificate.maximum_score,
            "grade": certificate.grade,
            "creation": certificate.creation,
            "certificate_validity_date": getattr(certificate, 'certificate_validity_date', None),
            "validity_period": getattr(certificate, 'validity_period', None),
            "course_start_date": getattr(certificate, 'course_start_date', None),
            **expiry_info
        }
        
        return {
            "status": "success",
            "message": "Certificate found",
            "certificate": certificate_data
        }
        
    except frappe.DoesNotExistError:
        return {
            "status": "error",
            "message": "Certificate not found"
        }
    except Exception as e:
        frappe.log_error(f"Certificate QR lookup error: {str(e)}", "Certificate Verification")
        return {
            "status": "error",
            "message": "Error retrieving certificate. Please try again."
        }
