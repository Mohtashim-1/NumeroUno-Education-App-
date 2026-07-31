# Copyright (c) 2026, NumeroUNO and contributors
# License: MIT

"""ADNOC DDC Instructor Development Course forms.

Creates structured ERPNext entry forms and matching paper-style print formats for:
- Candidate Pre-Requisite Checklist (SLTIC-IDC-PRCL)
- Micro Teaching Assessment Checklist (SLTIC-IDC-MTCL)
- Examination Answer Sheet / OMR (SLTIC-IDC-OMR)
"""

from __future__ import annotations

import json

import frappe

MODULE = "Numerouno"

MICRO = "DDC Micro Teaching Assessment"
MICRO_ROW = "DDC Micro Teaching Criterion"
PREREQ = "DDC Candidate Prerequisite"
PREREQ_ROW = "DDC Prerequisite Item"
OMR = "DDC OMR Answer Sheet"
OMR_ROW = "DDC OMR Answer"

MICRO_PRINT = "DDC Micro Teaching Assessment Checklist"
PREREQ_PRINT = "DDC Candidate Pre-Requisite Checklist"
OMR_PRINT = "DDC Instructor Course OMR Answer Sheet"
CLIENT_SCRIPT = "NUTC DDC Instructor Course"

MICRO_CRITERIA = [
	"Learning objectives clearly stated",
	"Content accuracy and relevance",
	"Logical structure and organisation",
	"Effective introduction and conclusion",
	"Subject knowledge demonstrated",
	"Use of training aids / visual materials",
	"Communication clarity (voice, pace, language)",
	"Engagement with learners",
	"Questioning techniques used effectively",
	"Time management",
	"Handling of questions confidently",
	"Professional appearance and behavior",
	"Health & Safety considerations addressed (if applicable)",
]

ELIGIBILITY_REQUIREMENTS = [
	"Hold a valid Work Permit under nominated organization",
	"Valid UAE Driving License (License No.)",
	"Driving License Issue Date",
	"Minimum 5 Years UAE Driving Experience (Years of Experience)",
	"Minimum 5 Years Teaching/Training Experience (Years of Experience)",
	"Recognized Train the Trainer Certification (Certificate No.)",
	"TTT Certificate Issue Date",
	"English Language Proficiency",
	"Off-Road Driving Experience (Years of Experience)",
	"Valid ADSD Card (Card No.)",
	"Medical Fitness Certificate / Declaration (Medical Fitness No.)",
	"Medical Certificate Issue Date",
]

VEHICLE_REQUIREMENTS = [
	"Vehicle is 4x4 and Off-Road Capable (Vehicle Make/Model)",
	"Vehicle complies with UAE Traffic Regulations (Registration No.)",
	"Vehicle Modified as per ADNOC Requirements",
	"Vehicle Registered under Nominated Organization",
	"Equipped with Complete Desert Survival Kit",
]


def _permissions():
	full = {
		"read": 1,
		"write": 1,
		"create": 1,
		"delete": 1,
		"submit": 1,
		"cancel": 1,
		"amend": 1,
		"report": 1,
		"print": 1,
		"email": 1,
		"share": 1,
	}
	entry = {
		"read": 1,
		"write": 1,
		"create": 1,
		"submit": 1,
		"report": 1,
		"print": 1,
		"email": 1,
	}
	return [
		{"role": "System Manager", **full},
		{"role": "Quality Manager", **full},
		{"role": "Instructor", **entry},
		{"role": "Trainer", **entry},
	]


def _create_doctype(spec):
	if frappe.db.exists("DocType", spec["name"]):
		return False
	frappe.get_doc({"doctype": "DocType", "custom": 1, "module": MODULE, **spec}).insert(
		ignore_permissions=True
	)
	return True


