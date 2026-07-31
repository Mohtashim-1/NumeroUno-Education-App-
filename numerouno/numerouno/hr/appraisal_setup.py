# Copyright (c) 2026, NumeroUNO and contributors
# License: MIT

"""Set up the NUTC Performance Appraisal Form (NUTC-EOMS-P22-F07.1) in ERPNext/HRMS.

The paper form is mapped onto standard HRMS Appraisal doctypes:

- Section I  (Appraisal Information) -> Appraisal fields + custom fields
- Section II (Rating Scale)          -> printed as reference + performance band calculation
- Section III(Rating by Appraiser)   -> Appraisal Template KRAs (competency + weightage),
                                        rated manually by the appraiser on a 0-5 scale
                                        (score x weightage -> weighted % out of 100)

Run with:
    bench --site <site> execute numerouno.numerouno.hr.appraisal_setup.setup
"""

from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import getdate, today

COMPANY = "Numero Uno Training and Consulting LLC"
TEMPLATE_NAME = "NUTC Performance Appraisal"
PRINT_FORMAT_NAME = "NUTC Performance Appraisal Form"
CLIENT_SCRIPT_NAME = "NUTC Appraisal Performance Band"
FORM_REF = "NUTC-P22-F07.1 - Rev. 1 - August 2025"
APPRAISAL_ROLE = "NUTC Appraisal User"
APPRAISAL_USERS = {
	"Minhaj": "m.mashood@numerouno-me.com",
	"Vinod": "sales@nutc.ae",
	"Ahmed": "a.mamdouh@numerouno-me.com",
	"Monis": "sales1@nutc.ae",
	"Nayab": "n.jahangir@numerouno-me.com",
	"Samy": "s.fathallah@nutc.ae",
	"Nanda": "n.gopal@numerouno-me.com",
}

# (competency, description, weightage %) -- Section III of the form. Weightages total 100.
COMPETENCIES = [
	(
		"HSE Performance",
		"Works in a safe manner, aware of safety of others, able to identify hazards and take "
		"proper control based on the company's hierarchy of control; can participate in safety discussions.",
		10,
	),
	(
		"Role Specific Job Skills",
		"Aptitudes, talent, knowledge and training needed to perform well at the job.",
		20,
	),
	(
		"Technical Competence",
		"Demonstrates effective application of required knowledge and skills.",
		15,
	),
	(
		"Proactive",
		"Able to identify potential challenges before they arise. Does not wait for instructions; "
		"instead, takes the lead to contribute and enhance team dynamics.",
		10,
	),
	(
		"Innovative",
		"Can come up with innovative ideas to enhance performance and work operations.",
		5,
	),
	(
		"Versatility & Adaptability",
		"Learns new methods and techniques quickly, responds readily to new situations.",
		5,
	),
	(
		"Problem Solving/Judgement",
		"Sizes up problems quickly, makes prompt, sound decisions after analysing relevant facts.",
		5,
	),
	(
		"Administrative/Organising Ability",
		"Arranges work for most effective handling of tasks, uses time efficiently.",
		5,
	),
	(
		"Communication Skills",
		"Expresses ideas clearly in speech and writing, listens effectively, keeps others informed as appropriate.",
		5,
	),
	("Punctuality", "Always reports for watch/duty on time.", 5),
	("Productivity", "Gets things done, maintains required standard for quality and quantity.", 10),
	(
		"Personal Development",
		"Invests in career development via identifying strengths, weaknesses and goals to develop; "
		"engages in continuous learning, seeking mentorship and challenging assignments.",
		5,
	),
]

# (lower bound %, upper bound %, rating, description) -- Section II of the form
RATING_BANDS = [
	(90, None, "Outstanding", "Performance is consistently superior and significantly exceeds position requirements."),
	(80, 90, "Exceeding", "Performance frequently exceeds position requirements."),
	(65, 80, "Proficient", "Performance consistently meets position requirements."),
	(50, 65, "Inconsistent", "Performance meets some, but not all position requirements."),
	(
		None,
		50,
		"Unsatisfactory",
		"Performance consistently fails to meet minimum position requirements, employee lacks skills "
		"required or fails to utilise necessary skills.",
	),
]


