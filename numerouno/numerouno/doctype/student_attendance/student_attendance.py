import frappe
from frappe import _

@frappe.whitelist()
def attendance_restriction(doc, method):
    if not doc.custom_student_signature:
        frappe.throw("""
            <div style="text-align:center; padding: 10px;">
                        <img src="https://cdn-icons-png.flaticon.com/512/463/463612.png" width="60" style="margin-bottom: 10px;" />
                        <h3 style="color:#d9534f;">Signature Missing</h3>
                        <p style="font-size:14px;">Please provide your signature in the <b>Signature</b> field before submitting the attendance.</p>
                    </div>
        """)