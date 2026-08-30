"""Dedicated HABC workspace and access for Highfield forms."""

from __future__ import annotations

import json

import frappe

ROLE = "HABC"
WORKSPACE = "HABC"
MODULE = "Numerouno"

ACCESS_USERS = (
	"m.acharya@numerouno-me.com",  # Madhura Acharya
	"s.arshad@numerouno-me.com",  # Seyad Arshad
	"s.javed@numerouno-me.com",  # Shaik Javed
	"a.manoharakumar@numerouno-me.com",  # Aparna Manoharakumar
	"shoaibmohtashim973@gmail.com",  # Mohtashim
	"sales1@nutc.ae",  # Monis Khan
)

FORM_PAGES = (
	"habc1-assessment-form",
	"habc2-examination-form",
)

PARENT_DOCTYPES = (
	"HABC1 Assessment Pack",
	"HABC2 Examination Declaration",
)

RELATED_READ = (
	"Student Group",
	"Student",
	"Course",
	"Instructor",
)

SHORTCUTS = (
	{
		"type": "Page",
		"link_to": "habc1-assessment-form",
		"label": "First Aid",
		"color": "Blue",
		"doc_view": "",
	},
	{
		"type": "DocType",
		"link_to": "HABC1 Assessment Pack",
		"label": "First Aid List",
		"color": "Blue",
		"doc_view": "List",
	},
	{
		"type": "Page",
		"link_to": "habc2-examination-form",
		"label": "Fire Safety",
		"color": "Orange",
		"doc_view": "",
	},
	{
		"type": "DocType",
		"link_to": "HABC2 Examination Declaration",
		"label": "Fire Safety List",
		"color": "Orange",
		"doc_view": "List",
	},
)

WRITE_PERMS = {
	"read": 1,
	"select": 1,
	"create": 1,
	"write": 1,
	"print": 1,
	"export": 1,
	"report": 1,
	"email": 1,
	"share": 1,
	"submit": 1,
	"cancel": 1,
	"amend": 1,
}

READ_PERMS = {
	"read": 1,
	"select": 1,
}


def after_migrate():
	try:
		setup()
	except Exception:
		frappe.log_error(title="HABC workspace after_migrate")


def setup():
	ensure_role()
	ensure_workspace()
	for doctype in PARENT_DOCTYPES:
		ensure_custom_perm(doctype, WRITE_PERMS)
	for doctype in RELATED_READ:
		ensure_custom_perm(doctype, READ_PERMS)
	for page in FORM_PAGES:
		ensure_page_role(page)
	frappe.db.set_value("Page", "habc1-assessment-form", "title", "First Aid")
	frappe.db.set_value("Page", "habc2-examination-form", "title", "Fire Safety")
	granted = grant_users(ACCESS_USERS)
	frappe.clear_cache()
	frappe.db.commit()
	return {
		"workspace": WORKSPACE,
		"role": ROLE,
		"granted": granted,
		"shortcuts": [row["label"] for row in SHORTCUTS],
	}


def ensure_role():
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


def ensure_workspace():
	if frappe.db.exists("Workspace", WORKSPACE):
		workspace = frappe.get_doc("Workspace", WORKSPACE)
	else:
		workspace = frappe.new_doc("Workspace")
		workspace.label = WORKSPACE
		workspace.title = WORKSPACE

	workspace.module = MODULE
	workspace.public = 1
	workspace.is_hidden = 0
	workspace.icon = "education"
	workspace.indicator_color = "blue"

	workspace.set("shortcuts", [])
	content = [
		{
			"id": frappe.generate_hash(length=10),
			"type": "header",
			"data": {"text": '<span class="h4">HABC Forms</span>', "col": 12},
		}
	]
	for spec in SHORTCUTS:
		if spec["type"] == "DocType" and not frappe.db.exists("DocType", spec["link_to"]):
			continue
		if spec["type"] == "Page" and not frappe.db.exists("Page", spec["link_to"]):
			continue
		workspace.append(
			"shortcuts",
			{
				"type": spec["type"],
				"link_to": spec["link_to"],
				"label": spec["label"],
				"color": spec["color"],
				"doc_view": spec.get("doc_view") or "",
			},
		)
		content.append(
			{
				"id": frappe.generate_hash(length=10),
				"type": "shortcut",
				"data": {"shortcut_name": spec["label"], "col": 3},
			}
		)
	workspace.content = json.dumps(content)
	workspace.set("roles", [])
	workspace.append("roles", {"role": ROLE})
	workspace.append("roles", {"role": "System Manager"})

	frappe.flags.in_import = True
	try:
		if workspace.is_new():
			workspace.insert(ignore_permissions=True)
		else:
			workspace.save(ignore_permissions=True)
	finally:
		frappe.flags.in_import = False
	return WORKSPACE


def ensure_custom_perm(doctype, perms):
	if not frappe.db.exists("DocType", doctype):
		return
	existing = frappe.db.exists(
		"Custom DocPerm",
		{"parent": doctype, "role": ROLE, "permlevel": 0},
	)
	values = {
		"parent": doctype,
		"parenttype": "DocType",
		"parentfield": "permissions",
		"role": ROLE,
		"permlevel": 0,
		**perms,
	}
	if existing:
		doc = frappe.get_doc("Custom DocPerm", existing)
		doc.update(values)
		doc.save(ignore_permissions=True)
		return
	frappe.get_doc({"doctype": "Custom DocPerm", **values}).insert(ignore_permissions=True)


def ensure_page_role(page_name):
	if not frappe.db.exists("Page", page_name):
		return
	if frappe.db.exists("Has Role", {"parent": page_name, "parenttype": "Page", "role": ROLE}):
		return
	frappe.get_doc(
		{
			"doctype": "Has Role",
			"parent": page_name,
			"parenttype": "Page",
			"parentfield": "roles",
			"role": ROLE,
		}
	).insert(ignore_permissions=True)


def grant_users(emails):
	granted = []
	missing = []
	for email in emails:
		if not frappe.db.exists("User", email):
			missing.append(email)
			continue
		user = frappe.get_doc("User", email)
		if ROLE not in {r.role for r in user.roles}:
			user.add_roles(ROLE)
		granted.append({"email": email, "full_name": user.full_name, "enabled": int(user.enabled)})
	return {"users": granted, "missing": missing}
