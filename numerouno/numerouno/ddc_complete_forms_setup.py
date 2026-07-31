"""Complete ADNOC DDC Instructor Development Course forms.

Adds the forms not covered by ``ddc_instructor_forms_setup``:
- Written Assessment question papers Sets A-D (SLTIC-IDC-Q1..Q4)
- Practical Assessment Checklist (SLTIC-IDC-PACL)

Question text is loaded from ``ddc_written_question_sets.json``, extracted
verbatim from the approved source PDFs. The PDFs do not contain answer keys,
so assessor marking is intentionally manual.
"""

from __future__ import annotations

import json
from pathlib import Path

import frappe

MODULE = "Numerouno"

WRITTEN = "DDC Written Assessment"
WRITTEN_ROW = "DDC Written Assessment Question"
WRITTEN_PRINT = "DDC Instructor Course Written Assessment"

PRACTICAL = "DDC Practical Assessment"
PRACTICAL_PRECHECK = "DDC Practical Precheck Item"
PRACTICAL_KNOWLEDGE = "DDC Practical Knowledge Question"
PRACTICAL_CRITERION = "DDC Practical Criterion"
PRACTICAL_SCORE = "DDC Practical Score"
PRACTICAL_PRINT = "DDC Instructor Course Practical Assessment Checklist"

CLIENT_SCRIPT_PREFIX = "NUTC DDC Complete Forms"

PRECHECK_ITEMS = [
	"Check motor vehicle driver's license",
	"Identify and explain the purpose of the assessment",
	"Discuss the assessment and confirm the candidate understands the performance criteria",
	"Discuss relevant policies and ensure the candidate understands the implications",
	"Identify opportunities for collecting evidence to support the assessment decision",
	"Tell the candidate whom to contact for questions or further assessment information",
	"Identify any special needs of the candidate",
	"Check the location / environment is suitable for assessment",
	"Check the assessment instrument is current",
	"Identify the resources required for assessment with the candidate",
	"Confirm assessment arrangements with the candidate's supervisor",
	"Check the vehicle is modified as per ADNOC requirements",
]

KNOWLEDGE_QUESTIONS = [
	{
		"question": "What are the advantages of lifting your vision?",
		"acceptable_answer": (
			"Identify hazards and escape options early; formulate a hazard action plan; "
			"centre the vehicle without sawing the wheel; generally achieve a smoother drive."
		),
	},
	{
		"question": "What is a safe following distance?",
		"acceptable_answer": (
			"Two seconds for a light vehicle, four seconds for a heavy vehicle, "
			"and double those distances in adverse weather."
		),
	},
	{
		"question": "What are some tell-tale signs that you are not concentrating fully?",
		"acceptable_answer": "Hazards catch the driver by surprise; repeated on-and-off use of brake and accelerator.",
	},
	{
		"question": "What is the defensive driving BESAFE system?",
		"acceptable_answer": (
			"Talking through the drive to demonstrate compliance with the five observation techniques."
		),
	},
	{
		"question": "How can we increase our visibility on the road?",
		"acceptable_answer": (
			"Adjust road position, leave sufficient hang-back space, and use appropriate lighting and signals."
		),
	},
	{
		"question": "What are some factors affecting concentration?",
		"acceptable_answer": (
			"In-car or scenery distractions, drugs, alcohol, fatigue, illness and stress."
		),
	},
]

