"""Setup ROSPA Learning Outcome Assessment print format and workspace shortcuts."""

from __future__ import annotations

import json
from pathlib import Path

import frappe

MODULE = "Numerouno"
DOCTYPE = "ROSPA Learning Outcome Assessment"
PRINT_NAME = "ROSPA Learning Outcome Assessment Form"
WORKSPACE = "Forms"
HEADER = "ROSPA"
SHORTCUT_LABEL = "ROSPA Learning Outcome Assessment"
FORM_PAGE = "rospa-learning-outcome-form"


def _load_template():
	path = Path(__file__).parent / "doctype/rospa_learning_outcome_assessment/rospa_learning_outcome_assessment_template.json"
	return json.loads(path.read_text())


@frappe.whitelist()
def get_template_rows():
	template = _load_template()
	rows = []
	for idx, row in enumerate(template.get("criteria") or [], start=1):
		rows.append(
			{
				"sr_no": idx,
				"criterion_no": row.get("criterion_no") or "",
				"outcome": row.get("outcome") or "",
				"criterion": row.get("criterion") or "",
				"result": "",
				"comments": "",
			}
		)
	return {
		"form_title": template.get("form_title"),
		"form_subtitle": template.get("form_subtitle"),
		"criteria": rows,
	}


def install():
	from frappe.modules.import_file import import_file_by_path

	base = Path(__file__).parent
	for rel in (
		"doctype/rospa_learning_outcome_criterion/rospa_learning_outcome_criterion.json",
		"doctype/rospa_learning_outcome_assessment/rospa_learning_outcome_assessment.json",
		"page/rospa_learning_outcome_form/rospa_learning_outcome_form.json",
		"print_format/rospa_learning_outcome_assessment_form/rospa_learning_outcome_assessment_form.json",
	):
		import_file_by_path(str(base / rel), force=True, ignore_version=True)
	return setup()


def setup():
	_ensure_print_format()
	_ensure_workspace()
	frappe.db.commit()
	return {"doctype": DOCTYPE, "print_format": PRINT_NAME, "workspace": WORKSPACE}


def _ensure_print_format():
	html_path = Path(__file__).parent / "print_format/rospa_learning_outcome_assessment/rospa_learning_outcome_assessment.html"
	css_path = Path(__file__).parent / "print_format/rospa_learning_outcome_assessment/rospa_learning_outcome_assessment.css"
	html = html_path.read_text() if html_path.exists() else _default_print_html()
	css = css_path.read_text() if css_path.exists() else _default_print_css()

	if frappe.db.exists("Print Format", PRINT_NAME):
		frappe.db.set_value(
			"Print Format",
			PRINT_NAME,
			{
				"css": css,
				"html": html,
				"custom_format": 1,
				"print_format_type": "Jinja",
				"font_size": 9,
				"margin_top": 8,
				"margin_bottom": 8,
				"margin_left": 10,
				"margin_right": 10,
				"show_section_headings": 0,
				"page_number": "Hide",
				"align_labels_right": 0,
				"line_breaks": 0,
			},
			update_modified=True,
		)
		if frappe.db.exists("DocType", DOCTYPE):
			frappe.db.set_value("DocType", DOCTYPE, "default_print_format", PRINT_NAME)
		frappe.db.commit()
		return

	doc = frappe.new_doc("Print Format")
	doc.name = PRINT_NAME
	doc.doc_type = DOCTYPE
	doc.module = MODULE
	doc.standard = "Yes"
	doc.custom_format = 1
	doc.print_format_type = "Jinja"
	doc.font_size = 9
	doc.margin_top = 8
	doc.margin_bottom = 8
	doc.margin_left = 10
	doc.margin_right = 10
	doc.css = css
	doc.html = html
	doc.insert(ignore_permissions=True)


def _ensure_workspace():
	if not frappe.db.exists("Workspace", WORKSPACE):
		return
	if not frappe.db.exists("DocType", DOCTYPE):
		return

	workspace = frappe.get_doc("Workspace", WORKSPACE)
	existing_links = {row.link_to for row in workspace.shortcuts}
	if DOCTYPE not in existing_links:
		workspace.append(
			"shortcuts",
			{
				"type": "DocType",
				"link_to": DOCTYPE,
				"doc_view": "List",
				"label": SHORTCUT_LABEL,
				"color": "Blue",
			},
		)

	if FORM_PAGE not in existing_links and frappe.db.exists("Page", FORM_PAGE):
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
	if SHORTCUT_LABEL not in existing_shortcut_names:
		content.append(
			{
				"id": frappe.generate_hash(length=10),
				"type": "shortcut",
				"data": {"shortcut_name": SHORTCUT_LABEL, "col": 3},
			}
		)
	workspace.content = json.dumps(content)
	workspace.save(ignore_permissions=True)


