import json

import frappe


PUBLIC_FIELD_EXCLUSIONS = {
	"registration_status",
	"is_flagged",
	"review_notes",
	"full_name",
	"date_of_birth",
	"course_declaration_responses",
	"course_declaration_section",
}
COURSE_DERIVED_FIELDS = {
	"product_title",
	"joining_product_title",
	"joining_instructions_title",
	"joining_opito_code",
}

no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.show_sidebar = False
	context.title = "OPITO Learner Registration"
	context.form_schema = json.dumps(build_public_form_schema())
	return context


def build_public_form_schema():
	meta = frappe.get_meta("Registration")
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

		if df.fieldname in PUBLIC_FIELD_EXCLUSIONS or not current_section:
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
				"default": normalize_default(df.fieldname, df.default),
				"options": df.options or "",
				"depends_on": df.depends_on or "",
			}
		)

	return [section for section in sections if section.get("items")]


def normalize_default(fieldname, value):
	if fieldname in COURSE_DERIVED_FIELDS:
		return ""
	if value == "Today":
		return frappe.utils.nowdate()
	return value or ""


def cint(value):
	try:
		return int(value)
	except (TypeError, ValueError):
		return 0
