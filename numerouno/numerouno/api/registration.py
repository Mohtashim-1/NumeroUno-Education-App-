from html import escape

import frappe


EXCLUDED_PUBLIC_FIELDS = {
	"registration_status",
	"is_flagged",
	"review_notes",
	"full_name",
	"date_of_birth",
	"course_declaration_responses",
}
LAYOUT_FIELD_TYPES = {"Section Break", "Column Break", "HTML"}


@frappe.whitelist(allow_guest=True)
def get_opito_courses():
	courses = frappe.get_all(
		"Course",
		filters={"is_opito": 1},
		fields=["name", "course_name", "course_code", "custom_learning_outcome"],
		order_by="course_name asc",
	)
	return {
		"status": "success",
		"courses": [
			{
				"value": row.name,
				"label": row.course_name or row.name,
				"product_title": (
					f"{row.course_name} ({row.course_code})"
					if row.course_name and row.course_code
					else (row.course_name or row.name)
				),
				"joining_product_title": (
					f"{row.course_name} ({row.course_code})"
					if row.course_name and row.course_code
					else (row.course_name or row.name)
				),
				"joining_instructions_title": (
					f"Course Joining Instructions - {row.course_name}"
					if row.course_name
					else "Course Joining Instructions"
				),
				"joining_opito_code": (
					f"{row.course_name} OPITO Code ({row.course_code})"
					if row.course_name and row.course_code
					else (row.course_name or row.name)
				),
				"custom_learning_outcome": row.custom_learning_outcome or "",
				"learning_outcomes_html": build_learning_outcomes_html(row.custom_learning_outcome),
			}
			for row in courses
		],
	}


@frappe.whitelist(allow_guest=True)
def get_course_declaration_template(course_name):
	if not course_name:
		return {"status": "success", "template": None}

	template_name = frappe.db.get_value(
		"Course Declaration Template",
		{"course": course_name, "is_active": 1},
		"name",
	)
	if not template_name:
		return {"status": "success", "template": None}

	template = frappe.get_doc("Course Declaration Template", template_name)
	return {
		"status": "success",
		"template": {
			"name": template.name,
			"course": template.course,
			"course_name": template.course_name,
			"declaration_notes": template.declaration_notes,
			"highlight_observation_note": template.highlight_observation_note,
			"declarations": [
				{
					"parameter_code": row.parameter_code,
					"declaration_text": row.declaration_text,
					"is_mandatory": cint_like(row.is_mandatory),
					"is_highlighted": cint_like(row.is_highlighted),
				}
				for row in template.declarations
			],
		},
	}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def submit_registration(payload=None):
	try:
		data = frappe.parse_json(payload) if payload else frappe.form_dict
		if not isinstance(data, dict):
			return {"status": "error", "message": "Invalid registration payload."}

		meta = frappe.get_meta("Registration")
		field_map = {
			df.fieldname: df
			for df in meta.fields
			if df.fieldname and df.fieldtype not in LAYOUT_FIELD_TYPES and df.fieldname not in EXCLUDED_PUBLIC_FIELDS
		}

		doc_data = {"doctype": "Registration"}
		for fieldname, df in field_map.items():
			if fieldname not in data:
				continue

			value = data.get(fieldname)
			if df.fieldtype == "Check":
				doc_data[fieldname] = 1 if cint_like(value) else 0
			else:
				doc_data[fieldname] = value

		doc_data["registration_status"] = "Pending"
		doc_data["is_flagged"] = 0
		doc_data["review_notes"] = None

		doc = frappe.get_doc(doc_data)
		apply_course_declaration_responses(doc, data.get("course_declaration_responses"))
		doc.insert(ignore_permissions=True)
		frappe.db.commit()

		return {
			"status": "success",
			"name": doc.name,
			"message": "Registration submitted successfully.",
		}
	except frappe.ValidationError as exc:
		return {
			"status": "error",
			"message": str(exc) or "Please review the required registration fields and declarations.",
		}
	except Exception as exc:
		frappe.log_error(frappe.get_traceback(), "Public Registration Submission")
		return {
			"status": "error",
			"message": str(exc) or "Unable to submit registration right now.",
		}


def cint_like(value):
	if isinstance(value, bool):
		return int(value)
	if isinstance(value, (int, float)):
		return int(value)
	if isinstance(value, str):
		return value.strip().lower() in {"1", "true", "yes", "on"}
	return 0


def apply_course_declaration_responses(doc, responses):
	if not doc.course_name:
		return

	template_name = frappe.db.get_value(
		"Course Declaration Template",
		{"course": doc.course_name, "is_active": 1},
		"name",
	)
	if not template_name:
		return

	template = frappe.get_doc("Course Declaration Template", template_name)
	response_map = {}
	for row in frappe.parse_json(responses) or []:
		key = (row.get("parameter_code") or "").strip()
		if key:
			response_map[key] = {
				"response": (row.get("response") or "").strip(),
				"details_if_yes": (row.get("details_if_yes") or "").strip(),
			}

	for item in template.declarations:
		key = (item.parameter_code or "").strip()
		response_row = response_map.get(key, {})
		response = (response_row.get("response") or "").strip()
		details_if_yes = (response_row.get("details_if_yes") or "").strip()

		if cint_like(item.is_mandatory) and response not in {"Yes", "No"}:
			frappe.throw(f"Please select Yes or No for: {item.declaration_text}")
		if response == "Yes" and not details_if_yes:
			frappe.throw(f"Please complete 'If Yes, What and When' for: {item.declaration_text}")

		doc.append(
			"course_declaration_responses",
			{
				"parameter_code": item.parameter_code,
				"declaration_text": item.declaration_text,
				"response": response,
				"details_if_yes": details_if_yes,
				"is_highlighted": cint_like(item.is_highlighted),
			},
		)


def build_learning_outcomes_html(value):
	content = (value or "").strip()
	if not content:
		return ""

	formatted_content = "<br>".join(escape(line) for line in content.splitlines())
	return (
		'<div style="padding: 14px 16px; background: #fcfcfd; border: 1px solid #eaecf0; '
		'border-radius: 8px; font-size: 12px; line-height: 1.7; color: #475467;">'
		"<strong>Learning Outcomes</strong><br>"
		f"{formatted_content}"
		"</div>"
	)
