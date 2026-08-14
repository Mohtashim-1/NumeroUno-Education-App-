"""Add ADNOC instructor forms to the Forms workspace."""

import json

import frappe

WORKSPACE = "Forms"
ADNOC_HEADER = "ADNOC"
LEGACY_HEADERS = ("DDC Instructor Course", "ADNOC DDC Instructor Course")

# ADNOC DDC Instructor Development Course forms
ADNOC_SHORTCUTS = (
	("DDC Candidate Prerequisite", "Green"),
	("DDC Written Assessment", "Blue"),
	("DDC OMR Answer Sheet", "Orange"),
	("DDC Practical Assessment", "Red"),
	("DDC Micro Teaching Assessment", "Purple"),
	("Pre Test ADSD", "Cyan"),
)


def setup():
	workspace = frappe.get_doc("Workspace", WORKSPACE)
	existing = {row.label or row.link_to for row in workspace.shortcuts}

	for label, color in ADNOC_SHORTCUTS:
		if label in existing:
			continue
		if not frappe.db.exists("DocType", label):
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
	content = _strip_legacy_adnoc_blocks(content)
	content = _ensure_adnoc_section(content)

	workspace.content = json.dumps(content)
	workspace.save(ignore_permissions=True)
	frappe.db.commit()
	return {
		"workspace": WORKSPACE,
		"header": ADNOC_HEADER,
		"shortcuts": [label for label, _color in ADNOC_SHORTCUTS if frappe.db.exists("DocType", label)],
	}


def _strip_legacy_adnoc_blocks(content: list) -> list:
	"""Remove old DDC/ADNOC headers and their shortcut blocks so we can rebuild cleanly."""
	adnoc_labels = {label for label, _color in ADNOC_SHORTCUTS}
	filtered = []
	skip_shortcuts = False

	for block in content:
		if block.get("type") == "header":
			text = block.get("data", {}).get("text", "")
			if any(legacy in text for legacy in LEGACY_HEADERS) or ADNOC_HEADER in text:
				skip_shortcuts = True
				continue
			skip_shortcuts = False
			filtered.append(block)
			continue

		if skip_shortcuts and block.get("type") == "shortcut":
			shortcut_name = block.get("data", {}).get("shortcut_name")
			if shortcut_name in adnoc_labels:
				continue
			skip_shortcuts = False

		if block.get("type") == "shortcut":
			shortcut_name = block.get("data", {}).get("shortcut_name")
			if shortcut_name in adnoc_labels:
				continue

		filtered.append(block)

	return filtered


def _ensure_adnoc_section(content: list) -> list:
	shortcut_names = {
		block.get("data", {}).get("shortcut_name")
		for block in content
		if block.get("type") == "shortcut"
	}

	content.append(
		{
			"id": frappe.generate_hash(length=10),
			"type": "header",
			"data": {"text": f'<span class="h4">{ADNOC_HEADER}</span>', "col": 12},
		}
	)

	for label, _color in ADNOC_SHORTCUTS:
		if label in shortcut_names:
			continue
		if not frappe.db.exists("DocType", label):
			continue
		content.append(
			{
				"id": frappe.generate_hash(length=10),
				"type": "shortcut",
				"data": {"shortcut_name": label, "col": 3},
			}
		)

	return content
