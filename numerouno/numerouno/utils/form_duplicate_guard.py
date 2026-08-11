import frappe
from frappe import _


FORM_ROUTE = {
	"Safety Briefing": "/app/safety-briefing-form/{name}",
	"Assessor Checklist": "/app/course-assessor-checklist-form/{name}",
}


def find_existing_course_form(doctype, student_group, form_type_field, form_type, exclude_name=None):
	"""Return existing draft/submitted form for a student group + type, if any."""
	student_group = (student_group or "").strip()
	form_type = (form_type or "").strip()
	exclude_name = (exclude_name or "").strip()

	if not student_group or not form_type:
		return None

	filters = {
		"student_group": student_group,
		form_type_field: form_type,
		"docstatus": ["<", 2],
	}
	if exclude_name:
		filters["name"] = ["!=", exclude_name]

	return frappe.db.get_value(
		doctype,
		filters,
		["name", "docstatus"],
		as_dict=True,
		order_by="modified desc",
	)


def get_form_open_url(doctype, name):
	template = FORM_ROUTE.get(doctype)
	if not template:
		return frappe.utils.get_url(f"/app/{frappe.scrub(doctype)}/{name}")
	return frappe.utils.get_url(template.format(name=name))


def build_duplicate_form_message(doctype, existing):
	name = existing.get("name")
	status = _("Submitted") if frappe.utils.cint(existing.get("docstatus")) == 1 else _("Draft")
	url = get_form_open_url(doctype, name)
	label = _("Safety Briefing") if doctype == "Safety Briefing" else _("Course Assessor Checklist")
	return _(
		"A {0} already exists for this student group ({1} — {2}). "
		'<a href="{3}"><b>Open {1}</b></a>'
	).format(label, name, status, url)


def throw_if_duplicate_course_form(
	doctype,
	student_group,
	form_type_field,
	form_type,
	exclude_name=None,
):
	existing = find_existing_course_form(
		doctype, student_group, form_type_field, form_type, exclude_name=exclude_name
	)
	if not existing:
		return None

	title = (
		_("Safety Briefing Already Exists")
		if doctype == "Safety Briefing"
		else _("Assessor Checklist Already Exists")
	)
	frappe.throw(
		build_duplicate_form_message(doctype, existing),
		title=title,
		exc=frappe.DuplicateEntryError,
	)
	return existing


def check_existing_course_form_payload(form_kind, student_group, form_type):
	"""Whitelisted helper payload for portal / form pickers."""
	form_kind = (form_kind or "").strip().lower()
	student_group = (student_group or "").strip()
	form_type = (form_type or "").strip()

	if form_kind == "safety_briefing":
		doctype = "Safety Briefing"
		type_field = "briefing_type"
	elif form_kind in ("assessor_checklist", "course_assessor_checklist"):
		doctype = "Assessor Checklist"
		type_field = "checklist_type"
	else:
		frappe.throw(_("Unknown form kind: {0}").format(form_kind))

	existing = find_existing_course_form(doctype, student_group, type_field, form_type)
	if not existing:
		return {"exists": False}

	return {
		"exists": True,
		"name": existing.name,
		"docstatus": existing.docstatus,
		"url": get_form_open_url(doctype, existing.name),
		"message": build_duplicate_form_message(doctype, existing),
	}


@frappe.whitelist()
def check_existing_course_form(form_kind, student_group, form_type):
	return check_existing_course_form_payload(form_kind, student_group, form_type)
