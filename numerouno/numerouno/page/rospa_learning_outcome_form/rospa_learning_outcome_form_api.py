import frappe

from numerouno.numerouno.page.rospa_learning_outcome_form.rospa_learning_outcome_form import (
	cancel_form,
	get_form_data,
	get_group_students,
	prepare_group,
	save_form_data,
	submit_form,
)


def _doc_for_template(data):
	doc = frappe._dict(data)
	doc.criteria = [frappe._dict(row) for row in doc.get("criteria") or []]
	return doc


def _render_form_html(doc_data):
	doc = _doc_for_template(doc_data)
	return frappe.render_template(
		"numerouno/numerouno/print_format/rospa_learning_outcome_assessment/rospa_learning_outcome_assessment.html",
		{"doc": doc},
	)


@frappe.whitelist()
def get_form_html(docname=None, student_group=None, student=None):
	doc_data = get_form_data(docname=docname, student_group=student_group, student=student)
	return {"doc": doc_data, "html": _render_form_html(doc_data)}


@frappe.whitelist()
def save_form(data):
	return save_form_data(data)


@frappe.whitelist()
def submit(docname):
	return submit_form(docname)


@frappe.whitelist()
def cancel(docname):
	return cancel_form(docname)


@frappe.whitelist()
def get_students(student_group):
	return get_group_students(student_group)


@frappe.whitelist()
def prepare(student_group, assessment_date=None):
	return prepare_group(student_group, assessment_date=assessment_date)
