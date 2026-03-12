# Copyright (c) 2025, Numerouno and Contributors
# License: MIT. See LICENSE

import io
import frappe
from frappe import _
from frappe.utils import get_url

try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False


def get_context(context):
    """Generate QR code image and return as response"""
    context.no_cache = 1
    
    # Get data from query parameter
    data = frappe.form_dict.get('data') or frappe.request.args.get('data', '')
    size = int(frappe.form_dict.get('size', 120) or frappe.request.args.get('size', 120))
    box_size = int(frappe.form_dict.get('box_size', 10) or frappe.request.args.get('box_size', 10))
    border = int(frappe.form_dict.get('border', 4) or frappe.request.args.get('border', 4))
    
    if not data:
        frappe.throw(_("Data parameter is required"))
    
    if not QRCODE_AVAILABLE:
        frappe.throw(_("QR code library not installed. Please install qrcode[pil] package."))
    
    try:
        # Create QR code instance
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=box_size,
            border=border,
        )
        
        # Add data
        qr.add_data(data)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Resize if needed
        if size and size != 120:
            from PIL import Image
            img = img.resize((size, size), Image.Resampling.LANCZOS)
        
        # Convert to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_bytes = buffer.getvalue()
        
        # Return as image response
        frappe.response['type'] = 'binary'
        frappe.response['filename'] = 'qrcode.png'
        frappe.response['filecontent'] = img_bytes
        
    except Exception as e:
        frappe.log_error(f"QR Code generation error: {str(e)}", "QR Code Generation")
        frappe.throw(_("Error generating QR code: {0}").format(str(e)))