PRACTICAL_OUTCOMES = [
	{
		"number": 1,
		"outcome": "Demonstrate Pre-Trip Check",
		"weight": 10,
		"description": "Candidate demonstrates and discusses the POWERS check.",
		"criteria": [
			"Check for fluid leaks on approach to vehicle",
			"Inspect vehicle panel damage and record findings",
			"Verify vehicle documentation",
			"Confirm possession of vehicle keys prior to check",
			"Conduct full POWERS check",
		],
	},
	{
		"number": 2,
		"outcome": "Apply Correct Seating Position",
		"weight": 10,
		"description": "Seat belt, driver position and steering-wheel position are correctly maintained.",
		"criteria": [
			"Seat belt correctly worn - low, flat and firm",
			"Driver positioned correctly in seat",
			"Maintains correct steering position (9-3)",
			"Left foot braced, knees slightly bent",
			"Sits deep in seat to prevent sliding",
			"Elbows bent when holding steering wheel",
			"Head lifted for good observation",
			"Head restraint centred at base of skull",
		],
	},
	{
		"number": 3,
		"outcome": "Safely and Efficiently Operate Vehicle",
		"weight": 30,
		"description": "Drive on road, complete manoeuvres, stop and leave the vehicle safely.",
		"criteria": [
			"Ensure all passengers wear seat belts",
			"Adjust mirrors appropriately",
			"Start engine with one hand on wheel",
			"Check all gauges",
			"Ensure all doors are secure",
			"Safely enter traffic flow",
			"Smooth acceleration control",
			"Maintain steady speed",
			"Brake smoothly in a straight line",
			"Brake appropriately for conditions",
			"Stop accurately at instructed point",
			"Steer smoothly and accurately",
			"Maintain control of direction at all times",
			"Change gears smoothly",
			"Use suitable gear for speed and conditions",
			"Change gears in a straight line",
			"Adjust controls for road-surface variations",
			"Mirror-signal-blind-spot check before manoeuvre",
			"Clear rear before reversing",
			"Control manoeuvre speed",
			"Reverse parallel park - 3 moves",
			"Forward parallel park - 1 move",
			"Angle park - 1 move",
			"Three-point turn - 3 moves",
			"U-turn - 1 move",
			"Stop vehicle safely",
			"Apply park brake correctly",
			"Switch engine off",
			"Select safe gear when parked",
			"Secure vehicle",
		],
	},
	{
		"number": 4,
		"outcome": "Off-Road Skill Assessment",
		"weight": 10,
		"description": "Sand driving, pre-trip inspection and dealing with dunes using low and high gears.",
		"criteria": [
			"Pre-trip inspection for off-road",
			"Verify survival kit availability",
			"Check tyre pressure for sand driving",
			"Verify flag pole and water availability",
			"Select correct high / low gear range",
			"Steer smoothly over dunes",
			"Manage slip faces correctly",
			"Recover vehicle stuck in soft sand",
			"Descend safely from sand dunes",
		],
	},
	{
		"number": 5,
		"outcome": "Observation and Vehicle Control Skills",
		"weight": 30,
		"description": "Demonstrate effective observation and vehicle control to front, rear and sides.",
		"criteria": [
			"Maintain one-car-length stopping distance",
			"Apply 1-2 second delay before moving",
			"Maintain 2-second following distance",
			"Physically check blind spot before moving",
			"Use mirrors every 5-8 seconds",
			"Identify tailgaters and react appropriately",
			"Check RLR / LRL at intersections",
			"Prepare for stale green lights",
			"Scan parked-vehicle steering wheels",
			"Shoulder check before lane change",
			"Establish eye contact with road users",
			"Check instruments and gauges appropriately",
		],
	},
	{
		"number": 6,
		"outcome": "Anticipate Road Crash Situations",
		"weight": 10,
		"description": "Identify hazards and modify driving to suit.",
		"criteria": [
			"Spot hazards and assess risks",
			"Modify driving to suit conditions",
			"Identify risks early through observation",
			"Recognise and read intersections",
			"Avoid driving in blind spots",
			"Cover brake near significant hazards",
			"Check mirrors upon identifying a hazard",
			"Modify speed appropriately",
			"Identify road signage",
			"Anticipate pedestrian actions",
			"Anticipate driver actions",
			"Check intersections until clear",
			"Check wheel-to-ground reference",
			"Scan interior of parked vehicles",
			"Use headlights where permitted",
			"Display a courteous driving attitude",
		],
	},
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
		{"fieldname": "organization_name", "label": "Organization Name", "fieldtype": "Data"},
		{"fieldname": "candidate_email", "label": "Candidate Email", "fieldtype": "Data", "options": "Email"},
		{"fieldname": "candidate_column", "fieldtype": "Column Break"},
		{
			"fieldname": "assessment_date",
			"label": "Date of Assessment",
			"fieldtype": "Date",
			"reqd": 1,
			"in_list_view": 1,
		},
		{"fieldname": "candidate_contact", "label": "Candidate Contact Number", "fieldtype": "Data"},
		{"fieldname": "location", "label": "Location", "fieldtype": "Data"},
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
		{"fieldname": "assessor_contact", "label": "Assessor Contact Number", "fieldtype": "Data"},
		{"fieldname": "assessor_column", "fieldtype": "Column Break"},
		{"fieldname": "assessor_email", "label": "Assessor Email", "fieldtype": "Data", "options": "Email"},
	]