def get_band(percentage: float) -> str:
	"""Map an overall percentage onto the Section II rating scale."""
	pct = float(percentage or 0)
	for lower, upper, rating, _desc in RATING_BANDS:
		if (lower is None or pct >= lower) and (upper is None or pct < upper):
			return rating
	return ""


def create_kras():
	for title, description, _weight in COMPETENCIES:
		if frappe.db.exists("KRA", title):
			doc = frappe.get_doc("KRA", title)
			doc.description = description
			doc.save(ignore_permissions=True)
		else:
			frappe.get_doc(
				{"doctype": "KRA", "title": title, "description": description}
			).insert(ignore_permissions=True)


def create_feedback_criteria():
	"""Same competencies re-used for line manager / reviewer feedback ratings."""
	for title, _description, _weight in COMPETENCIES:
		if not frappe.db.exists("Employee Feedback Criteria", title):
			frappe.get_doc(
				{"doctype": "Employee Feedback Criteria", "criteria": title}
			).insert(ignore_permissions=True)


def create_appraisal_template():
	if frappe.db.exists("Appraisal Template", TEMPLATE_NAME):
		doc = frappe.get_doc("Appraisal Template", TEMPLATE_NAME)
	else:
		doc = frappe.new_doc("Appraisal Template")
		doc.template_title = TEMPLATE_NAME

	doc.description = (
		f"Annual performance appraisal competencies as per {FORM_REF}. "
		"Each competency is rated 0-5 by the appraiser and weighted to a score out of 100."
	)
	doc.set("goals", [])
	doc.set("rating_criteria", [])

	for title, _description, weight in COMPETENCIES:
		doc.append("goals", {"key_result_area": title, "per_weightage": weight})
		doc.append("rating_criteria", {"criteria": title, "per_weightage": weight})

	doc.save(ignore_permissions=True)
	return doc.name


def assign_template_to_designations(template: str = TEMPLATE_NAME):
	"""Use the NUTC template by default for every employee designation."""
	designations = frappe.get_all("Designation", pluck="name")
	for designation in designations:
		frappe.db.set_value(
			"Designation",
			designation,
			"appraisal_template",
			template,
			update_modified=False,
		)
	return len(designations)


def grant_appraisal_access(users: dict[str, str] | None = None):
	"""Grant appraisal-only Desk access without granting broad HR User permissions."""
	users = users or APPRAISAL_USERS

	if not frappe.db.exists("Role", APPRAISAL_ROLE):
		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": APPRAISAL_ROLE,
				"desk_access": 1,
			}
		).insert(ignore_permissions=True)

	permissions = {
		"Appraisal": {
			"read": 1,
			"write": 1,
			"create": 1,
			"submit": 1,
			"report": 1,
			"print": 1,
			"email": 1,
			"share": 1,
		},
		"Appraisal Cycle": {"read": 1, "report": 1},
		"Appraisal Template": {"read": 1, "select": 1},
		"KRA": {"read": 1, "select": 1},
		"Employee Feedback Criteria": {"read": 1, "select": 1},
		"Employee Performance Feedback": {
			"read": 1,
			"write": 1,
			"create": 1,
			"submit": 1,
			"report": 1,
			"print": 1,
		},
	}

	for doctype, rights in permissions.items():
		filters = {"parent": doctype, "role": APPRAISAL_ROLE, "permlevel": 0}
		name = frappe.db.get_value("Custom DocPerm", filters, "name")
		doc = frappe.get_doc("Custom DocPerm", name) if name else frappe.new_doc("Custom DocPerm")
		doc.parent = doctype
		doc.role = APPRAISAL_ROLE
		doc.permlevel = 0
		for field in (
			"select",
			"read",
			"write",
			"create",
			"delete",
			"submit",
			"cancel",
			"amend",
			"report",
			"export",
			"import",
			"share",
			"print",
			"email",
		):
			doc.set(field, rights.get(field, 0))
		doc.save(ignore_permissions=True)

	assigned = []
	for display_name, user_id in users.items():
		if not frappe.db.exists("User", {"name": user_id, "enabled": 1}):
			frappe.throw(f"Enabled user not found for {display_name}: {user_id}")
		user = frappe.get_doc("User", user_id)
		user.add_roles(APPRAISAL_ROLE)
		assigned.append(user_id)

	frappe.clear_cache()
	return assigned


