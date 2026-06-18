import frappe
from frappe.handler import upload_file as frappe_upload_file


def _clean(value):
	if value is None or not isinstance(value, str):
		return value
	return value.strip()


@frappe.whitelist(allow_guest=True)
def upload_file():
	"""Strip whitespace from upload params to avoid corrupted doctype names."""
	for key in ("doctype", "docname", "fieldname", "folder", "file_name", "file_url"):
		if frappe.form_dict.get(key):
			frappe.form_dict[key] = _clean(frappe.form_dict[key])

	return frappe_upload_file()
