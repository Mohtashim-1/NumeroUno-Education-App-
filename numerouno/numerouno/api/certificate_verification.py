import frappe
from frappe.utils import add_days, getdate

@frappe.whitelist(allow_guest=True)
def verify_certificate(certificate_number, student_name):
    """
    Verify an assessment result or driving card by number and student name
    """
    try:
        doctype, document = get_verifiable_document(certificate_number)
        validate_document_name_match(doctype, document, student_name)
        certificate_data = build_verification_data(doctype, document)

        return {
            "status": "success",
            "message": "Document verified successfully",
            "certificate": certificate_data
        }
    except frappe.DoesNotExistError:
        return {
            "status": "error",
            "message": "Document not found"
        }
    except frappe.ValidationError as e:
        return {
            "status": "error",
            "message": str(e)
        }
    except Exception as e:
        frappe.log_error(f"Certificate verification error: {str(e)}", "Certificate Verification")
        return {
            "status": "error",
            "message": "Error verifying document. Please try again."
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
    Get assessment result or driving card details by QR code
    """
    try:
        doctype, document = get_verifiable_document(certificate_number)
        certificate_data = build_verification_data(doctype, document)

        return {
            "status": "success",
            "message": "Document found",
            "certificate": certificate_data
        }
    except frappe.DoesNotExistError:
        return {
            "status": "error",
            "message": "Document not found"
        }
    except frappe.ValidationError as e:
        return {
            "status": "error",
            "message": str(e)
        }
    except Exception as e:
        frappe.log_error(f"Certificate QR lookup error: {str(e)}", "Certificate Verification")
        return {
            "status": "error",
            "message": "Error retrieving document. Please try again."
        }


def get_verifiable_document(document_number):
    document_number = (document_number or "").strip()

    if not document_number:
        frappe.throw("Please enter a certificate or driving card number")

    if frappe.db.exists("Assessment Result", document_number):
        document = frappe.get_doc("Assessment Result", document_number)
        if document.docstatus != 1:
            frappe.throw("Certificate not found or invalid")
        if document.grade != "PASS":
            frappe.throw(f"Certificate is not valid (Grade: {document.grade})")
        return "Assessment Result", document

    if frappe.db.exists("Driving Card", document_number):
        document = frappe.get_doc("Driving Card", document_number)
        if document.docstatus != 1:
            frappe.throw("Driving card not found or invalid")
        return "Driving Card", document

    raise frappe.DoesNotExistError


def validate_document_name_match(doctype, document, student_name):
    expected_names = get_document_name_candidates(doctype, document)
    entered_name = (student_name or "").strip().lower()

    if not entered_name:
        frappe.throw("Student name is required")

    if not expected_names or entered_name not in expected_names:
        if doctype == "Driving Card":
            frappe.throw("Student name does not match driving card")
        frappe.throw("Student name does not match certificate")


def get_document_name_candidates(doctype, document):
    names = set()

    if doctype == "Assessment Result":
        if document.student_name:
            names.add(document.student_name.strip().lower())
        return names

    if doctype == "Driving Card" and document.student:
        student_values = frappe.db.get_value(
            "Student",
            document.student,
            ["student_name", "first_name"],
            as_dict=True,
        ) or {}

        for fieldname in ("student_name", "first_name"):
            value = student_values.get(fieldname)
            if value:
                names.add(value.strip().lower())

    return names


def build_verification_data(doctype, document):
    if doctype == "Driving Card":
        return build_driving_card_data(document)

    return build_assessment_result_data(document)


def build_assessment_result_data(certificate):
    expiry_info = calculate_certificate_expiry(certificate)

    return {
        "name": certificate.name,
        "document_type": "Assessment Result",
        "student_name": certificate.student_name,
        "course": certificate.course,
        "program": certificate.program,
        "total_score": certificate.total_score,
        "maximum_score": certificate.maximum_score,
        "grade": certificate.grade,
        "creation": certificate.creation,
        "certificate_validity_date": getattr(certificate, "certificate_validity_date", None),
        "validity_period": getattr(certificate, "validity_period", None),
        "course_start_date": getattr(certificate, "course_start_date", None),
        **expiry_info,
    }


def build_driving_card_data(card):
    expiry_info = calculate_driving_card_expiry(card)
    student_values = {}

    if card.student:
        student_values = frappe.db.get_value(
            "Student",
            card.student,
            ["student_name", "first_name", "employee_id", "customer_name"],
            as_dict=True,
        ) or {}

    student_name = (
        student_values.get("student_name")
        or student_values.get("first_name")
        or card.student
    )

    employee_id = card.employee_id or student_values.get("employee_id")
    company = card.company or student_values.get("customer_name")

    return {
        "name": card.name,
        "document_type": "Driving Card",
        "student_name": student_name,
        "employee_id": employee_id,
        "company": company,
        "vehicle_type": card.vehicle_type,
        "issue_date": card.issue_date,
        "expiry_date": card.expiry_date,
        "certificate_validity_date": card.expiry_date,
        "creation": card.creation,
        **expiry_info,
    }


def calculate_driving_card_expiry(card):
    try:
        if not getattr(card, "expiry_date", None):
            return {
                "is_expired": False,
                "expiry_date": None,
                "days_until_expiry": None,
                "needs_renewal": False,
            }

        expiry_date = getdate(card.expiry_date)
        current_date = getdate()

        is_expired = current_date > expiry_date
        days_until_expiry = (expiry_date - current_date).days
        needs_renewal = is_expired or days_until_expiry <= 30

        return {
            "is_expired": is_expired,
            "expiry_date": expiry_date.strftime("%Y-%m-%d"),
            "days_until_expiry": days_until_expiry,
            "needs_renewal": needs_renewal,
        }
    except Exception as e:
        frappe.log_error(f"Error calculating driving card expiry: {str(e)}", "Certificate Verification")
        return {
            "is_expired": False,
            "expiry_date": None,
            "days_until_expiry": None,
            "needs_renewal": False,
        }
