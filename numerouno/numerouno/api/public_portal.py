# Copyright (c) 2026, mohtashim and contributors
# For license information, please see license.txt

import frappe
from frappe.model.meta import get_meta

LAYOUT_FIELD_TYPES = frozenset(
	{"Section Break", "Column Break", "Tab Break", "Fold", "Heading"}
)

SUBMITTABLE_FIELD_TYPES = frozenset(
	{
		"Data",
		"Date",
		"Datetime",
		"Time",
		"Link",
		"Small Text",
		"Text",
		"Text Editor",
		"Select",
		"Check",
		"Int",
		"Float",
		"Currency",
		"Percent",
		"Duration",
		"Signature",
		"Long Text",
		"Rating",
	}
)

SKIPPED_FIELD_NAMES = frozenset({"amended_from", "naming_series"})


def _portal_form_allowed(reference_doctype: str) -> bool:
	return bool(
		frappe.db.exists(
			"Public Portal Form",
			{"reference_doctype": reference_doctype, "is_active": 1},
		)
	)


def _field_supported(df) -> bool:
	if df.fieldtype in LAYOUT_FIELD_TYPES:
		return False
	if df.fieldtype == "HTML":
		return True
	if df.fieldtype not in SUBMITTABLE_FIELD_TYPES:
		return False
	if df.hidden:
		return False
	return True


@frappe.whitelist(allow_guest=True)
def get_public_portal_form_list():
	"""Forms enabled for the public hub page."""
	rows = frappe.get_all(
		"Public Portal Form",
		filters={"is_active": 1},
		fields=["name", "form_label", "reference_doctype", "sort_order"],
		order_by="sort_order asc, form_label asc",
	)
	return rows


@frappe.whitelist(allow_guest=True)
def search_public_portal_link(
	reference_doctype: str | None = None,
	fieldname: str | None = None,
	txt: str | None = None,
	page_length: int = 20,
):
	"""Typeahead options for Link fields on active public portal forms (guest-safe)."""
	if not reference_doctype or not fieldname:
		frappe.throw(frappe._("Invalid request."))
	if not _portal_form_allowed(reference_doctype):
		frappe.throw(frappe._("This form is not available on the public portal."))

	meta = get_meta(reference_doctype)
	df = meta.get_field(fieldname)
	if not df or df.fieldtype != "Link":
		frappe.throw(frappe._("Not a link field."))

	link_doctype = (df.options or "").strip()
	if not link_doctype or not frappe.db.exists("DocType", link_doctype):
		frappe.throw(frappe._("Invalid link target."))

	txt = (txt or "").strip()[:120]
	page_length = max(1, min(cint(page_length) or 20, 50))

	link_meta = get_meta(link_doctype)
	title_field = link_meta.get_title_field()
	fields: list = ["name"]
	if title_field and title_field != "name" and link_meta.has_field(title_field):
		fields.append(title_field)

	if txt:
		or_filters = [["name", "like", f"%{txt}%"]]
		if title_field and title_field != "name" and link_meta.has_field(title_field):
			or_filters.append([title_field, "like", f"%{txt}%"])
		rows = frappe.get_all(
			link_doctype,
			or_filters=or_filters,
			fields=fields,
			limit_page_length=page_length,
			order_by="name asc",
			ignore_permissions=True,
		)
	else:
		rows = frappe.get_all(
			link_doctype,
			fields=fields,
			limit_page_length=page_length,
			order_by="modified desc",
			ignore_permissions=True,
		)

	out = []
	for row in rows:
		name = row.get("name")
		if not name:
			continue
		if title_field and title_field != "name" and row.get(title_field) is not None:
			label = str(row.get(title_field)).strip() or name
		else:
			label = name
		out.append({"value": name, "label": label})
	return out


@frappe.whitelist(allow_guest=True)
def get_public_portal_form_schema(reference_doctype: str | None = None):
	if not reference_doctype:
		frappe.throw(frappe._("Choose a form first."))
	if not _portal_form_allowed(reference_doctype):
		frappe.throw(frappe._("This form is not available on the public portal."))
	return build_public_form_schema(reference_doctype)


def build_public_form_schema(reference_doctype: str):
	meta = get_meta(reference_doctype)
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

		if not current_section:
			# Fields listed before the first Section Break are otherwise skipped.
			current_section = {
				"fieldname": "_public_portal_header",
				"label": "",
				"items": [],
			}
			sections.append(current_section)

		if df.fieldtype == "Column Break":
			continue

		if df.fieldname in SKIPPED_FIELD_NAMES:
			continue

		if not _field_supported(df):
			continue

		current_section["items"].append(
			{
				"fieldname": df.fieldname,
				"label": df.label or "",
				"fieldtype": df.fieldtype,
				"reqd": cint(df.reqd),
				"read_only": cint(df.read_only),
				"default": normalize_default(df),
				"options": df.options or "",
				# Desk often uses Data + default "Today" for dates; portal needs a calendar for those too.
				"use_date_picker": cint(df.fieldtype == "Data" and (df.default or "").strip() == "Today"),
			}
		)

	return [s for s in sections if s.get("items")]


def normalize_default(df):
	v = df.default
	if v == "Today":
		return frappe.utils.nowdate()
	if df.fieldtype == "Time" and (v or "").strip() == "Now":
		t = frappe.utils.nowtime()
		if isinstance(t, str) and "." in t:
			t = t.split(".")[0]
		return t or ""
	return v or ""


def cint(value):
	try:
		return int(value)
	except (TypeError, ValueError):
		return 0


def _assignable_field(df) -> bool:
	if df.read_only:
		return False
	if df.fieldtype not in SUBMITTABLE_FIELD_TYPES:
		return False
	if df.hidden:
		return False
	return True


@frappe.whitelist(allow_guest=True, methods=["POST"])
def submit_public_portal_form(payload=None):
	try:
		data = frappe.parse_json(payload) if payload else frappe.form_dict
		if not isinstance(data, dict):
			return {"status": "error", "message": "Invalid payload."}

		reference_doctype = (data.pop("reference_doctype", None) or "").strip()
		if not reference_doctype:
			return {"status": "error", "message": "Missing reference_doctype."}

		if not _portal_form_allowed(reference_doctype):
			return {"status": "error", "message": "This form is not available on the public portal."}

		meta = get_meta(reference_doctype)
		assignable = {
			df.fieldname: df
			for df in meta.fields
			if df.fieldname and _assignable_field(df)
		}

		doc_data: dict = {"doctype": reference_doctype}
		for fieldname, df in assignable.items():
			if fieldname not in data:
				continue
			value = data.get(fieldname)
			if value in (None, ""):
				continue
			doc_data[fieldname] = value

		doc = frappe.get_doc(doc_data)
		doc.insert(ignore_permissions=True)
		frappe.db.commit()

		return {
			"status": "success",
			"name": doc.name,
			"message": frappe._("Saved successfully."),
		}
	except frappe.ValidationError as exc:
		return {"status": "error", "message": str(exc) or frappe._("Validation failed.")}
	except Exception as exc:
		frappe.log_error(frappe.get_traceback(), "Public Portal Form Submit")
		return {
			"status": "error",
			"message": str(exc) or frappe._("Unable to save right now."),
		}