def create_child_doctypes():
	specs = [
		{
			"name": WRITTEN_ROW,
			"istable": 1,
			"editable_grid": 1,
			"fields": [
				{
					"fieldname": "question_number",
					"label": "No.",
					"fieldtype": "Int",
					"reqd": 1,
					"read_only": 1,
					"in_list_view": 1,
					"columns": 1,
				},
				{
					"fieldname": "question",
					"label": "Question",
					"fieldtype": "Text",
					"reqd": 1,
					"read_only": 1,
					"in_list_view": 1,
					"columns": 5,
				},
				{
					"fieldname": "options_text",
					"label": "Options",
					"fieldtype": "Small Text",
					"read_only": 1,
				},
				{"fieldname": "options_json", "label": "Options", "fieldtype": "Code", "read_only": 1, "hidden": 1},
				{
					"fieldname": "selected_answers",
					"label": "Selected Answer(s)",
					"fieldtype": "Data",
					"description": "Use A, B, C, D; comma-separate multiple answers.",
					"in_list_view": 1,
					"columns": 2,
				},
				{
					"fieldname": "marking",
					"label": "Marking",
					"fieldtype": "Select",
					"options": "\nCorrect\nIncorrect",
					"in_list_view": 1,
					"columns": 2,
				},
				{"fieldname": "remarks", "label": "Remarks", "fieldtype": "Small Text", "columns": 2},
			],
		},
		{
			"name": PRACTICAL_PRECHECK,
			"istable": 1,
			"editable_grid": 1,
			"fields": [
				{
					"fieldname": "item",
					"label": "Pre-Assessment Check",
					"fieldtype": "Small Text",
					"reqd": 1,
					"read_only": 1,
					"in_list_view": 1,
					"columns": 7,
				},
				{
					"fieldname": "result",
					"label": "Result",
					"fieldtype": "Select",
					"options": "\nYes\nNo\nN/A",
					"in_list_view": 1,
					"columns": 2,
				},
				{"fieldname": "comments", "label": "Comments", "fieldtype": "Small Text", "columns": 3},
			],
		},
		{
			"name": PRACTICAL_KNOWLEDGE,
			"istable": 1,
			"editable_grid": 1,
			"fields": [
				{
					"fieldname": "question",
					"label": "Oral Question",
					"fieldtype": "Text",
					"reqd": 1,
					"read_only": 1,
					"in_list_view": 1,
					"columns": 5,
				},
				{
					"fieldname": "satisfactory",
					"label": "Satisfactory",
					"fieldtype": "Select",
					"options": "\nYes\nNo",
					"in_list_view": 1,
					"columns": 2,
				},
				{"fieldname": "candidate_response", "label": "Candidate Response", "fieldtype": "Text", "columns": 3},
				{"fieldname": "acceptable_answer", "label": "Acceptable Answer", "fieldtype": "Text", "read_only": 1},
			],
		},
		{
			"name": PRACTICAL_CRITERION,
			"istable": 1,
			"editable_grid": 1,
			"fields": [
				{
					"fieldname": "outcome_number",
					"label": "LO",
					"fieldtype": "Int",
					"read_only": 1,
					"in_list_view": 1,
					"columns": 1,
				},
				{
					"fieldname": "learning_outcome",
					"label": "Learning Outcome",
					"fieldtype": "Small Text",
					"read_only": 1,
					"in_list_view": 1,
					"columns": 3,
				},
				{
					"fieldname": "criterion",
					"label": "Detailed Assessment Criterion",
					"fieldtype": "Small Text",
					"reqd": 1,
					"read_only": 1,
					"in_list_view": 1,
					"columns": 4,
				},
				{
					"fieldname": "source_of_evidence",
					"label": "Source of Evidence",
					"fieldtype": "Data",
					"in_list_view": 1,
					"columns": 2,
				},
				{
					"fieldname": "result",
					"label": "Y / N / N/A",
					"fieldtype": "Select",
					"options": "\nYes\nNo\nN/A",
					"in_list_view": 1,
					"columns": 2,
				},
				{"fieldname": "remarks", "label": "Remarks", "fieldtype": "Small Text"},
			],
		},
		{
			"name": PRACTICAL_SCORE,
			"istable": 1,
			"editable_grid": 1,
			"fields": [
				{
					"fieldname": "competency_area",
					"label": "Competency Area",
					"fieldtype": "Data",
					"read_only": 1,
					"in_list_view": 1,
					"columns": 5,
				},
				{
					"fieldname": "maximum_score",
					"label": "Maximum",
					"fieldtype": "Int",
					"read_only": 1,
					"in_list_view": 1,
					"columns": 2,
				},
				{
					"fieldname": "score",
					"label": "Score",
					"fieldtype": "Float",
					"in_list_view": 1,
					"columns": 2,
				},
				{"fieldname": "remarks", "label": "Remarks", "fieldtype": "Small Text", "columns": 3},
			],
		},
	]
	return [spec["name"] for spec in specs if _create_doctype(spec)]