def _candidate_fields():
	return [
		{"fieldname": "candidate_section", "label": "Candidate Information", "fieldtype": "Section Break"},
		{
			"fieldname": "candidate_name",
			"label": "Candidate Name",
			"fieldtype": "Data",
			"reqd": 1,
			"in_list_view": 1,
			"in_standard_filter": 1,
		},
		{"fieldname": "employee_id", "label": "Employee ID", "fieldtype": "Data"},
		{"fieldname": "department_organization", "label": "Department / Organization", "fieldtype": "Data"},
		{"fieldname": "candidate_column", "fieldtype": "Column Break"},
		{
			"fieldname": "assessment_date",
			"label": "Date of Assessment",
			"fieldtype": "Date",
			"reqd": 1,
			"in_list_view": 1,
		},
		{"fieldname": "account_number", "label": "Contact Number", "fieldtype": "Data"},
		{"fieldname": "adnoc_card_number", "label": "ADSD Card Number", "fieldtype": "Data"},
		{"fieldname": "email_address", "label": "Email Address", "fieldtype": "Data", "options": "Email"},
	]


def _assessor_fields():
	return [
		{"fieldname": "assessor_section", "label": "Assessor", "fieldtype": "Section Break"},
		{
			"fieldname": "assessor",
			"label": "Assessor",
			"fieldtype": "Link",
			"options": "Employee",
			"in_standard_filter": 1,
		},
		{
			"fieldname": "assessor_name",
			"label": "Assessor Name",
			"fieldtype": "Data",
			"fetch_from": "assessor.employee_name",
			"fetch_if_empty": 1,
		},
	]


def create_child_doctypes():
	created = []
	if _create_doctype(
		{
			"name": MICRO_ROW,
			"istable": 1,
			"editable_grid": 1,
			"fields": [
				{
					"fieldname": "criterion",
					"label": "Criteria",
					"fieldtype": "Data",
					"reqd": 1,
					"read_only": 1,
					"in_list_view": 1,
					"columns": 5,
				},
				{
					"fieldname": "rating",
					"label": "Assessment",
					"fieldtype": "Select",
					"options": "\nCompetent\nNeeds Improvement",
					"in_list_view": 1,
					"columns": 2,
				},
				{
					"fieldname": "comments",
					"label": "Comments",
					"fieldtype": "Small Text",
					"in_list_view": 1,
					"columns": 4,
				},
			],
		}
	):
		created.append(MICRO_ROW)

	if _create_doctype(
		{
			"name": PREREQ_ROW,
			"istable": 1,
			"editable_grid": 1,
			"fields": [
				{
					"fieldname": "requirement",
					"label": "Requirement",
					"fieldtype": "Small Text",
					"reqd": 1,
					"read_only": 1,
					"in_list_view": 1,
					"columns": 5,
				},
				{
					"fieldname": "details",
					"label": "Candidate Details",
					"fieldtype": "Small Text",
					"in_list_view": 1,
					"columns": 3,
				},
				{
					"fieldname": "result",
					"label": "Yes / No",
					"fieldtype": "Select",
					"options": "\nYes\nNo\nN/A",
					"in_list_view": 1,
					"columns": 1,
				},
				{
					"fieldname": "verified_by",
					"label": "Verified By Assessor",
					"fieldtype": "Data",
					"in_list_view": 1,
					"columns": 2,
				},
			],
		}
	):
		created.append(PREREQ_ROW)

	if _create_doctype(
		{
			"name": OMR_ROW,
			"istable": 1,
			"editable_grid": 1,
			"fields": [
				{
					"fieldname": "question_number",
					"label": "Question",
					"fieldtype": "Int",
					"reqd": 1,
					"read_only": 1,
					"in_list_view": 1,
					"columns": 2,
				},
				{
					"fieldname": "answer",
					"label": "Answer",
					"fieldtype": "Select",
					"options": "\nA\nB\nC\nD",
					"in_list_view": 1,
					"columns": 3,
				},
			],
		}
	):
		created.append(OMR_ROW)
	return created


