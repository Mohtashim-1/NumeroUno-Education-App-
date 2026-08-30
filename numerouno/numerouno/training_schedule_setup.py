"""Register Training Schedule shortcuts and course capacity field."""

from __future__ import annotations

import json

from pathlib import Path

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

WORKSPACES = ("NumeroUNO", "Forms")
PAGE = "training-schedule"
SHORTCUT_LABEL = "Training Schedule"
COURSE_MAX_STRENGTH = "custom_max_strength"
ROLE = "Training Portal"
PORTAL_WORKSPACE = "Training Portal"


def get_custom_fields():
	return {
		"Course": [
			{
				"fieldname": COURSE_MAX_STRENGTH,
				"label": "Max Strength",
				"fieldtype": "Int",
				"insert_after": "custom_course_rate",
				"description": "Default batch capacity. Student Group Max Strength can override this. 0 means no limit.",
				"non_negative": 1,
				"translatable": 0,
			}
		]
	}


def _ensure_course_max_strength():
	create_custom_fields(get_custom_fields(), update=True)
	_insert_in_field_order("Course", [COURSE_MAX_STRENGTH], after="custom_course_rate")
	frappe.clear_cache(doctype="Course")


def _insert_in_field_order(doctype, fieldnames, after):
	name = frappe.db.get_value(
		"Property Setter",
		{"doc_type": doctype, "property": "field_order", "doctype_or_field": "DocType"},
		"name",
	)
	if not name:
		return
	doc = frappe.get_doc("Property Setter", name)
	try:
		order = json.loads(doc.value or "[]")
	except Exception:
		return
	insert_at = order.index(after) + 1 if after in order else len(order)
	for fieldname in fieldnames:
		if fieldname in order:
			continue
		order.insert(insert_at, fieldname)
		insert_at += 1
	doc.value = json.dumps(order)
	doc.save(ignore_permissions=True)


def setup():
	_ensure_course_max_strength()
	_ensure_training_candidate()
	if not frappe.db.exists("Page", PAGE):
		from frappe.modules.import_file import import_file_by_path

		page_json = Path(__file__).parent / "page" / "training_schedule" / "training_schedule.json"
		if page_json.exists():
			import_file_by_path(str(page_json), force=True)

	for workspace_name in WORKSPACES:
		_ensure_workspace(workspace_name)
	setup_access()
	frappe.db.commit()
	return {"page": PAGE, "workspaces": list(WORKSPACES)}


def _ensure_training_candidate():
	from frappe.modules.import_file import import_file_by_path

	path = Path(__file__).parent / "doctype" / "training_candidate" / "training_candidate.json"
	if path.exists():
		import_file_by_path(str(path), force=True, ignore_version=True)


def after_migrate():
	setup()


def setup_access():
	"""Role-based access for the training portal. Users are managed from User → Roles."""
	from numerouno.numerouno.api.training_schedule import INITIAL_USERS

	_ensure_role()
	_ensure_legacy_role()
	_set_page_roles()
	_ensure_portal_workspace()
	_ensure_candidate_perm()
	granted, missing = _grant_users(INITIAL_USERS)
	frappe.clear_cache()
	return {
		"role": ROLE,
		"workspace": PORTAL_WORKSPACE,
		"granted": granted,
		"missing": missing,
	}


def _ensure_role():
	if frappe.db.exists("Role", ROLE):
		return
	frappe.get_doc(
		{
			"doctype": "Role",
			"role_name": ROLE,
			"desk_access": 1,
			"is_custom": 1,
		}
	).insert(ignore_permissions=True)


def _ensure_legacy_role():
	"""Keep the earlier Training Schedule role so existing assignments still work."""
	if frappe.db.exists("Role", "Training Schedule"):
		return
	frappe.get_doc(
		{
			"doctype": "Role",
			"role_name": "Training Schedule",
			"desk_access": 1,
			"is_custom": 1,
		}
	).insert(ignore_permissions=True)


