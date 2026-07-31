# Copyright (c) 2026, NumeroUNO and contributors
# License: MIT

"""Set up the NUTC Minutes of Staff Weekly Meeting form (NUTC-P04-F13) in ERPNext.

Creates a submittable "Staff Meeting Minutes" doctype (plus child tables) that mirrors
the paper form, along with a matching print format and a client script that fills the
meeting day and can push action items to To-Do.

Run with:
    bench --site <site> execute numerouno.numerouno.hr.meeting_minutes_setup.setup
"""

from __future__ import annotations

import frappe

MODULE = "Numerouno"
PARENT_DOCTYPE = "Staff Meeting Minutes"
POINT_DOCTYPE = "Staff Meeting Point"
ATTENDEE_DOCTYPE = "Staff Meeting Attendee"
ACTION_DOCTYPE = "Staff Meeting Action Item"
PRINT_FORMAT_NAME = "NUTC Minutes of Staff Weekly Meeting"
CLIENT_SCRIPT_NAME = "NUTC Staff Meeting Minutes"
FORM_REF = "NUTC-P04-F13 Minutes of Staff Weekly Meeting"
FORM_REV = "Rev.1 Dated 15.07.2026"


def _create_doctype(spec: dict):
	"""Create a Custom DocType if it does not exist yet (no data is ever overwritten)."""
	if frappe.db.exists("DocType", spec["name"]):
		return False

	doc = frappe.get_doc({"doctype": "DocType", "custom": 1, "module": MODULE, **spec})
	doc.insert(ignore_permissions=True)
	return True


def create_child_doctypes():
	created = []

	if _create_doctype(
		{
			"name": POINT_DOCTYPE,
			"istable": 1,
			"editable_grid": 1,
			"fields": [
				{
					"fieldname": "point",
					"label": "Point",
					"fieldtype": "Small Text",
					"in_list_view": 1,
					"reqd": 1,
					"columns": 10,
				}
			],
		}
	):
		created.append(POINT_DOCTYPE)

	if _create_doctype(
		{
			"name": ATTENDEE_DOCTYPE,
			"istable": 1,
			"editable_grid": 1,
			"fields": [
				{
					"fieldname": "employee",
					"label": "Employee",
					"fieldtype": "Link",
					"options": "Employee",
					"in_list_view": 1,
					"columns": 3,
				},
				{
					"fieldname": "attendee_name",
					"label": "Name",
					"fieldtype": "Data",
					"fetch_from": "employee.employee_name",
					"fetch_if_empty": 1,
					"in_list_view": 1,
					"columns": 4,
				},
				{
					"fieldname": "designation",
					"label": "Designation",
					"fieldtype": "Data",
					"fetch_from": "employee.designation",
					"fetch_if_empty": 1,
					"in_list_view": 1,
					"columns": 3,
				},
			],
		}
	):
		created.append(ATTENDEE_DOCTYPE)

	if _create_doctype(
		{
			"name": ACTION_DOCTYPE,
			"istable": 1,
			"editable_grid": 1,
			"fields": [
				{
					"fieldname": "action_item",
					"label": "Action Item",
					"fieldtype": "Small Text",
					"in_list_view": 1,
					"reqd": 1,
					"columns": 4,
				},
				{
					"fieldname": "responsible",
					"label": "Responsible",
					"fieldtype": "Link",
					"options": "Employee",
					"in_list_view": 1,
					"columns": 2,
				},
				{
					"fieldname": "responsible_name",
					"label": "Responsible Name",
					"fieldtype": "Data",
					"fetch_from": "responsible.employee_name",
					"fetch_if_empty": 1,
					"in_list_view": 1,
					"columns": 2,
				},
				{
					"fieldname": "due_date",
					"label": "Due Date",
					"fieldtype": "Date",
					"in_list_view": 1,
					"columns": 2,
				},
				{
					"fieldname": "status",
					"label": "Status",
					"fieldtype": "Select",
					"options": "Open\nIn Progress\nCompleted",
					"default": "Open",
					"in_list_view": 1,
					"columns": 1,
				},
				{
					"fieldname": "todo",
					"label": "To Do",
					"fieldtype": "Link",
					"options": "ToDo",
					"read_only": 1,
				},
			],
		}
	):
		created.append(ACTION_DOCTYPE)

	return created


