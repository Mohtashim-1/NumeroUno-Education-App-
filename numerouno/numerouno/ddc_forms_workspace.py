"""Add ADNOC instructor forms to the Forms workspace."""

import json

import frappe

WORKSPACE = "Forms"
ADNOC_HEADER = "ADNOC"
LEGACY_HEADERS = ("DDC Instructor Course", "ADNOC DDC Instructor Course")

# ADNOC DDC Instructor Development Course forms (link_to, color, display label)
ADNOC_SHORTCUTS = (
	("DDC Candidate Prerequisite", "Green", "DDC Candidate Pre-Requisite Checklist"),
	("DDC Written Assessment", "Blue", "DDC Written Assessment"),
	("DDC OMR Answer Sheet", "Orange", "DDC OMR Answer Sheet"),
	("DDC Practical Assessment", "Red", "DDC Practical Assessment"),
	("DDC Micro Teaching Assessment", "Purple", "DDC Micro Teaching Assessment"),
	("Pre Test ADSD", "Cyan", "Pre Test ADSD"),
)


def setup():
	workspace = frappe.get_doc("Workspace", WORKSPACE)
	existing_by_link = {row.link_to: row for row in workspace.shortcuts}

	for link_to, color, display_label in ADNOC_SHORTCUTS:
		if not frappe.db.exists("DocType", link_to):
			continue
		row = existing_by_link.get(link_to)
		if row:
			row.label = display_label
			row.color = color
			continue
		workspace.append(
			"shortcuts",
			{
				"type": "DocType",
				"link_to": link_to,
				"doc_view": "List",
				"label": display_label,
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
		"shortcuts": [
			display_label
			for link_to, _color, display_label in ADNOC_SHORTCUTS
			if frappe.db.exists("DocType", link_to)
		],
	}


def _strip_legacy_adnoc_blocks(content: list) -> list:
	"""Remove old DDC/ADNOC headers and their shortcut blocks so we can rebuild cleanly."""
	adnoc_shortcut_names = {
		display_label for _link_to, _color, display_label in ADNOC_SHORTCUTS
	} | {link_to for link_to, _color, _display_label in ADNOC_SHORTCUTS}
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
			if shortcut_name in adnoc_shortcut_names:
				continue
			skip_shortcuts = False

		if block.get("type") == "shortcut":
			shortcut_name = block.get("data", {}).get("shortcut_name")
			if shortcut_name in adnoc_shortcut_names:
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

	for link_to, _color, display_label in ADNOC_SHORTCUTS:
		if display_label in shortcut_names:
			continue
		if not frappe.db.exists("DocType", link_to):
			continue
		content.append(
			{
				"id": frappe.generate_hash(length=10),
				"type": "shortcut",
				"data": {"shortcut_name": display_label, "col": 3},
			}
		)

	return content