def create_written_doctype():
	fields = _candidate_fields() + _assessor_fields()
	fields += [
		{"fieldname": "paper_section", "label": "Question Paper", "fieldtype": "Section Break"},
		{
			"fieldname": "question_set",
			"label": "Written Assessment Set",
			"fieldtype": "Select",
			"options": "\nA\nB\nC\nD",
			"reqd": 1,
			"in_list_view": 1,
			"in_standard_filter": 1,
		},
		{
			"fieldname": "instructions",
			"label": "Instructions",
			"fieldtype": "HTML",
			"options": (
				"<p><b>Use the OMR sheet to complete the examination. "
				"A minimum score of 100% must be attained to pass.</b></p>"
			),
		},
		{
			"fieldname": "questions",
			"label": "Questions and Responses",
			"fieldtype": "Table",
			"options": WRITTEN_ROW,
			"reqd": 1,
		},
		{"fieldname": "result_section", "label": "Assessment Result", "fieldtype": "Section Break"},
		{
			"fieldname": "correct_answers",
			"label": "Correct Answers",
			"fieldtype": "Int",
			"read_only": 1,
		},
		{
			"fieldname": "assessment_result",
			"label": "Result",
			"fieldtype": "Select",
			"options": "\nPass\nRefer",
			"in_list_view": 1,
		},
		{"fieldname": "result_column", "fieldtype": "Column Break"},
		{"fieldname": "assessor_comments", "label": "Assessor Comments", "fieldtype": "Small Text"},
	]
	return _create_doctype(
		{
			"name": WRITTEN,
			"is_submittable": 1,
			"autoname": "naming_series:",
			"naming_rule": 'By "Naming Series" field',
			"track_changes": 1,
			"search_fields": "candidate_name,employee_id,question_set,assessor_name",
			"sort_field": "assessment_date",
			"sort_order": "DESC",
			"fields": [
				{
					"fieldname": "naming_series",
					"label": "Series",
					"fieldtype": "Select",
					"options": "DDC-WA-.YYYY.-",
					"default": "DDC-WA-.YYYY.-",
					"reqd": 1,
				},
				*fields,
			],
			"permissions": _permissions(),
		}
	)


def ensure_written_options_field():
	"""Add the printable options field when upgrading an already-created child DocType."""
	if not frappe.db.exists("DocType", WRITTEN_ROW):
		return
	meta = frappe.get_meta(WRITTEN_ROW, cached=False)
	if meta.get_field("options_text"):
		return
	doc = frappe.get_doc("DocType", WRITTEN_ROW)
	doc.append(
		"fields",
		{
			"fieldname": "options_text",
			"label": "Options",
			"fieldtype": "Small Text",
			"read_only": 1,
		},
	)
	doc.save(ignore_permissions=True)


def create_practical_doctype():
	fields = _candidate_fields() + [
		{"fieldname": "time_start", "label": "Time Start", "fieldtype": "Time"},
		{"fieldname": "time_finish", "label": "Time Finish", "fieldtype": "Time"},
		{"fieldname": "license_section", "label": "Driving License", "fieldtype": "Section Break"},
		{"fieldname": "license_number", "label": "License Number", "fieldtype": "Data"},
		{"fieldname": "license_expiry", "label": "Expiry Date", "fieldtype": "Date"},
		{"fieldname": "license_column", "fieldtype": "Column Break"},
		{"fieldname": "license_type", "label": "License Type", "fieldtype": "Data"},
	] + _assessor_fields()
	fields += [
		{
			"fieldname": "instructions_section",
			"label": "Instructions to the Assessor",
			"fieldtype": "Section Break",
		},
		{
			"fieldname": "instructions",
			"label": "Assessment Instructions",
			"fieldtype": "HTML",
			"options": (
				"<p>To achieve competency all boxes must be ticked or marked N/A. "
				"Record reasons for N/A and supporting assessor comments. Terminate the "
				"assessment if the candidate is involved in a crash/near miss or the assessor feels unsafe.</p>"
			),
		},
		{"fieldname": "precheck_section", "label": "Pre-Assessment Information Guide", "fieldtype": "Section Break"},
		{
			"fieldname": "precheck_items",
			"label": "Pre-Assessment Checks",
			"fieldtype": "Table",
			"options": PRACTICAL_PRECHECK,
			"reqd": 1,
		},
		{"fieldname": "knowledge_section", "label": "Questions for Checking Knowledge", "fieldtype": "Section Break"},
		{
			"fieldname": "knowledge_questions",
			"label": "Oral Questions",
			"fieldtype": "Table",
			"options": PRACTICAL_KNOWLEDGE,
			"reqd": 1,
		},
		{
			"fieldname": "knowledge_result",
			"label": "Candidate's Underpinning Knowledge",
			"fieldtype": "Select",
			"options": "\nSatisfactory\nNot Satisfactory",
		},
		{"fieldname": "knowledge_feedback", "label": "Feedback to Candidate", "fieldtype": "Small Text"},
		{"fieldname": "criteria_section", "label": "Observation Checklist", "fieldtype": "Section Break"},
		{
			"fieldname": "criteria",
			"label": "Detailed Assessment Criteria",
			"fieldtype": "Table",
			"options": PRACTICAL_CRITERION,
			"reqd": 1,
		},
		{"fieldname": "summary_section", "label": "Assessment Summary", "fieldtype": "Section Break"},
		{
			"fieldname": "scores",
			"label": "Competency Scores",
			"fieldtype": "Table",
			"options": PRACTICAL_SCORE,
			"reqd": 1,
		},
		{
			"fieldname": "grand_total",
			"label": "Grand Total",
			"fieldtype": "Float",
			"read_only": 1,
			"in_list_view": 1,
		},
		{
			"fieldname": "assessment_result",
			"label": "Assessment Result",
			"fieldtype": "Select",
			"options": "\nCompetent\nNot Yet Competent",
			"reqd": 1,
			"in_list_view": 1,
		},
		{"fieldname": "summary_column", "fieldtype": "Column Break"},
		{"fieldname": "reason_for_non_approval", "label": "Reason for Non-Approval", "fieldtype": "Small Text"},
		{"fieldname": "assessor_comments", "label": "Assessor Comments", "fieldtype": "Text Editor"},
		{"fieldname": "signature_section", "label": "Signatures", "fieldtype": "Section Break"},
		{"fieldname": "candidate_signature", "label": "Candidate Signature", "fieldtype": "Signature"},
		{"fieldname": "candidate_signature_date", "label": "Candidate Signature Date", "fieldtype": "Date"},
		{"fieldname": "signature_column", "fieldtype": "Column Break"},
		{"fieldname": "assessor_signature", "label": "Assessor Signature", "fieldtype": "Signature"},
		{"fieldname": "assessor_signature_date", "label": "Assessor Signature Date", "fieldtype": "Date"},
	]
	return _create_doctype(
		{
			"name": PRACTICAL,
			"is_submittable": 1,
			"autoname": "naming_series:",
			"naming_rule": 'By "Naming Series" field',
			"track_changes": 1,
			"search_fields": "candidate_name,employee_id,assessor_name,license_number",
			"sort_field": "assessment_date",
			"sort_order": "DESC",
			"fields": [
				{
					"fieldname": "naming_series",
					"label": "Series",
					"fieldtype": "Select",
					"options": "DDC-PA-.YYYY.-",
					"default": "DDC-PA-.YYYY.-",
					"reqd": 1,
				},
				*fields,
			],
			"permissions": _permissions(),
		}
	)


