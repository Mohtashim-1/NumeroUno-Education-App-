"""Install HABC1 Assessment Pack print format and workspace shortcuts."""

from __future__ import annotations

import json
from pathlib import Path

import frappe

MODULE = "Numerouno"
DOCTYPE = "HABC1 Assessment Pack"
PRINT_NAME = "HABC1 Assessment Pack"
WORKSPACE = "Forms"
HEADER = "First Aid"
SHORTCUT_LABEL = "First Aid"
LIST_LABEL = "First Aid List"
FORM_PAGE = "habc1-assessment-form"


def install():
	from frappe.modules.import_file import import_file_by_path

	base = Path(__file__).parent
	for rel in (
		"doctype/habc1_learner/habc1_learner.json",
		"doctype/habc1_referral/habc1_referral.json",
		"doctype/habc1_assessment_pack/habc1_assessment_pack.json",
		"page/habc1_assessment_form/habc1_assessment_form.json",
		"print_format/habc1_assessment_pack_form/habc1_assessment_pack_form.json",
	):
		import_file_by_path(str(base / rel), force=True, ignore_version=True)
	return setup()


def after_migrate():
	if not Path(__file__).parent.joinpath("doctype/habc1_assessment_pack/habc1_assessment_pack.json").exists():
		return
	try:
		install()
	except Exception:
		frappe.log_error(title="HABC1 setup after_migrate")


def setup():
	_ensure_print_format()
	_ensure_workspace()
	frappe.db.commit()
	return {"doctype": DOCTYPE, "print_format": PRINT_NAME, "workspace": WORKSPACE, "page": FORM_PAGE}


def _ensure_print_format():
	html_path = Path(__file__).parent / "print_format/habc1_assessment_pack/habc1_assessment_pack.html"
	css_path = Path(__file__).parent / "print_format/habc1_assessment_pack/habc1_assessment_pack.css"
	html = html_path.read_text() if html_path.exists() else ""
	css = css_path.read_text() if css_path.exists() else ""
	values = {
		"css": css,
		"html": html,
		"custom_format": 1,
		"print_format_type": "Jinja",
		"font_size": 10,
		"margin_top": 10,
		"margin_bottom": 10,
		"margin_left": 11,
		"margin_right": 11,
		"show_section_headings": 0,
		"page_number": "Hide",
		"align_labels_right": 0,
		"line_breaks": 0,
		"doc_type": DOCTYPE,
		"module": MODULE,
	}
	if frappe.db.exists("Print Format", PRINT_NAME):
		frappe.db.set_value("Print Format", PRINT_NAME, values, update_modified=True)
	else:
		doc = frappe.new_doc("Print Format")
		doc.name = PRINT_NAME
		doc.update(values)
		doc.standard = "Yes"
		doc.insert(ignore_permissions=True)
	if frappe.db.exists("DocType", DOCTYPE):
		frappe.db.set_value("DocType", DOCTYPE, "default_print_format", PRINT_NAME)


def _ensure_workspace():
	if not frappe.db.exists("Workspace", WORKSPACE):
		return
	if not frappe.db.exists("DocType", DOCTYPE):
		return

	workspace = frappe.get_doc("Workspace", WORKSPACE)
	existing_links = {row.link_to: row for row in workspace.shortcuts}
	if DOCTYPE in existing_links:
		existing_links[DOCTYPE].label = LIST_LABEL
	else:
		workspace.append(
			"shortcuts",
			{
				"type": "DocType",
				"link_to": DOCTYPE,
				"doc_view": "List",
				"label": LIST_LABEL,
				"color": "Blue",
			},
		)
	if FORM_PAGE in existing_links:
		existing_links[FORM_PAGE].label = SHORTCUT_LABEL
	elif frappe.db.exists("Page", FORM_PAGE):
		workspace.append(
			"shortcuts",
			{
				"type": "Page",
				"link_to": FORM_PAGE,
				"label": SHORTCUT_LABEL,
				"color": "Blue",
			},
		)

	content = json.loads(workspace.content or "[]")
	existing_shortcut_names = {
		block.get("data", {}).get("shortcut_name")
		for block in content
		if block.get("type") == "shortcut"
	}
	has_header = any(
		HEADER in (block.get("data", {}).get("text") or "")
		for block in content
		if block.get("type") == "header"
	)
	if not has_header:
		content.append(
			{
				"id": frappe.generate_hash(length=10),
				"type": "header",
				"data": {"text": f'<span class="h4">{HEADER}</span>', "col": 12},
			}
		)
	for label in (SHORTCUT_LABEL, LIST_LABEL):
		if label not in existing_shortcut_names:
			content.append(
				{
					"id": frappe.generate_hash(length=10),
					"type": "shortcut",
					"data": {"shortcut_name": label, "col": 4},
				}
			)
	workspace.content = json.dumps(content)
	workspace.save(ignore_permissions=True)