def create_micro_doctype():
	fields = _candidate_fields() + _assessor_fields()
	fields += [
		{"fieldname": "criteria_section", "label": "Assessment Criteria", "fieldtype": "Section Break"},
		{
			"fieldname": "criteria",
			"label": "Assessment Criteria",
			"fieldtype": "Table",
			"options": MICRO_ROW,
			"reqd": 1,
		},
		{"fieldname": "overall_section", "label": "Overall Assessment", "fieldtype": "Section Break"},
		{
			"fieldname": "overall_result",
			"label": "Overall Result",
			"fieldtype": "Select",
			"options": "\nCompetent\nNot Yet Competent",
			"reqd": 1,
			"in_list_view": 1,
		},
		{"fieldname": "general_feedback", "label": "General Feedback", "fieldtype": "Text Editor"},
		{"fieldname": "signature_section", "label": "Assessor Signature & Date", "fieldtype": "Section Break"},
		{"fieldname": "assessor_signature", "label": "Assessor Signature", "fieldtype": "Signature"},
		{"fieldname": "signature_column", "fieldtype": "Column Break"},
		{"fieldname": "signature_date", "label": "Date", "fieldtype": "Date"},
	]
	return _create_doctype(
		{
			"name": MICRO,
			"is_submittable": 1,
			"autoname": "naming_series:",
			"naming_rule": 'By "Naming Series" field',
			"track_changes": 1,
			"search_fields": "candidate_name,employee_id,assessor_name",
			"sort_field": "assessment_date",
			"sort_order": "DESC",
			"fields": [
				{
					"fieldname": "naming_series",
					"label": "Series",
					"fieldtype": "Select",
					"options": "DDC-MT-.YYYY.-",
					"default": "DDC-MT-.YYYY.-",
					"reqd": 1,
				},
				*fields,
			],
			"permissions": _permissions(),
		}
	)


def create_prereq_doctype():
	fields = _candidate_fields()
	fields += [
		{"fieldname": "license_number", "label": "Driving License Number", "fieldtype": "Data"},
		{"fieldname": "section_1", "label": "Section 1 - Candidate Eligibility Requirements", "fieldtype": "Section Break"},
		{
			"fieldname": "eligibility_requirements",
			"label": "Candidate Eligibility Requirements",
			"fieldtype": "Table",
			"options": PREREQ_ROW,
			"reqd": 1,
		},
		{"fieldname": "section_2", "label": "Section 2 - Vehicle Pre-Requisites", "fieldtype": "Section Break"},
		{
			"fieldname": "vehicle_requirements",
			"label": "Vehicle Pre-Requisites",
			"fieldtype": "Table",
			"options": PREREQ_ROW,
			"reqd": 1,
		},
		{"fieldname": "declaration_section", "label": "Declaration", "fieldtype": "Section Break"},
		{
			"fieldname": "declaration_accepted",
			"label": "Candidate confirms the declaration",
			"fieldtype": "Check",
			"reqd": 1,
		},
		{"fieldname": "candidate_signature", "label": "Candidate Signature", "fieldtype": "Signature"},
		{"fieldname": "declaration_column", "fieldtype": "Column Break"},
		{"fieldname": "declaration_date", "label": "Date", "fieldtype": "Date"},
		{"fieldname": "provider_section", "label": "To be completed by the TTT Training Provider", "fieldtype": "Section Break"},
		{"fieldname": "assessor_comments", "label": "Assessor Comments", "fieldtype": "Text Editor"},
		{
			"fieldname": "provider_assessor",
			"label": "Assessor",
			"fieldtype": "Link",
			"options": "Employee",
		},
		{
			"fieldname": "provider_assessor_name",
			"label": "Name",
			"fieldtype": "Data",
			"fetch_from": "provider_assessor.employee_name",
			"fetch_if_empty": 1,
		},
		{"fieldname": "provider_signature", "label": "Signature", "fieldtype": "Signature"},
		{"fieldname": "provider_column", "fieldtype": "Column Break"},
		{"fieldname": "provider_date", "label": "Date", "fieldtype": "Date"},
	]
	return _create_doctype(
		{
			"name": PREREQ,
			"is_submittable": 1,
			"autoname": "naming_series:",
			"naming_rule": 'By "Naming Series" field',
			"track_changes": 1,
			"search_fields": "candidate_name,employee_id,department_organization",
			"sort_field": "assessment_date",
			"sort_order": "DESC",
			"fields": [
				{
					"fieldname": "naming_series",
					"label": "Series",
					"fieldtype": "Select",
					"options": "DDC-PR-.YYYY.-",
					"default": "DDC-PR-.YYYY.-",
					"reqd": 1,
				},
				*fields,
			],
			"permissions": _permissions(),
		}
	)