def _question_sets():
	path = Path(__file__).with_name("ddc_written_question_sets.json")
	return json.loads(path.read_text(encoding="utf-8"))


@frappe.whitelist()
def get_written_questions(set_code):
	set_code = (set_code or "").strip().upper()
	if set_code not in ("A", "B", "C", "D"):
		frappe.throw("Written assessment set must be A, B, C or D")
	return _question_sets()[set_code]


@frappe.whitelist()
def get_practical_template():
	criteria = []
	scores = []
	for outcome in PRACTICAL_OUTCOMES:
		scores.append(
			{
				"competency_area": outcome["outcome"],
				"maximum_score": outcome["weight"],
			}
		)
		for criterion in outcome["criteria"]:
			criteria.append(
				{
					"outcome_number": outcome["number"],
					"learning_outcome": outcome["outcome"],
					"criterion": criterion,
				}
			)
	return {
		"prechecks": [{"item": item} for item in PRECHECK_ITEMS],
		"knowledge": KNOWLEDGE_QUESTIONS,
		"criteria": criteria,
		"scores": scores,
	}


def _upsert_client_script(doctype, code):
	name = f"{CLIENT_SCRIPT_PREFIX} - {doctype}"
	doc = frappe.get_doc("Client Script", name) if frappe.db.exists("Client Script", name) else frappe.new_doc("Client Script")
	if doc.is_new():
		doc.name = name
	doc.dt = doctype
	doc.view = "Form"
	doc.enabled = 1
	doc.script = code.strip()
	doc.save(ignore_permissions=True)