def _default_print_css():
	return """
.lv-form { font-family: Arial, Helvetica, sans-serif; font-size: 9pt; color: #000; }
.lv-title { text-align: center; font-weight: 700; font-size: 12pt; margin-bottom: 4px; }
.lv-subtitle { text-align: center; margin-bottom: 10px; }
.lv-meta { width: 100%; border-collapse: collapse; margin-bottom: 10px; }
.lv-meta td { border: 1px solid #000; padding: 4px 6px; }
.lv-grid { width: 100%; border-collapse: collapse; margin-bottom: 10px; }
.lv-grid th, .lv-grid td { border: 1px solid #000; padding: 3px 4px; vertical-align: top; }
.lv-grid th { background: #eee; font-weight: 700; text-align: center; }
.lv-check { text-align: center; width: 28px; }
.lv-section { font-weight: 700; background: #f5f5f5; }
.lv-guidance { border: 1px solid #000; padding: 6px; margin: 8px 0; font-size: 8.5pt; white-space: pre-wrap; }
.lv-footer { width: 100%; border-collapse: collapse; margin-top: 10px; }
.lv-footer td { border: 1px solid #000; padding: 4px 6px; vertical-align: top; }
""".strip()


def _default_print_html():
	return """
<div class="lv-form">
  <div class="lv-title">{{ doc.form_title or "Learning Outcome Assessment Record – Defensive Driving for Light Vehicle" }}</div>
  <div class="lv-subtitle">{{ doc.form_subtitle or "Level 2 Defensive Driving for Light Vehicles | Learning Outcome Assessment Record_Feb26" }}</div>

  <table class="lv-meta">
    <tr>
      <td><b>Candidate Name</b><br>{{ doc.candidate_name or "" }}</td>
      <td><b>Date</b><br>{{ frappe.utils.formatdate(doc.assessment_date) if doc.assessment_date else "" }}</td>
    </tr>
    <tr>
      <td><b>Employing company</b><br>{{ doc.employing_company or "" }}</td>
      <td><b>Mobile number</b><br>{{ doc.mobile_number or "" }}</td>
    </tr>
  </table>

  <table class="lv-grid">
    <thead>
      <tr>
        <th style="width:4%">No.</th>
        <th style="width:18%">Outcomes</th>
        <th style="width:58%">Criteria</th>
        <th style="width:8%">Achieved</th>
        <th style="width:12%">Source of Evidence</th>
      </tr>
    </thead>
    <tbody>
      {% set ns = namespace(last_section="") %}
      {% for row in doc.criteria %}
        {% if row.section and row.section != ns.last_section %}
          {% set ns.last_section = row.section %}
          <tr class="lv-section"><td colspan="5">{{ row.section }}</td></tr>
        {% endif %}
        <tr>
          <td class="lv-check">{{ row.sr_no or loop.index }}</td>
          <td>{{ row.outcome or "" }}</td>
          <td>{{ row.criterion or "" }}</td>
          <td class="lv-check">{{ "☑" if row.achieved else "☐" }}</td>
          <td class="lv-check">{{ row.source_of_evidence or "" }}</td>
        </tr>
      {% endfor %}
    </tbody>
  </table>

  <div class="lv-guidance">
    <b>Assessment Guidance</b><br>
    This outcome specifies the standard of competence required by the driver, through a number of practical outcomes specified in Outcome 1 of Unit 5. Learners must successfully complete all practical exercises to achieve this Unit.
    Records of methods used, and assessment results must be maintained.
  </div>
  <p><b>Remarks:</b> {{ doc.remarks or "" }}</p>
  <p><small>Source of Evidence: O – Observation  S – Simulation  Q – Questioning  W – Witness</small></p>

  <table class="lv-footer">
    <tr>
      <td><b>Learner Name:</b> {{ doc.candidate_name or "" }}</td>
      <td><b>Company:</b> {{ doc.employing_company or "" }}</td>
    </tr>
    <tr>
      <td colspan="2"><b>Training and Development Needs:</b><br>{{ doc.training_development_needs or "" }}</td>
    </tr>
    <tr>
      <td colspan="2">
        <b>Declaration:</b> The person named was assessed by me against the standards of performance specified in this document and in accordance with the assessment guidance.<br><br>
        I consider that the above person {% if doc.achievement_status == "Has achieved" %}<b>has</b>{% else %}<b>has not</b>{% endif %} achieved a sufficient level of understanding of the Off-Road Vehicle Professional Driving Theory course.<br>
        {% if doc.requires_further_training %}I consider that the above person requires further training and development in addition to that which is installation specific.{% endif %}
      </td>
    </tr>
    <tr>
      <td><b>Assessor's Name</b><br>{{ doc.assessor_name or "" }}</td>
      <td><b>Date</b><br>{{ frappe.utils.formatdate(doc.assessor_date) if doc.assessor_date else "" }}</td>
    </tr>
  </table>
</div>
""".strip()