def create_parent_doctype():
	spec = {
		"name": PARENT_DOCTYPE,
		"is_submittable": 1,
		"autoname": "naming_series:",
		"naming_rule": 'By "Naming Series" field',
		"track_changes": 1,
		"search_fields": "meeting_date,meeting_location",
		"sort_field": "meeting_date",
		"sort_order": "DESC",
		"fields": [
			{
				"fieldname": "naming_series",
				"label": "Series",
				"fieldtype": "Select",
				"options": "NUTC-MOM-.YYYY.-",
				"default": "NUTC-MOM-.YYYY.-",
				"reqd": 1,
			},
			{
				"fieldname": "meeting_date",
				"label": "Meeting Date",
				"fieldtype": "Date",
				"reqd": 1,
				"in_list_view": 1,
				"in_standard_filter": 1,
			},
			{
				"fieldname": "meeting_day",
				"label": "Day",
				"fieldtype": "Data",
				"read_only": 1,
			},
			{
				"fieldname": "meeting_time",
				"label": "Meeting Time",
				"fieldtype": "Time",
			},
			{"fieldname": "column_break_details", "fieldtype": "Column Break"},
			{
				"fieldname": "meeting_location",
				"label": "Meeting Location",
				"fieldtype": "Data",
				"in_list_view": 1,
			},
			{
				"fieldname": "meeting_facilitator",
				"label": "Meeting Facilitator",
				"fieldtype": "Link",
				"options": "Employee",
				"in_standard_filter": 1,
			},
			{
				"fieldname": "facilitator_name",
				"label": "Facilitator Name",
				"fieldtype": "Data",
				"fetch_from": "meeting_facilitator.employee_name",
				"read_only": 1,
			},
			{
				"fieldname": "minutes_issued_by",
				"label": "Minutes Issued By",
				"fieldtype": "Link",
				"options": "Employee",
			},
			{
				"fieldname": "issued_by_name",
				"label": "Issued By Name",
				"fieldtype": "Data",
				"fetch_from": "minutes_issued_by.employee_name",
				"read_only": 1,
			},
			{
				"fieldname": "company",
				"label": "Company",
				"fieldtype": "Link",
				"options": "Company",
			},
			{
				"fieldname": "attendees_section",
				"label": "Attendees",
				"fieldtype": "Section Break",
			},
			{
				"fieldname": "attendees",
				"label": "Attendees",
				"fieldtype": "Table",
				"options": ATTENDEE_DOCTYPE,
			},
			{
				"fieldname": "agenda_section",
				"label": "Agenda of the Weekly Meeting",
				"fieldtype": "Section Break",
			},
			{
				"fieldname": "agenda",
				"label": "Agenda",
				"fieldtype": "Table",
				"options": POINT_DOCTYPE,
			},
			{
				"fieldname": "discussion_section",
				"label": "Discussion & Agreements",
				"fieldtype": "Section Break",
			},
			{
				"fieldname": "discussion",
				"label": "Discussion & Agreements",
				"fieldtype": "Table",
				"options": POINT_DOCTYPE,
			},
			{
				"fieldname": "action_section",
				"label": "Action Items",
				"fieldtype": "Section Break",
			},
			{
				"fieldname": "action_items",
				"label": "Action Items",
				"fieldtype": "Table",
				"options": ACTION_DOCTYPE,
			},
			{
				"fieldname": "misc_section",
				"label": "Miscellaneous Items",
				"fieldtype": "Section Break",
			},
			{
				"fieldname": "miscellaneous_items",
				"label": "Miscellaneous Items",
				"fieldtype": "Text Editor",
			},
		],
		"permissions": [
			{
				"role": "System Manager",
				"read": 1,
				"write": 1,
				"create": 1,
				"delete": 1,
				"submit": 1,
				"cancel": 1,
				"amend": 1,
				"print": 1,
				"email": 1,
				"share": 1,
				"report": 1,
			},
			{
				"role": "HR Manager",
				"read": 1,
				"write": 1,
				"create": 1,
				"delete": 1,
				"submit": 1,
				"cancel": 1,
				"amend": 1,
				"print": 1,
				"email": 1,
				"share": 1,
				"report": 1,
			},
			{
				"role": "HR User",
				"read": 1,
				"write": 1,
				"create": 1,
				"submit": 1,
				"print": 1,
				"email": 1,
				"share": 1,
				"report": 1,
			},
			{"role": "Employee", "read": 1, "print": 1},
		],
	}

	return _create_doctype(spec)


