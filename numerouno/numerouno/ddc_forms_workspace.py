"""Add the DDC instructor forms to the Forms workspace."""

import json

import frappe


WORKSPACE = "Forms"
DDC_SHORTCUTS = (
	("DDC Candidate Prerequisite", "Green"),
	("DDC Written Assessment", "Blue"),
	("DDC OMR Answer Sheet", "Orange"),
	("DDC Practical Assessment", "Red"),
	("DDC Micro Teaching Assessment", "Purple"),
)


def setup():
	workspace = frappe.get_doc("Workspace", WORKSPACE)
	existing = {row.label or row.link_to for row in workspace.shortcuts}

	for label, color in DDC_SHORTCUTS:
		if label in existing:
			continue
		workspace.append(
			"shortcuts",
			{
				"type": "DocType",
				"link_to": label,
				"doc_view": "List",
				"label": label,
				"color": color,
			},
		)

	content = json.loads(workspace.content or "[]")
	shortcut_names = {
		block.get("data", {}).get("shortcut_name")
		for block in content
		if block.get("type") == "shortcut"
	}

	if not any(
		block.get("type") == "header"
		and "DDC Instructor Course" in block.get("data", {}).get("text", "")
		for block in content
	):
		content.append(
			{
				"id": frappe.generate_hash(length=10),
				"type": "header",
				"data": {"text": '<span class="h4">DDC Instructor Course</span>', "col": 12},
			}
		)

	for label, _color in DDC_SHORTCUTS:
		if label in shortcut_names:
			continue
		content.append(
			{
				"id": frappe.generate_hash(length=10),
				"type": "shortcut",
				"data": {"shortcut_name": label, "col": 3},
			}
		)

	workspace.content = json.dumps(content)
	workspace.save(ignore_permissions=True)
	frappe.db.commit()
	return {"workspace": WORKSPACE, "added": [label for label, _color in DDC_SHORTCUTS]}