def create_client_scripts():
	_upsert_client_script(
		WRITTEN,
		f"""
frappe.ui.form.on("{WRITTEN}", {{
    refresh(frm) {{
        frm.set_value("correct_answers", (frm.doc.questions || [])
            .filter(row => row.marking === "Correct").length);
    }},
    question_set(frm) {{
        if (!frm.doc.question_set) return;
        const load = () => frappe.call({{
            method: "numerouno.numerouno.ddc_complete_forms_setup.get_written_questions",
            args: {{ set_code: frm.doc.question_set }},
            callback: (r) => {{
                frm.clear_table("questions");
                (r.message || []).forEach((item) => frm.add_child("questions", {{
                    question_number: item.number,
                    question: item.question,
                    options_text: item.options.map((option, index) =>
                        `${{String.fromCharCode(65 + index)}}. ${{option}}`).join("\\n"),
                    options_json: JSON.stringify(item.options)
                }}));
                frm.refresh_field("questions");
            }}
        }});
        if ((frm.doc.questions || []).some(row => row.question)) {{
            frappe.confirm(__("Changing the set will replace all current questions and responses."), load);
        }} else {{
            load();
        }}
    }}
}});
frappe.ui.form.on("{WRITTEN_ROW}", {{
    marking(frm) {{
        frm.set_value("correct_answers", (frm.doc.questions || [])
            .filter(row => row.marking === "Correct").length);
    }}
}});
""",
	)
	_upsert_client_script(
		PRACTICAL,
		f"""
frappe.ui.form.on("{PRACTICAL}", {{
    onload(frm) {{
        const hasTemplate = (frm.doc.criteria || []).some(row => row.criterion);
        if (!frm.is_new() || hasTemplate || frm.__ddc_template_loading) return;
        frm.__ddc_template_loading = true;
        frappe.call({{
            method: "numerouno.numerouno.ddc_complete_forms_setup.get_practical_template",
            callback: (r) => {{
                const data = r.message || {{}};
                ["precheck_items", "knowledge_questions", "criteria", "scores"]
                    .forEach(field => frm.clear_table(field));
                (data.prechecks || []).forEach(row => frm.add_child("precheck_items", row));
                (data.knowledge || []).forEach(row => frm.add_child("knowledge_questions", row));
                (data.criteria || []).forEach(row => frm.add_child("criteria", row));
                (data.scores || []).forEach(row => frm.add_child("scores", row));
                ["precheck_items", "knowledge_questions", "criteria", "scores"]
                    .forEach(field => frm.refresh_field(field));
            }},
            always: () => {{ frm.__ddc_template_loading = false; }}
        }});
    }},
    validate(frm) {{
        const total = (frm.doc.scores || []).reduce((sum, row) => sum + (row.score || 0), 0);
        frm.set_value("grand_total", total);
        for (const row of (frm.doc.scores || [])) {{
            if ((row.score || 0) > (row.maximum_score || 0)) {{
                frappe.throw(__("Score for {{0}} cannot exceed {{1}}", [row.competency_area, row.maximum_score]));
            }}
        }}
    }}
}});
frappe.ui.form.on("{PRACTICAL_SCORE}", {{
    score(frm) {{
        frm.set_value("grand_total", (frm.doc.scores || [])
            .reduce((sum, row) => sum + (row.score || 0), 0));
    }}
}});
""",
	)


def _print_style():
	return """
<style>
	.ddc { font-family: Arial, Helvetica, sans-serif; font-size: 9px; color: #000; }
	.ddc h2 { text-align:center; color:#24517a; font-size:13px; margin:0 0 6px; }
	.ddc h3 { color:#24517a; font-size:10px; margin:10px 0 4px; }
	.ddc table { width:100%; border-collapse:collapse; margin-bottom:7px; }
	.ddc td, .ddc th { border:1px solid #333; padding:3px 4px; vertical-align:top; }
	.ddc th { text-align:center; background:#f2f2f2; }
	.ddc .label { font-weight:bold; background:#f5f5f5; }
	.ddc .center { text-align:center; }
	.ddc .question { margin:0 0 7px; page-break-inside:avoid; line-height:1.35; }
	.ddc .option { margin-left:14px; }
	.ddc .signature { min-height:38px; }
	.ddc .signature img { max-height:36px; max-width:170px; }
	.ddc .footer { border:0; margin-top:12px; font-size:8px; }
	.ddc .footer td { border:0; }
	.ddc .page-break { page-break-before:always; }
</style>
"""


def _footer(code, page, total):
	return f"""<table class="footer"><tr><td>Doc Rev: {code}/Rev 0.0</td>
<td class="center">Page {page} of {total}</td><td style="text-align:right">Review: August 2028</td></tr></table>"""


def _upsert_print(name, doctype, html):
	doc = frappe.get_doc("Print Format", name) if frappe.db.exists("Print Format", name) else frappe.new_doc("Print Format")
	if doc.is_new():
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


def create_written_print():
	pages = []
	for page in range(1, 14):
		start = (page - 1) * 8 + 1
		end = min(page * 8, 100)
		header = ""
		if page == 1:
			header = """
<h2>ADNOC Defensive Driving Certification Instructor Development Course</h2>
<div class="center"><b>Written Assessment (Set - {{ doc.question_set }})</b></div>
<p><b>Please use the OMR sheet to complete the examination. A minimum score of 100% must be attained to pass.</b></p>
"""
		body = f"""
{{% for row in doc.questions %}}{{% if row.question_number >= {start} and row.question_number <= {end} %}}
<div class="question"><b>{{{{ row.question_number }}}}. {{{{ row.question }}}}</b>
<div class="option" style="white-space:pre-line">{{{{ row.options_text or "" }}}}</div></div>
{{% endif %}}{{% endfor %}}
"""
		pages.append(
			('<div class="page-break"></div>' if page > 1 else "")
			+ header
			+ body
			+ _footer("SLTIC-IDC-Q" + "{{ doc.question_set }}", page, 13)
		)
	_upsert_print(
		WRITTEN_PRINT,
		WRITTEN,
		'<div class="ddc">' + _print_style() + "".join(pages) + "</div>",
	)