def create_client_script():
	code = """
frappe.ui.form.on("Staff Meeting Minutes", {
	meeting_date(frm) {
		if (!frm.doc.meeting_date) {
			frm.set_value("meeting_day", "");
			return;
		}
		const day = frappe.datetime.str_to_obj(frm.doc.meeting_date).toLocaleDateString("en-US", {
			weekday: "long",
		});
		frm.set_value("meeting_day", day);
	},

	refresh(frm) {
		if (frm.doc.docstatus !== 1) return;

		const pending = (frm.doc.action_items || []).filter((row) => row.responsible && !row.todo);
		if (!pending.length) return;

		frm.add_custom_button(__("Create To-Dos"), () => {
			frappe.call({
				method: "numerouno.numerouno.hr.meeting_minutes_setup.create_todos",
				args: { docname: frm.doc.name },
				freeze: true,
				freeze_message: __("Creating To-Dos"),
			}).then((r) => {
				frappe.msgprint(__("{0} To-Do(s) created", [r.message || 0]));
				frm.reload_doc();
			});
		});
	},
});
""".strip()

	if frappe.db.exists("Client Script", CLIENT_SCRIPT_NAME):
		doc = frappe.get_doc("Client Script", CLIENT_SCRIPT_NAME)
	else:
		doc = frappe.new_doc("Client Script")
		doc.name = CLIENT_SCRIPT_NAME

	doc.dt = PARENT_DOCTYPE
	doc.view = "Form"
	doc.enabled = 1
	doc.script = code
	doc.save(ignore_permissions=True)


@frappe.whitelist()
def create_todos(docname: str):
	"""Create a To-Do for each action item that has a responsible employee with a user."""
	doc = frappe.get_doc(PARENT_DOCTYPE, docname)
	doc.check_permission("read")
	count = 0

	for row in doc.action_items:
		if not row.responsible or row.todo:
			continue

		user = frappe.db.get_value("Employee", row.responsible, "user_id")
		if not user:
			continue

		todo = frappe.get_doc(
			{
				"doctype": "ToDo",
				"allocated_to": user,
				"date": row.due_date,
				"description": f"{row.action_item}\n\n{FORM_REF}: {doc.name}",
				"reference_type": PARENT_DOCTYPE,
				"reference_name": doc.name,
			}
		).insert(ignore_permissions=True)

		row.db_set("todo", todo.name, update_modified=False)
		count += 1

	return count