def _set_page_roles():
	if not frappe.db.exists("Page", PAGE):
		return
	existing = set(
		frappe.get_all(
			"Has Role",
			filters={"parent": PAGE, "parenttype": "Page"},
			pluck="role",
		)
	)
	for role in (ROLE, "Training Schedule"):
		if role in existing:
			continue
		frappe.get_doc(
			{
				"doctype": "Has Role",
				"parent": PAGE,
				"parenttype": "Page",
				"parentfield": "roles",
				"role": role,
			}
		).insert(ignore_permissions=True)


def _ensure_portal_workspace():
	content = [
		{
			"id": frappe.generate_hash(length=10),
			"type": "header",
			"data": {"text": '<span class="h4">Training Portal</span>', "col": 12},
		},
		{
			"id": frappe.generate_hash(length=10),
			"type": "shortcut",
			"data": {"shortcut_name": SHORTCUT_LABEL, "col": 4},
		},
	]
	if frappe.db.exists("Workspace", PORTAL_WORKSPACE):
		workspace = frappe.get_doc("Workspace", PORTAL_WORKSPACE)
	else:
		workspace = frappe.new_doc("Workspace")
		workspace.label = PORTAL_WORKSPACE
		workspace.title = PORTAL_WORKSPACE

	workspace.module = "Numerouno"
	workspace.public = 1
	workspace.is_hidden = 0
	workspace.icon = "education"
	workspace.indicator_color = "purple"
	workspace.content = json.dumps(content)
	workspace.set("shortcuts", [])
	workspace.append(
		"shortcuts",
		{
			"type": "URL",
			"url": "/training-schedule",
			"label": SHORTCUT_LABEL,
			"color": "Purple",
			"doc_view": "",
		},
	)
	workspace.set("roles", [])
	workspace.append("roles", {"role": ROLE})
	workspace.append("roles", {"role": "Training Schedule"})
	workspace.append("roles", {"role": "System Manager"})

	frappe.flags.in_import = True
	try:
		if workspace.is_new():
			workspace.insert(ignore_permissions=True)
		else:
			workspace.save(ignore_permissions=True)
	finally:
		frappe.flags.in_import = False


def _ensure_candidate_perm():
	if not frappe.db.exists("DocType", "Training Candidate"):
		return
	existing = frappe.db.exists(
		"Custom DocPerm",
		{"parent": "Training Candidate", "role": ROLE, "permlevel": 0},
	)
	values = {
		"parent": "Training Candidate",
		"parenttype": "DocType",
		"parentfield": "permissions",
		"role": ROLE,
		"permlevel": 0,
		"read": 1,
		"select": 1,
		"create": 1,
		"write": 1,
		"print": 1,
		"export": 1,
		"report": 1,
	}
	if existing:
		doc = frappe.get_doc("Custom DocPerm", existing)
		doc.update(values)
		doc.save(ignore_permissions=True)
		return
	frappe.get_doc({"doctype": "Custom DocPerm", **values}).insert(ignore_permissions=True)


def _grant_users(emails):
	"""Grant the role. Never revoke — extra people are added from User → Roles."""
	granted = []
	missing = []
	legacy_holders = frappe.get_all(
		"Has Role",
		filters={"role": "Training Schedule", "parenttype": "User"},
		pluck="parent",
	)
	wanted = list(dict.fromkeys([*emails, *legacy_holders]))
	for email in wanted:
		if not frappe.db.exists("User", email):
			missing.append(email)
			continue
		user = frappe.get_doc("User", email)
		if ROLE not in {r.role for r in user.roles}:
			user.add_roles(ROLE)
		granted.append({"email": email, "full_name": user.full_name, "enabled": int(user.enabled)})
	return granted, missing


def _ensure_workspace(workspace_name):
	if not frappe.db.exists("Workspace", workspace_name):
		return

	workspace = frappe.get_doc("Workspace", workspace_name)
	existing = {row.link_to for row in workspace.shortcuts if row.type == "Page"}
	if PAGE in existing:
		return

	workspace.append(
		"shortcuts",
		{
			"type": "Page",
			"link_to": PAGE,
			"label": SHORTCUT_LABEL,
			"color": "Purple",
			"doc_view": "",
			"format": "",
		},
	)
	workspace.save(ignore_permissions=True)