def create_custom_fields_for_form():
	fields = {
		"Appraisal": [
			{
				"fieldname": "custom_appraisal_year",
				"label": "Appraisal Year",
				"fieldtype": "Data",
				"insert_after": "designation",
				"in_standard_filter": 1,
				"description": "Section I of the appraisal form",
			},
			{
				"fieldname": "custom_division",
				"label": "Division",
				"fieldtype": "Data",
				"insert_after": "custom_appraisal_year",
			},
			{
				"fieldname": "custom_appraiser",
				"label": "Appraiser",
				"fieldtype": "Link",
				"options": "Employee",
				"insert_after": "custom_division",
			},
			{
				"fieldname": "custom_appraiser_name",
				"label": "Appraiser Name",
				"fieldtype": "Data",
				"fetch_from": "custom_appraiser.employee_name",
				"read_only": 1,
				"insert_after": "custom_appraiser",
			},
			{
				"fieldname": "custom_line_manager",
				"label": "Line Manager",
				"fieldtype": "Link",
				"options": "Employee",
				"insert_after": "custom_appraiser_name",
			},
			{
				"fieldname": "custom_line_manager_name",
				"label": "Line Manager Name",
				"fieldtype": "Data",
				"fetch_from": "custom_line_manager.employee_name",
				"read_only": 1,
				"insert_after": "custom_line_manager",
			},
			{
				"fieldname": "custom_score_percentage",
				"label": "Overall Performance Rating (%)",
				"fieldtype": "Percent",
				"read_only": 1,
				"insert_after": "final_score",
				"description": "Weighted appraiser score converted to a percentage",
			},
			{
				"fieldname": "custom_performance_band",
				"label": "Performance Band",
				"fieldtype": "Data",
				"read_only": 1,
				"insert_after": "custom_score_percentage",
				"in_list_view": 1,
				"in_standard_filter": 1,
			},
			{
				"fieldname": "custom_professional_development",
				"label": "Professional Development Identified",
				"fieldtype": "Small Text",
				"insert_after": "remarks",
			},
		],
		"Appraisal Goal": [
			{
				"fieldname": "custom_remarks",
				"label": "Remarks",
				"fieldtype": "Small Text",
				"insert_after": "score_earned",
				"in_list_view": 1,
			}
		],
	}
	create_custom_fields(fields, update=True)


def create_client_script():
	code = """
frappe.ui.form.on("Appraisal", {
	refresh: set_nutc_performance_band,
	validate: set_nutc_performance_band,
	total_score: set_nutc_performance_band,
	final_score: set_nutc_performance_band,
});

function set_nutc_performance_band(frm) {
	const score = flt(frm.doc.final_score) || flt(frm.doc.total_score);
	const pct = flt(score * 20, 2);

	let band = "Unsatisfactory";
	if (pct >= 90) band = "Outstanding";
	else if (pct >= 80) band = "Exceeding";
	else if (pct >= 65) band = "Proficient";
	else if (pct >= 50) band = "Inconsistent";

	if (frm.doc.custom_score_percentage !== pct) {
		frm.set_value("custom_score_percentage", pct);
	}
	if (frm.doc.custom_performance_band !== band) {
		frm.set_value("custom_performance_band", band);
	}
}
""".strip()

	if frappe.db.exists("Client Script", CLIENT_SCRIPT_NAME):
		doc = frappe.get_doc("Client Script", CLIENT_SCRIPT_NAME)
	else:
		doc = frappe.new_doc("Client Script")
		doc.name = CLIENT_SCRIPT_NAME

	doc.dt = "Appraisal"
	doc.view = "Form"
	doc.enabled = 1
	doc.script = code
	doc.save(ignore_permissions=True)