def create_omr_doctype():
	fields = _candidate_fields() + _assessor_fields()
	fields += [
		{"fieldname": "questionnaire_code", "label": "Questionnaire Code", "fieldtype": "Data", "reqd": 1},
		{"fieldname": "answers_section", "label": "Answers (Questions 1-100)", "fieldtype": "Section Break"},
		{
			"fieldname": "answers",
			"label": "Answer Sheet",
			"fieldtype": "Table",
			"options": OMR_ROW,
			"reqd": 1,
		},
		{"fieldname": "summary_section", "label": "Assessment Summary", "fieldtype": "Section Break"},
		{
			"fieldname": "assessment_summary",
			"label": "Assessment Summary",
			"fieldtype": "Select",
			"options": "\nPass\nRefer",
			"in_list_view": 1,
		},
		{"fieldname": "learner_signature", "label": "Learner Signature", "fieldtype": "Signature"},
		{"fieldname": "summary_column", "fieldtype": "Column Break"},
		{"fieldname": "signed_date", "label": "Date", "fieldtype": "Date"},
	]
	return _create_doctype(
		{
			"name": OMR,
			"is_submittable": 1,
			"autoname": "naming_series:",
			"naming_rule": 'By "Naming Series" field',
			"track_changes": 1,
			"search_fields": "candidate_name,employee_id,questionnaire_code",
			"sort_field": "assessment_date",
			"sort_order": "DESC",
			"fields": [
				{
					"fieldname": "naming_series",
					"label": "Series",
					"fieldtype": "Select",
					"options": "DDC-OMR-.YYYY.-",
					"default": "DDC-OMR-.YYYY.-",
					"reqd": 1,
				},
				*fields,
			],
			"permissions": _permissions(),
		}
	)


def create_client_script():
	scripts = {
		MICRO: f"""
const DDC_MICRO_CRITERIA = {json.dumps(MICRO_CRITERIA)};
frappe.ui.form.on("{MICRO}", {{
    onload(frm) {{
        if (!frm.is_new()) return;
        if ((frm.doc.criteria || []).some((row) => row.criterion)) return;
        frm.clear_table("criteria");
        DDC_MICRO_CRITERIA.forEach((criterion) => frm.add_child("criteria", {{ criterion }}));
        frm.refresh_field("criteria");
    }},
}});
""",
		PREREQ: f"""
const DDC_ELIGIBILITY = {json.dumps(ELIGIBILITY_REQUIREMENTS)};
const DDC_VEHICLE = {json.dumps(VEHICLE_REQUIREMENTS)};
frappe.ui.form.on("{PREREQ}", {{
    onload(frm) {{
        if (!frm.is_new()) return;
        const filled = (rows) => (rows || []).some((row) => row.requirement);
        if (!filled(frm.doc.eligibility_requirements)) {{
            frm.clear_table("eligibility_requirements");
            DDC_ELIGIBILITY.forEach((requirement) =>
                frm.add_child("eligibility_requirements", {{ requirement }}));
            frm.refresh_field("eligibility_requirements");
        }}
        if (!filled(frm.doc.vehicle_requirements)) {{
            frm.clear_table("vehicle_requirements");
            DDC_VEHICLE.forEach((requirement) =>
                frm.add_child("vehicle_requirements", {{ requirement }}));
            frm.refresh_field("vehicle_requirements");
        }}
    }},
}});
""",
		OMR: f"""
frappe.ui.form.on("{OMR}", {{
    onload(frm) {{
        if (!frm.is_new()) return;
        if ((frm.doc.answers || []).some((row) => row.question_number)) return;
        frm.clear_table("answers");
        for (let question_number = 1; question_number <= 100; question_number++) {{
            frm.add_child("answers", {{ question_number }});
        }}
        frm.refresh_field("answers");
    }},
}});
""",
	}

	for doctype, code in scripts.items():
		name = f"{CLIENT_SCRIPT} - {doctype}"
		if frappe.db.exists("Client Script", name):
			doc = frappe.get_doc("Client Script", name)
		else:
			doc = frappe.new_doc("Client Script")
			doc.name = name
		doc.dt = doctype
		doc.view = "Form"
		doc.enabled = 1
		doc.script = code.strip()
		doc.save(ignore_permissions=True)


