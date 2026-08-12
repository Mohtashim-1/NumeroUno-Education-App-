import frappe

from numerouno.numerouno.api.certificate_verification import get_public_verification_url


def get_context(context):
	"""Redirect legacy ERP verification URLs to the public marketing site."""
	certificate_number = frappe.form_dict.get("cert") or frappe.form_dict.get("certNumber")
	student_name = frappe.form_dict.get("name")

	redirect_url = get_public_verification_url(certificate_number, student_name)
	frappe.local.flags.redirect_location = redirect_url
	raise frappe.Redirect
