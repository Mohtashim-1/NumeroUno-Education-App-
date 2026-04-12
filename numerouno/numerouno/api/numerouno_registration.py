import frappe
from frappe.utils import formatdate, nowdate


EXCLUDED_PUBLIC_FIELDS = {"amended_from", "naming_series"}
LAYOUT_FIELD_TYPES = {"Section Break", "Column Break", "HTML"}
SUPPORT_EMAIL = "training@nutc.ae"
SUPPORT_PHONE = "+971 2 557 5220"


@frappe.whitelist(allow_guest=True, methods=["POST"])
def submit_numerouno_registration(payload=None):
	try:
		data = frappe.parse_json(payload) if payload else frappe.form_dict
		if not isinstance(data, dict):
			return {"status": "error", "message": "Invalid registration payload."}

		meta = frappe.get_meta("NumeroUno Registration")
		field_map = {
			df.fieldname: df
			for df in meta.fields
			if df.fieldname and df.fieldtype not in LAYOUT_FIELD_TYPES and df.fieldname not in EXCLUDED_PUBLIC_FIELDS
		}

		doc_data = {"doctype": "NumeroUno Registration"}
		for fieldname in field_map:
			value = data.get(fieldname)
			if value in (None, ""):
				continue
			doc_data[fieldname] = value

		doc = frappe.get_doc(doc_data)
		doc.insert(ignore_permissions=True)
		frappe.db.commit()
		send_acknowledgement_email(doc)

		return {
			"status": "success",
			"name": doc.name,
			"message": "Registration submitted successfully.",
		}
	except frappe.ValidationError as exc:
		return {
			"status": "error",
			"message": str(exc) or "Please review the required fields and try again.",
		}
	except Exception as exc:
		frappe.log_error(frappe.get_traceback(), "NumeroUno Public Registration Submission")
		return {
			"status": "error",
			"message": str(exc) or "Unable to submit registration right now.",
		}


def send_acknowledgement_email(doc):
	recipient = (doc.get("email") or "").strip()
	if not recipient:
		return

	candidate_name = doc.get("full_name") or "Candidate"
	submission_date = formatdate(doc.creation or nowdate())
	subject = f"Numero Uno Registration Acknowledgement - {doc.name}"
	message = f"""
<p>Dear {frappe.utils.escape_html(candidate_name)},</p>

<p>Thank you for registering for Numero Uno through our portal.</p>
<p>We have successfully received your application. This email serves as a formal acknowledgement of your registration.</p>

<p><strong>Your Registration Details:</strong></p>
<ul>
	<li><strong>Reference Number:</strong> {frappe.utils.escape_html(doc.name)}</li>
	<li><strong>Date of Submission:</strong> {frappe.utils.escape_html(submission_date)}</li>
	<li><strong>Status:</strong> Received/Under Review</li>
</ul>

<p><strong>What happens next?</strong></p>
<p>Our team will review the information you provided. If your profile meets the requirements or if further documentation is needed, one of our coordinators will reach out to you via this email address or your provided phone number.</p>
<p>In the meantime, we recommend keeping your Reference Number handy for any future inquiries regarding your application.</p>
<p>If you have any urgent questions, please feel free to reply to this email or contact our support team at {frappe.utils.escape_html(SUPPORT_EMAIL)} / {frappe.utils.escape_html(SUPPORT_PHONE)}.</p>

<p>Best regards,</p>
<p><strong>Numero Uno Registrations</strong></p>
"""

	try:
		frappe.sendmail(
			recipients=[recipient],
			subject=subject,
			message=message,
			reply_to=SUPPORT_EMAIL,
			now=True,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), f"NumeroUno Registration Acknowledgement Email: {doc.name}")


@frappe.whitelist(allow_guest=True)
def get_numerouno_registration_schema():
	return build_public_form_schema()


@frappe.whitelist(allow_guest=True)
def get_course_options():
	return frappe.get_all("Course", fields=["name"], order_by="name asc")


@frappe.whitelist(allow_guest=True)
def get_link_options(doctype):
	allowed_doctypes = {"Course", "Country"}
	if doctype not in allowed_doctypes:
		frappe.throw("Unsupported Link options request.")

	return frappe.get_all(doctype, fields=["name"], order_by="name asc")



def build_public_form_schema():
	meta = frappe.get_meta("NumeroUno Registration")
	sections = []
	current_section = None

	for df in meta.fields:
		if df.fieldtype == "Section Break":
			current_section = {
				"fieldname": df.fieldname,
				"label": df.label or "",
				"items": [],
			}
			sections.append(current_section)
			continue

		if df.fieldname in EXCLUDED_PUBLIC_FIELDS or not current_section:
			continue

		if df.fieldtype == "Column Break":
			continue

		current_section["items"].append(
			{
				"fieldname": df.fieldname,
				"label": df.label or "",
				"fieldtype": df.fieldtype,
				"reqd": cint(df.reqd),
				"read_only": cint(df.read_only),
				"default": normalize_default(df.default),
				"options": df.options or "",
			}
		)

	return sections



def normalize_default(value):
	if value == "Today":
		return frappe.utils.nowdate()
	return value or ""



def cint(value):
	try:
		return int(value)
	except (TypeError, ValueError):
		return 0
