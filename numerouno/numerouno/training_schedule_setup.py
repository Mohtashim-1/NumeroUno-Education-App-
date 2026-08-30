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
ROLE = "Training Schedule"


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
	"""Restrict Training Schedule to the named reception users."""
	from numerouno.numerouno.api.training_schedule import ACCESS_USERS

	_ensure_role()
	_set_page_roles()
	granted, missing, revoked = _sync_users(ACCESS_USERS)
	frappe.clear_cache()
	return {
		"role": ROLE,
		"granted": granted,
		"missing": missing,
		"revoked": revoked,
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


def _set_page_roles():
	if not frappe.db.exists("Page", PAGE):
		return
	frappe.db.delete("Has Role", {"parent": PAGE, "parenttype": "Page"})
	frappe.get_doc(
		{
			"doctype": "Has Role",
			"parent": PAGE,
			"parenttype": "Page",
			"parentfield": "roles",
			"role": ROLE,
		}
	).insert(ignore_permissions=True)


def _sync_users(emails):
	wanted = {email.lower() for email in emails}
	granted = []
	missing = []
	revoked = []

	holders = frappe.get_all(
		"Has Role",
		filters={"role": ROLE, "parenttype": "User"},
		fields=["parent"],
	)
	for row in holders:
		parent = row.parent
		if parent in wanted or parent == "Administrator":
			continue
		if not frappe.db.exists("User", parent):
			continue
		frappe.get_doc("User", parent).remove_roles(ROLE)
		revoked.append(parent)

	for email in emails:
		if not frappe.db.exists("User", email):
			missing.append(email)
			continue
		user = frappe.get_doc("User", email)
		if ROLE not in {r.role for r in user.roles}:
			user.add_roles(ROLE)
		granted.append({"email": email, "full_name": user.full_name, "enabled": int(user.enabled)})
	return granted, missing, revoked


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
