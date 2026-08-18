"""Register Student PDF Bundle page shortcut on Forms workspace."""

from __future__ import annotations

import frappe

WORKSPACE = "Forms"
PAGE = "student-pdf-bundle"
SHORTCUT_LABEL = "Student PDF Bundle"


def setup():
	_ensure_workspace()
	frappe.db.commit()
	return {"page": PAGE, "workspace": WORKSPACE}


def _ensure_workspace():
	if not frappe.db.exists("Workspace", WORKSPACE):
		return

	workspace = frappe.get_doc("Workspace", WORKSPACE)
	existing = {row.link_to for row in workspace.shortcuts if row.type == "Page"}
	if PAGE in existing:
		return

	workspace.append(
		"shortcuts",
		{
			"type": "Page",
			"link_to": PAGE,
			"label": SHORTCUT_LABEL,
			"color": "Blue",
			"doc_view": "",
			"format": "",
		},
	)
	workspace.save(ignore_permissions=True)
