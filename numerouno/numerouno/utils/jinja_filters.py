"""
Jinja filters for Numerouno app
"""
import frappe
from numerouno.api import generate_qr_code
from numerouno.numerouno.utils.pdf_to_img import pdf_to_base64_image


def qr_code(data, size=120, box_size=10, border=4):
    """
    Jinja filter to generate QR code as base64 data URI
    
    Usage in templates:
    {{ doc.name | qr_code }}
    {{ doc.name | qr_code(150) }}
    {{ verify_url | qr_code(150, 12, 2) }}
    
    Args:
        data: The data to encode in QR code
        size: Output image size in pixels (default: 120)
        box_size: Size of each box in pixels (default: 10)
        border: Border thickness in boxes (default: 4)
    
    Returns:
        Base64 encoded data URI of the QR code image
    """
    try:
        return generate_qr_code(data, size, box_size, border)
    except Exception as e:
        frappe.log_error(f"QR Code filter error: {str(e)}", "QR Code Filter")
        return ""


def pdf_to_image(file_url):
    """Convert a PDF file URL into a base64 PNG for print-friendly rendering."""
    try:
        return pdf_to_base64_image(file_url) or ""
    except Exception as e:
        frappe.log_error(f"PDF image filter error: {str(e)}", "PDF Image Filter")
        return ""