def get_print_format_html() -> str:
	scale_rows = "".join(
		f"""<tr>
			<td class="c b">{_band_label(lower, upper)}</td>
			<td class="c">{rating}</td>
			<td>{desc}</td>
		</tr>"""
		for lower, upper, rating, desc in RATING_BANDS
	)

	return (
		"""
<style>
	.nutc-appraisal { font-family: Arial, Helvetica, sans-serif; font-size: 10.5px; color: #000; }
	.nutc-appraisal table { width: 100%; border-collapse: collapse; margin-bottom: 10px; }
	.nutc-appraisal td, .nutc-appraisal th { border: 1px solid #000; padding: 4px 6px; vertical-align: top; }
	.nutc-appraisal .title { border: 2px solid #000; text-align: center; font-weight: bold;
		padding: 6px; margin-bottom: 12px; letter-spacing: .5px; }
	.nutc-appraisal .section { background: #efefef; border: 1px solid #000; text-align: center;
		font-weight: bold; padding: 4px; margin-bottom: 0; }
	.nutc-appraisal th { background: #efefef; text-align: center; font-weight: bold; }
	.nutc-appraisal .c { text-align: center; }
	.nutc-appraisal .b { font-weight: bold; }
	.nutc-appraisal .fill { height: 46px; }
	.nutc-appraisal .foot { margin-top: 14px; font-size: 9px; text-align: left; }
</style>

<div class="nutc-appraisal">
	<div class="title">PERFORMANCE APPRAISAL FORM</div>

	<div class="section">SECTION I : APPRAISAL INFORMATION</div>
	{% set appraiser_designation = frappe.db.get_value("Employee", doc.custom_appraiser, "designation") if doc.custom_appraiser else "" %}
	<table>
		<tr>
			<td width="30%"><b>Employee Name:</b><br>{{ doc.employee_name or "" }}</td>
			<td width="12%"><b>Emp. No.:</b><br>{{ doc.employee or "" }}</td>
			<td width="30%"><b>Appraiser Name:</b><br>{{ doc.custom_appraiser_name or "" }}</td>
			<td width="12%"><b>Emp. No.:</b><br>{{ doc.custom_appraiser or "" }}</td>
		</tr>
		<tr>
			<td colspan="2"><b>Position Title:</b> {{ doc.designation or "" }}</td>
			<td colspan="2"><b>Position Title:</b> {{ appraiser_designation or "" }}</td>
		</tr>
		<tr><td colspan="4"><b>Division:</b> {{ doc.custom_division or doc.department or "" }}</td></tr>
		<tr><td colspan="4"><b>Appraisal Year:</b> {{ doc.custom_appraisal_year or doc.appraisal_cycle or "" }}</td></tr>
	</table>

	<div class="section">SECTION II : RATING SCALE &amp; DESCRIPTION</div>
	<table>
		<tr>
			<th width="12%">Rating Scale</th>
			<th width="18%">Rating</th>
			<th>Description</th>
		</tr>
		"""
		+ scale_rows
		+ """
	</table>

	<div class="section">SECTION III : RATING BY APPRAISER</div>
	{% set rows = doc.goals if doc.goals else doc.appraisal_kra %}
	<table>
		<tr>
			<th width="18%">COMPETENCY</th>
			<th width="37%">DESCRIPTION</th>
			<th width="8%">WEIGHT %</th>
			<th width="12%">RATING</th>
			<th width="25%">REMARKS</th>
		</tr>
		{% for row in rows %}
		{% set kra_name = row.kra %}
		<tr>
			<td>{{ kra_name }}</td>
			<td>{{ frappe.db.get_value("KRA", kra_name, "description") or "" }}</td>
			<td class="c">{{ row.per_weightage | round(0) | int }}</td>
			<td class="c">
				{% if row.get("score") %}
					{{ row.score }} / 5 ({{ (row.score * 20) | round(0) | int }}%)
				{% endif %}
			</td>
			<td>{{ row.get("custom_remarks") or "" }}</td>
		</tr>
		{% endfor %}
	</table>

	<table>
		<tr><td><b>Professional Development Identified:</b><div class="fill">{{ doc.custom_professional_development or "" }}</div></td></tr>
		<tr><td><b>Overall Performance Remarks:</b><div class="fill">{{ doc.remarks or "" }}</div></td></tr>
		{% set score = doc.final_score or doc.total_score or 0 %}
		{% set pct = doc.custom_score_percentage or (score * 20) %}
		{% set band = doc.custom_performance_band or ("Outstanding" if pct >= 90 else ("Exceeding" if pct >= 80
			else ("Proficient" if pct >= 65 else ("Inconsistent" if pct >= 50 else "Unsatisfactory")))) %}
		<tr><td><b>Overall Performance Rating:</b>
			{% if pct %}{{ pct | round(1) }}% &mdash; {{ band }}{% endif %}
		</td></tr>
	</table>

	<table>
		<tr>
			<th width="25%"></th>
			<th width="30%">Name</th>
			<th width="25%">Signature</th>
			<th width="20%">Date</th>
		</tr>
		<tr><td class="b">Employee</td><td>{{ doc.employee_name or "" }}</td><td></td><td></td></tr>
		<tr><td class="b">Appraiser</td><td>{{ doc.custom_appraiser_name or "" }}</td><td></td><td></td></tr>
		<tr><td class="b">Line Manager</td><td>{{ doc.custom_line_manager_name or "" }}</td><td></td><td></td></tr>
	</table>

	<div class="foot">"""
		+ FORM_REF
		+ """</div>
</div>
"""
	)