def _print_style():
	return """
<style>
	.ddc { font-family: Arial, Helvetica, sans-serif; font-size: 9px; color: #000; }
	.ddc h2 { text-align: center; color: #24517a; font-size: 13px; margin: 0 0 12px; }
	.ddc h3 { color: #24517a; font-size: 10px; margin: 12px 0 4px; }
	.ddc table { width: 100%; border-collapse: collapse; margin-bottom: 8px; }
	.ddc td, .ddc th { border: 1px solid #333; padding: 3px 4px; vertical-align: top; }
	.ddc th { text-align: center; background: #f2f2f2; }
	.ddc .label { font-weight: bold; background: #f5f5f5; }
	.ddc .center { text-align: center; }
	.ddc .feedback { min-height: 75px; }
	.ddc .signature { min-height: 42px; }
	.ddc .signature img { max-height: 40px; max-width: 180px; }
	.ddc .footer { border: 0; margin-top: 18px; font-size: 8px; }
	.ddc .footer td { border: 0; }
	.ddc .page-break { page-break-before: always; }
</style>
"""


def _candidate_header(title, subtitle=""):
	return (
		f"""<div class="ddc">{_print_style()}<h2>{title}</h2>"""
		+ (f'<div class="center"><b>{subtitle}</b></div>' if subtitle else "")
		+ """
<h3>Candidate Information</h3>
<table>
	<tr><td class="label">Candidate Name</td><td>{{ doc.candidate_name or "" }}</td>
		<td class="label">Employee ID</td><td>{{ doc.employee_id or "" }}</td></tr>
	<tr><td class="label">Department / Organization</td><td>{{ doc.department_organization or "" }}</td>
		<td class="label">Date of Assessment</td>
		<td>{{ frappe.format(doc.assessment_date, {"fieldtype":"Date"}) if doc.assessment_date else "" }}</td></tr>
</table>
"""
	)


def create_micro_print():
	html = (
		_candidate_header("Micro Teaching Assessment Checklist")
		+ """
<table><tr><td class="label">Assessor Name</td><td>{{ doc.assessor_name or "" }}</td></tr></table>
<h3>Assessment Criteria</h3>
<table>
	<tr><th width="43%">Criteria</th><th width="14%">Competent</th>
		<th width="17%">Needs Improvement</th><th>Comments</th></tr>
	{% for row in doc.criteria %}
	<tr><td>{{ row.criterion }}</td>
		<td class="center">{{ "✓" if row.rating == "Competent" else "☐" }}</td>
		<td class="center">{{ "✓" if row.rating == "Needs Improvement" else "☐" }}</td>
		<td>{{ row.comments or "" }}</td></tr>
	{% endfor %}
</table>
<table class="footer"><tr><td>Doc Rev: SLTIC-IDC-MTCL/Rev 0.0</td>
	<td class="center">Page 1 of 2</td><td style="text-align:right">Review: August 2028</td></tr></table>
<div class="page-break"></div>
<h3>Overall Assessment</h3>
<p><b>Overall Result:</b>
	{{ "☑" if doc.overall_result == "Competent" else "☐" }} Competent &nbsp;&nbsp;
	{{ "☑" if doc.overall_result == "Not Yet Competent" else "☐" }} Not Yet Competent
</p>
<table><tr><td><b>General Feedback:</b><div class="feedback">{{ doc.general_feedback or "" }}</div></td></tr></table>
<table><tr><td><b>Assessor Signature & Date:</b>
	<div class="signature">{% if doc.assessor_signature and "signature-placeholder" not in doc.assessor_signature %}
		<img src="{{ doc.assessor_signature }}">{% endif %}</div>
	{{ frappe.format(doc.signature_date, {"fieldtype":"Date"}) if doc.signature_date else "" }}
</td></tr></table>
<table class="footer"><tr><td>Doc Rev: SLTIC-IDC-MTCL/Rev 0.0</td>
	<td class="center">Page 2 of 2</td><td style="text-align:right">Review: August 2028</td></tr></table>
</div>
"""
	)
	_upsert_print(MICRO_PRINT, MICRO, html)


