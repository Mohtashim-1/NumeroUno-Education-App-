import frappe

from numerouno.numerouno.page.safety_briefing_form.safety_briefing_form import (
	get_form_data,
	save_form_data,
	submit_form,
)


def _doc_for_template(data):
	doc = frappe._dict(data)
	for table in ("discussion_points", "practical_items", "attendees", "instructors"):
		doc[table] = [frappe._dict(row) for row in doc.get(table) or []]
	return doc


def _render_form_html(doc_data):
	doc = _doc_for_template(doc_data)
	return frappe.render_template(
		"numerouno/numerouno/print_format/safety_briefing/safety_briefing.html",
		{"doc": doc},
	)


@frappe.whitelist()
def get_form_html(docname=None, briefing_type=None, student_group=None):
	doc_data = get_form_data(docname=docname, briefing_type=briefing_type, student_group=student_group)
	return {"doc": doc_data, "html": _render_form_html(doc_data)}


@frappe.whitelist()
def save_form(data):
	return save_form_data(data)


@frappe.whitelist()
def submit(docname):
	return submit_form(docname)