def create_practical_print():
	html = (
		'<div class="ddc">'
		+ _print_style()
		+ """
<h2>ADNOC Defensive Driving Certification Instructor Development Course</h2>
<div class="center"><b>Practical Assessment Checklist</b></div>
<table>
<tr><td class="label">Time Start</td><td>{{ doc.time_start or "" }}</td><td class="label">Time Finish</td><td>{{ doc.time_finish or "" }}</td></tr>
<tr><td class="label">Candidate Name</td><td colspan="3">{{ doc.candidate_name or "" }}</td></tr>
<tr><td class="label">Candidate Email</td><td>{{ doc.candidate_email or "" }}</td><td class="label">Contact Number</td><td>{{ doc.candidate_contact or "" }}</td></tr>
<tr><td class="label">Date of Assessment</td><td>{{ frappe.format(doc.assessment_date, {"fieldtype":"Date"}) if doc.assessment_date else "" }}</td><td class="label">Location</td><td>{{ doc.location or "" }}</td></tr>
<tr><td class="label">Assessor Name</td><td>{{ doc.assessor_name or "" }}</td><td class="label">Assessor Contact</td><td>{{ doc.assessor_contact or "" }}</td></tr>
<tr><td class="label">Assessor Email</td><td colspan="3">{{ doc.assessor_email or "" }}</td></tr>
<tr><td class="label">License Number</td><td>{{ doc.license_number or "" }}</td><td class="label">Expiry / Type</td><td>{{ frappe.format(doc.license_expiry, {"fieldtype":"Date"}) if doc.license_expiry else "" }} / {{ doc.license_type or "" }}</td></tr>
<tr><td class="label">Assessment Result</td><td colspan="3">☐ COMPETENT &nbsp;&nbsp; ☐ NOT YET COMPETENT</td></tr>
</table>
<table><tr><td><b>Candidate Signature</b><div class="signature">{% if doc.candidate_signature %}<img src="{{ doc.candidate_signature }}">{% endif %}</div></td>
<td><b>Assessor Signature</b><div class="signature">{% if doc.assessor_signature %}<img src="{{ doc.assessor_signature }}">{% endif %}</div></td></tr></table>
"""
		+ _footer("SLTIC-IDC-PACL", 1, 7)
		+ """
<div class="page-break"></div>
<h3>Instructions to the Assessor</h3>
<p>To achieve competency all boxes must be ticked or marked N/A. Reasons for N/A must be recorded beside the box and in Assessor Comments. Blank boxes indicate that further evidence is required.</p>
<h3>Conducting the Assessment</h3>
<p>A driving assessment enables the candidate to demonstrate driving expertise. Terminate the assessment if the candidate is involved in a crash or near miss, or if the assessor feels unsafe due to the candidate's actions.</p>
<h3>Assessment Methods</h3><ul><li>Visual observations</li><li>Verbal questions</li><li>Practical drive</li></ul>
<h3>Equipment and Venue</h3><p>Roadworthy motor vehicle, assessment sheet, clipboard and pens. Use appropriate local roads and worksite areas during daylight hours.</p>
<h3>Assessment Scope</h3><p>Confirm familiarity with the vehicle and local conditions; assess the full range of tasks; record evidence; and advise the candidate of any additional assessment required.</p>
"""
		+ _footer("SLTIC-IDC-PACL", 2, 7)
		+ """
<div class="page-break"></div><h3>Pre-Assessment Information Guide</h3>
<table><tr><th>With the candidate, did you:</th><th width="9%">Y</th><th width="9%">N</th><th width="9%">N/A</th><th>Comments</th></tr>
{% for row in doc.precheck_items %}<tr><td>{{ row.item }}</td>
<td class="center">{{ "☑" if row.result == "Yes" else "☐" }}</td><td class="center">{{ "☑" if row.result == "No" else "☐" }}</td>
<td class="center">{{ "☑" if row.result == "N/A" else "☐" }}</td><td>{{ row.comments or "" }}</td></tr>{% endfor %}</table>
"""
		+ _footer("SLTIC-IDC-PACL", 3, 7)
		+ """
<div class="page-break"></div><h3>Questions for Checking Knowledge - Oral Questions</h3>
<table><tr><th>Question</th><th width="10%">Yes</th><th width="10%">No</th><th>Candidate Response</th></tr>
{% for row in doc.knowledge_questions %}<tr><td>{{ loop.index }}. {{ row.question }}</td>
<td class="center">{{ "☑" if row.satisfactory == "Yes" else "☐" }}</td><td class="center">{{ "☑" if row.satisfactory == "No" else "☐" }}</td>
<td>{{ row.candidate_response or "" }}</td></tr>{% endfor %}</table>
<p><b>The candidate's underpinning knowledge was:</b> {{ doc.knowledge_result or "" }}</p>
<p><b>Feedback:</b> {{ doc.knowledge_feedback or "" }}</p>
<h3>Acceptable Answers</h3><ol>{% for row in doc.knowledge_questions %}<li>{{ row.acceptable_answer }}</li>{% endfor %}</ol>
"""
		+ _footer("SLTIC-IDC-PACL", 4, 7)
		+ """
<div class="page-break"></div><h3>Observation Checklist (Learning Outcomes 1-3)</h3>
<table><tr><th width="4%">LO</th><th width="20%">Learning Outcome</th><th>Detailed Assessment Criterion</th><th>Source of Evidence</th><th width="7%">Y/N/N/A</th></tr>
{% for row in doc.criteria %}{% if row.outcome_number <= 3 %}<tr><td class="center">{{ row.outcome_number }}</td><td>{{ row.learning_outcome }}</td>
<td>{{ row.criterion }}</td><td>{{ row.source_of_evidence or "" }}</td><td class="center">{{ row.result or "" }}</td></tr>{% endif %}{% endfor %}</table>
"""
		+ _footer("SLTIC-IDC-PACL", 5, 7)
		+ """
<div class="page-break"></div><h3>Observation Checklist (Learning Outcomes 4-6)</h3>
<table><tr><th width="4%">LO</th><th width="20%">Learning Outcome</th><th>Detailed Assessment Criterion</th><th>Source of Evidence</th><th width="7%">Y/N/N/A</th></tr>
{% for row in doc.criteria %}{% if row.outcome_number >= 4 %}<tr><td class="center">{{ row.outcome_number }}</td><td>{{ row.learning_outcome }}</td>
<td>{{ row.criterion }}</td><td>{{ row.source_of_evidence or "" }}</td><td class="center">{{ row.result or "" }}</td></tr>{% endif %}{% endfor %}</table>
"""
		+ _footer("SLTIC-IDC-PACL", 6, 7)
		+ """
<div class="page-break"></div><h3>Assessment Summary</h3>
<p>The candidate has attained competence when all criteria are achieved.</p>
<table><tr><th>Competency Area</th><th width="12%">Maximum</th><th width="12%">Score</th><th>Remarks</th></tr>
{% for row in doc.scores %}<tr><td>{{ row.competency_area }}</td><td class="center">{{ row.maximum_score }}</td>
<td class="center">{{ row.score or "" }}</td><td>{{ row.remarks or "" }}</td></tr>{% endfor %}
<tr><th>Grand Total</th><th>100</th><th>{{ doc.grand_total or 0 }}</th><th></th></tr></table>
<p><b>Assessment Result:</b> {{ "☑" if doc.assessment_result == "Competent" else "☐" }} COMPETENT &nbsp;&nbsp;
{{ "☑" if doc.assessment_result == "Not Yet Competent" else "☐" }} NOT YET COMPETENT</p>
<table><tr><td><b>Reason for Non-Approval:</b><br>{{ doc.reason_for_non_approval or "" }}</td></tr>
<tr><td><b>Assessor Comments:</b><br>{{ doc.assessor_comments or "" }}</td></tr></table>
<table><tr><td><b>Candidate:</b> {{ doc.candidate_name }}<div class="signature">{% if doc.candidate_signature %}<img src="{{ doc.candidate_signature }}">{% endif %}</div>
{{ frappe.format(doc.candidate_signature_date, {"fieldtype":"Date"}) if doc.candidate_signature_date else "" }}</td>
<td><b>Assessor:</b> {{ doc.assessor_name or "" }}<div class="signature">{% if doc.assessor_signature %}<img src="{{ doc.assessor_signature }}">{% endif %}</div>
{{ frappe.format(doc.assessor_signature_date, {"fieldtype":"Date"}) if doc.assessor_signature_date else "" }}</td></tr></table>
"""
		+ _footer("SLTIC-IDC-PACL", 7, 7)
		+ "</div>"
	)
	_upsert_print(PRACTICAL_PRINT, PRACTICAL, html)


def align_existing_forms():
	"""Correct labels/revision details in the earlier prerequisite setup."""
	updates = {
		"account_number": "Contact Number",
		"adnoc_card_number": "ADSD Card Number",
	}
	for fieldname, label in updates.items():
		name = frappe.db.get_value(
			"DocField",
			{"parent": "DDC Candidate Prerequisite", "fieldname": fieldname},
			"name",
		)
		if name:
			frappe.db.set_value("DocField", name, "label", label, update_modified=False)


def setup():
	# Keep the three forms from the original setup available as part of the full package.
	from numerouno.numerouno.ddc_instructor_forms_setup import setup as setup_existing

	setup_existing()
	align_existing_forms()
	children = create_child_doctypes()
	ensure_written_options_field()
	parents = {
		WRITTEN: create_written_doctype(),
		PRACTICAL: create_practical_doctype(),
	}
	create_client_scripts()
	create_written_print()
	create_practical_print()
	frappe.db.commit()
	frappe.clear_cache()
	print(f"Additional child doctypes created: {children or 'already present'}")
	print(f"Additional parent doctypes: {parents}")
	print(f"Additional print formats: {WRITTEN_PRINT}, {PRACTICAL_PRINT}")