def create_prereq_print():
	html = (
		'<div class="ddc">'
		+ _print_style()
		+ """
<h2>ADNOC Defensive Driving Certification Instructor Development Course</h2>
<div class="center"><b>Candidate Pre-Requisite Checklist Form</b></div>
<h3>Candidate Information</h3>
<table>
	<tr><td class="label">Candidate Full Name</td><td colspan="3">{{ doc.candidate_name or "" }}</td></tr>
	<tr><td class="label">Employee ID</td><td colspan="3">{{ doc.employee_id or "" }}</td></tr>
	<tr><td class="label">Organization Name</td><td colspan="3">{{ doc.department_organization or "" }}</td></tr>
	<tr><td class="label">Contact Number</td><td>{{ doc.account_number or "" }}</td>
		<td class="label">Email Address</td><td>{{ doc.email_address or "" }}</td></tr>
	<tr><td class="label">ADSD Card Number</td><td colspan="3">{{ doc.adnoc_card_number or "" }}</td></tr>
</table>
<h3>Section 1 - Candidate Eligibility Requirements</h3>
<table>
	<tr><th width="42%">Requirement</th><th width="30%">Candidate Details (To be Completed)</th>
		<th width="11%">Yes / No</th><th>Verified By Assessor</th></tr>
	{% for row in doc.eligibility_requirements %}
	<tr><td>{{ row.requirement }}</td><td>{{ row.details or "" }}</td>
		<td class="center">{{ "☑" if row.result == "Yes" else "☐" }} Yes
			{{ "☑" if row.result == "No" else "☐" }} No</td>
		<td>{{ row.verified_by or "" }}</td></tr>
	{% endfor %}
</table>
<h3>Section 2 - Vehicle Pre-Requisites (If Applicable)</h3>
<table>
	<tr><th width="42%">Requirement</th><th width="30%">Details</th>
		<th width="11%">Yes / No</th><th>Verified By Assessor</th></tr>
	{% for row in doc.vehicle_requirements %}
	<tr><td>{{ row.requirement }}</td><td>{{ row.details or "" }}</td>
		<td class="center">{{ "☑" if row.result == "Yes" else "☐" }} Yes
			{{ "☑" if row.result == "No" else "☐" }} No</td>
		<td>{{ row.verified_by or "" }}</td></tr>
	{% endfor %}
</table>
<table class="footer"><tr><td>Doc Rev: SLTIC-IDC-PRCL/Rev 0.1</td>
	<td class="center">Page 1 of 2</td><td style="text-align:right">Review: August 2028</td></tr></table>
<div class="page-break"></div>
<h3>Declaration</h3>
<p>I hereby declare that the information provided above is true and correct. I understand that
failure to meet the above prerequisites may result in rejection from the ADNOC DDC TTT course.</p>
<table><tr><td><b>Candidate Signature:</b><div class="signature">
	{% if doc.candidate_signature and "signature-placeholder" not in doc.candidate_signature %}
		<img src="{{ doc.candidate_signature }}">{% endif %}</div></td>
	<td><b>Date:</b><br>{{ frappe.format(doc.declaration_date, {"fieldtype":"Date"}) if doc.declaration_date else "" }}</td></tr></table>
<table><tr><th>To be completed by the TTT Training Provider</th></tr>
	<tr><td><b>Assessor Comments:</b><div class="feedback">{{ doc.assessor_comments or "" }}</div></td></tr>
	<tr><td><b>Name:</b> {{ doc.provider_assessor_name or "" }}</td></tr>
	<tr><td><b>Signature & Date:</b><div class="signature">
		{% if doc.provider_signature and "signature-placeholder" not in doc.provider_signature %}
		<img src="{{ doc.provider_signature }}">{% endif %}</div>
		{{ frappe.format(doc.provider_date, {"fieldtype":"Date"}) if doc.provider_date else "" }}</td></tr>
</table>
<table class="footer"><tr><td>Doc Rev: SLTIC-IDC-PRCL/Rev 0.1</td>
	<td class="center">Page 2 of 2</td><td style="text-align:right">Review: August 2028</td></tr></table>
</div>
"""
	)
	_upsert_print(PREREQ_PRINT, PREREQ, html)