def get_print_format_html() -> str:
	return """
<style>
	.nutc-mom { font-family: Arial, Helvetica, sans-serif; font-size: 11px; color: #000; }
	.nutc-mom table { width: 100%; border-collapse: collapse; margin-bottom: 10px; }
	.nutc-mom td, .nutc-mom th { border: 1px solid #000; padding: 4px 6px; vertical-align: top; }
	.nutc-mom .heading { text-align: center; font-weight: bold; font-size: 13px; margin-bottom: 10px; }
	.nutc-mom .bar { background: #efefef; font-weight: bold; }
	.nutc-mom .lbl { background: #efefef; font-weight: bold; width: 22%; }
	.nutc-mom .fill { min-height: 40px; }
	.nutc-mom th { background: #efefef; text-align: center; }
	.nutc-mom ol { margin: 0; padding-left: 18px; }
	.nutc-mom .foot { margin-top: 14px; font-size: 9px; }
	.nutc-mom .foot td { border: none; padding: 0; }
</style>

<div class="nutc-mom">
	<div class="heading">MINUTES OF STAFF WEEKLY MEETING</div>

	<table>
		<tr>
			<td class="lbl">Meeting Date / Day</td>
			<td colspan="2">
				{{ frappe.format(doc.meeting_date, {"fieldtype": "Date"}) if doc.meeting_date else "" }}
				{% if doc.meeting_day %} / {{ doc.meeting_day }}{% endif %}
			</td>
		</tr>
		<tr>
			<td class="lbl">Meeting Time:</td>
			<td colspan="2">{{ frappe.format(doc.meeting_time, {"fieldtype": "Time"}) if doc.meeting_time else "" }}</td>
		</tr>
		<tr>
			<td class="lbl">Meeting Location:</td>
			<td colspan="2">{{ doc.meeting_location or "" }}</td>
		</tr>
		<tr>
			<td class="lbl">Meeting Facilitator:</td>
			<td colspan="2">{{ doc.facilitator_name or "" }}</td>
		</tr>
		<tr>
			<td class="lbl">Minutes Issued By:</td>
			<td colspan="2">{{ doc.issued_by_name or "" }}</td>
		</tr>
		{% set attendees = doc.attendees or [] %}
		{% set rows = (attendees | length + 1) // 2 if attendees else 1 %}
		{% for i in range(rows) %}
		<tr>
			{% if i == 0 %}<td class="lbl" rowspan="{{ rows }}">Attendees:</td>{% endif %}
			{% set left = attendees[i * 2] if attendees | length > i * 2 else None %}
			{% set right = attendees[i * 2 + 1] if attendees | length > i * 2 + 1 else None %}
			<td width="39%">{{ left.attendee_name if left else "" }}</td>
			<td width="39%">{{ right.attendee_name if right else "" }}</td>
		</tr>
		{% endfor %}
	</table>

	<table>
		<tr><td class="bar">Agenda of the Weekly Meeting</td></tr>
		<tr><td>
			<ol class="fill">
				{% for row in doc.agenda %}<li>{{ row.point }}</li>{% endfor %}
			</ol>
		</td></tr>
	</table>

	<table>
		<tr><td class="bar">Discussion &amp; Agreements:</td></tr>
		<tr><td>
			<ol class="fill">
				{% for row in doc.discussion %}<li>{{ row.point }}</li>{% endfor %}
			</ol>
		</td></tr>
	</table>

	<table>
		<tr>
			<th width="60%">Action Items</th>
			<th width="22%">Responsible</th>
			<th width="18%">Due Date</th>
		</tr>
		{% for row in doc.action_items %}
		<tr>
			<td>{{ row.action_item or "" }}</td>
			<td>{{ row.responsible_name or "" }}</td>
			<td>{{ frappe.format(row.due_date, {"fieldtype": "Date"}) if row.due_date else "" }}</td>
		</tr>
		{% endfor %}
		{% if not doc.action_items %}<tr><td>&nbsp;</td><td></td><td></td></tr>{% endif %}
	</table>

	<table>
		<tr><td class="bar">Miscellaneous Items:</td></tr>
		<tr><td><div class="fill">{{ doc.miscellaneous_items or "" }}</div></td></tr>
	</table>

	<table class="foot">
		<tr>
			<td width="50%">""" + FORM_REF + """</td>
			<td width="50%" style="text-align:right">""" + FORM_REV + """</td>
		</tr>
	</table>
</div>
"""


def create_print_format():
	if frappe.db.exists("Print Format", PRINT_FORMAT_NAME):
		doc = frappe.get_doc("Print Format", PRINT_FORMAT_NAME)
	else:
		doc = frappe.new_doc("Print Format")
		doc.name = PRINT_FORMAT_NAME

	doc.doc_type = PARENT_DOCTYPE
	doc.standard = "No"
	doc.custom_format = 1
	doc.print_format_type = "Jinja"
	doc.disabled = 0
	doc.html = get_print_format_html()
	doc.save(ignore_permissions=True)

	frappe.make_property_setter(
		{
			"doctype": PARENT_DOCTYPE,
			"doctype_or_field": "DocType",
			"property": "default_print_format",
			"value": PRINT_FORMAT_NAME,
			"property_type": "Data",
		},
		is_system_generated=False,
	)


def setup():
	children = create_child_doctypes()
	parent_created = create_parent_doctype()
	create_client_script()
	create_print_format()

	frappe.db.commit()
	frappe.clear_cache()

	print(f"Child doctypes created: {children or 'already present'}")
	print(f"{PARENT_DOCTYPE}: {'created' if parent_created else 'already present'}")
	print(f"Print Format: {PRINT_FORMAT_NAME}")