def _band_label(lower, upper) -> str:
	if lower is None:
		return f"&lt;{upper}"
	if upper is None:
		return f"{lower}+"
	return f"{lower}-{upper}"


def create_print_format():
	if frappe.db.exists("Print Format", PRINT_FORMAT_NAME):
		doc = frappe.get_doc("Print Format", PRINT_FORMAT_NAME)
	else:
		doc = frappe.new_doc("Print Format")
		doc.name = PRINT_FORMAT_NAME

	doc.doc_type = "Appraisal"
	doc.standard = "No"
	doc.custom_format = 1
	doc.print_format_type = "Jinja"
	doc.disabled = 0
	doc.html = get_print_format_html()
	doc.save(ignore_permissions=True)

	frappe.make_property_setter(
		{
			"doctype": "Appraisal",
			"doctype_or_field": "DocType",
			"property": "default_print_format",
			"value": PRINT_FORMAT_NAME,
			"property_type": "Data",
		},
		is_system_generated=False,
	)


def create_appraisal_cycle(year: int | None = None):
	year = int(year or getdate(today()).year)
	cycle_name = f"NUTC Appraisal {year}"

	if frappe.db.exists("Appraisal Cycle", cycle_name):
		doc = frappe.get_doc("Appraisal Cycle", cycle_name)
	else:
		doc = frappe.new_doc("Appraisal Cycle")
		doc.cycle_name = cycle_name

	doc.company = COMPANY
	doc.start_date = f"{year}-01-01"
	doc.end_date = f"{year}-12-31"
	doc.kra_evaluation_method = "Manual Rating"
	doc.calculate_final_score_based_on_formula = 1
	# Final score = appraiser's weighted competency score only (as per the paper form)
	doc.final_score_formula = "goal_score"
	doc.description = (
		f"Annual performance appraisal cycle for {year} as per {FORM_REF}. "
		"Appraisers rate each competency from 0 to 5; scores are weighted to a total out of 100."
	)
	doc.save(ignore_permissions=True)
	return doc.name


def setup(year: int | None = None):
	create_kras()
	create_feedback_criteria()
	template = create_appraisal_template()
	designations = assign_template_to_designations(template)
	create_custom_fields_for_form()
	create_client_script()
	create_print_format()
	cycle = create_appraisal_cycle(year)

	frappe.db.commit()
	frappe.clear_cache()

	print(f"Appraisal Template: {template}")
	print(f"Appraisal Cycle: {cycle}")
	print(f"Print Format: {PRINT_FORMAT_NAME}")
	print(f"KRAs: {len(COMPETENCIES)} competencies, total weightage 100%")
	print(f"Designations assigned: {designations}")