def create_omr_print():
	def rows(start, end):
		return "\n".join(
			f"""<tr><td class="center">{n:02d}</td>
			{{% set row = (doc.answers | selectattr("question_number", "equalto", {n}) | list | first) %}}
			{{% set ans = row.answer if row else "" %}}
			<td class="center">A {{{{ "●" if ans == "A" else "○" }}}}</td>
			<td class="center">B {{{{ "●" if ans == "B" else "○" }}}}</td>
			<td class="center">C {{{{ "●" if ans == "C" else "○" }}}}</td>
			<td class="center">D {{{{ "●" if ans == "D" else "○" }}}}</td></tr>"""
			for n in range(start, end + 1)
		)

	def page(start, end, number, last=False):
		summary = (
			"""
<table><tr><td><b>Assessment Summary (Tick One):</b>&nbsp;
	{{ "☑" if doc.assessment_summary == "Pass" else "☐" }} PASS &nbsp;&nbsp;
	{{ "☑" if doc.assessment_summary == "Refer" else "☐" }} REFER</td></tr>
	<tr><td><b>Learner Signature:</b><div class="signature">
		{% if doc.learner_signature and "signature-placeholder" not in doc.learner_signature %}
		<img src="{{ doc.learner_signature }}">{% endif %}</div>
		<b>Date:</b> {{ frappe.format(doc.signed_date, {"fieldtype":"Date"}) if doc.signed_date else "" }}</td></tr></table>
"""
			if last
			else ""
		)
		return (
			('<div class="page-break"></div>' if number > 1 else "")
			+ f"""<table><tr><th width="16%">No.</th><th>A</th><th>B</th><th>C</th><th>D</th></tr>
{rows(start, end)}</table>{summary}
<table class="footer"><tr><td>Doc Rev: SLTIC-IDC-OMR/Rev 0.0</td>
<td class="center">Page {number} of 3</td><td style="text-align:right">Review: August 2028</td></tr></table>"""
		)

	html = (
		'<div class="ddc">'
		+ _print_style()
		+ """
<h2>ADNOC Defensive Driving Certification Instructor Course</h2>
<div class="center"><b>Examination Answer Sheet (OMR)</b></div>
<table>
	<tr><td class="label">Learner Name</td><td>{{ doc.candidate_name or "" }}</td>
		<td class="label">Learner ID Number</td><td>{{ doc.employee_id or "" }}</td>
		<td class="label">Questionnaire Code</td><td>{{ doc.questionnaire_code or "" }}</td></tr>
	<tr><td class="label">Organization Name</td><td colspan="3">{{ doc.department_organization or "" }}</td>
		<td class="label">Date</td>
		<td>{{ frappe.format(doc.assessment_date, {"fieldtype":"Date"}) if doc.assessment_date else "" }}</td></tr>
	<tr><td class="label">Assessor Name</td><td colspan="3">{{ doc.assessor_name or "" }}</td>
		<td class="label">Assessor Signature</td><td></td></tr>
</table>
<p><b>INSTRUCTIONS:</b> Use a PENCIL only. Shade ONE circle completely for each question.
Do NOT tick or cross. Erase mistakes thoroughly.</p>
"""
		+ page(1, 28, 1)
		+ page(29, 66, 2)
		+ page(67, 100, 3, last=True)
		+ "</div>"
	)
	_upsert_print(OMR_PRINT, OMR, html)


def _upsert_print(name, doctype, html):
	if frappe.db.exists("Print Format", name):
		doc = frappe.get_doc("Print Format", name)
	else:
		doc = frappe.new_doc("Print Format")
		doc.name = name
	doc.doc_type = doctype
	doc.standard = "No"
	doc.custom_format = 1
	doc.print_format_type = "Jinja"
	doc.disabled = 0
	doc.html = html
	doc.save(ignore_permissions=True)
	frappe.make_property_setter(
		{
			"doctype": doctype,
			"doctype_or_field": "DocType",
			"property": "default_print_format",
			"value": name,
			"property_type": "Data",
		},
		is_system_generated=False,
	)


def setup():
	created = create_child_doctypes()
	parents = {
		MICRO: create_micro_doctype(),
		PREREQ: create_prereq_doctype(),
		OMR: create_omr_doctype(),
	}
	create_client_script()
	create_micro_print()
	create_prereq_print()
	create_omr_print()
	frappe.db.commit()
	frappe.clear_cache()
	print(f"Child doctypes created: {created or 'already present'}")
	print(f"Parent doctypes: {parents}")
	print(f"Print formats: {MICRO_PRINT}, {PREREQ_PRINT}, {OMR_PRINT}")
