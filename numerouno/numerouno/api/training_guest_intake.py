import imghdr

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate
from frappe.utils.file_manager import save_file

MAX_PHOTO_BYTES = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def submit_training_guest_intake():
	"""Public guest form: name, training date, company, photo."""
	participant_name = (frappe.form_dict.get("participant_name") or "").strip()
	company_name = (frappe.form_dict.get("company_name") or "").strip()
	training_date = frappe.form_dict.get("training_date")

	if not participant_name:
		frappe.throw(_("Name is required."))
	if not company_name:
		frappe.throw(_("Name of company is required."))
	if not training_date:
		frappe.throw(_("Date of training is required."))

	try:
		training_date = getdate(training_date)
	except Exception:
		frappe.throw(_("Date of training is not valid."))

	upload = _get_uploaded_photo()
	if not upload:
		frappe.throw(_("Please upload a photo."))

	filename, content = upload
	_validate_photo(filename, content)

	doc = frappe.new_doc("Training Guest Record")
	doc.participant_name = participant_name
	doc.company_name = company_name
	doc.training_date = training_date
	doc.flags.ignore_permissions = True
	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True)

	file_url = _attach_photo(doc, filename, content)

	frappe.db.commit()

	return {
		"status": "success",
		"name": doc.name,
		"message": _("Your details have been recorded successfully."),
	}


def _attach_photo(doc, filename, content):
	"""Save image file and set the Attach Image field on the parent document."""
	for file_name in frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": doc.doctype,
			"attached_to_name": doc.name,
			"attached_to_field": "photo",
		},
		pluck="name",
	):
		frappe.delete_doc("File", file_name, ignore_permissions=True, force=True)

	file_doc = save_file(
		filename,
		content,
		doc.doctype,
		doc.name,
		is_private=0,
		df="photo",
	)
	file_url = (file_doc.file_url or "").strip()
	if not file_url:
		frappe.throw(_("Could not save photo. Please try again."))

	# save_file links File row only; Attach Image field must be set on the parent doc.
	parent = frappe.get_doc(doc.doctype, doc.name)
	parent.photo = file_url
	parent.flags.ignore_permissions = True
	parent.save(ignore_permissions=True)

	return file_url


def _get_uploaded_photo():
	files = getattr(frappe.request, "files", None)
	if not files:
		return None

	upload = files.get("photo") or files.get("file")
	if not upload or not getattr(upload, "filename", None):
		return None

	content = upload.read()
	return upload.filename, content


def _validate_photo(filename, content):
	if not content:
		frappe.throw(_("Please upload a photo."))

	if len(content) > MAX_PHOTO_BYTES:
		frappe.throw(_("Photo must be smaller than {0} MB.").format(MAX_PHOTO_BYTES // (1024 * 1024)))

	ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
	if ext and ext not in ALLOWED_EXTENSIONS:
		frappe.throw(_("Photo must be JPG, PNG, WEBP, or GIF."))

	kind = imghdr.what(None, content)
	if ext == ".webp" and not kind:
		kind = "webp"
	if kind not in ("jpeg", "png", "gif", "webp"):
		frappe.throw(_("Uploaded file is not a valid image."))


@frappe.whitelist(allow_guest=True)
def get_training_guest_intake_context():
	return {
		"max_photo_mb": cint(MAX_PHOTO_BYTES / (1024 * 1024)),
		"today": nowdate(),
	}
