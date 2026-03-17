import json

import frappe


BLOCK_NAME = "Laundries Quick Links"
WORKSPACE_NAME = "Laundries"


def add_custom_block_to_laundries_workspace():
	workspace = ensure_workspace()
	ensure_custom_block()
	ensure_workspace_block_link(workspace)
	ensure_workspace_content(workspace)
	frappe.db.commit()

	return {
		"status": "success",
		"workspace": WORKSPACE_NAME,
		"custom_block": BLOCK_NAME,
	}


def ensure_workspace():
	if frappe.db.exists("Workspace", WORKSPACE_NAME):
		return frappe.get_doc("Workspace", WORKSPACE_NAME)

	workspace = frappe.new_doc("Workspace")
	workspace.name = WORKSPACE_NAME
	workspace.label = WORKSPACE_NAME
	workspace.title = WORKSPACE_NAME
	workspace.public = 1
	workspace.content = json.dumps([{"type": "header", "data": {"text": WORKSPACE_NAME}}])
	workspace.insert(ignore_permissions=True)
	return workspace


def ensure_custom_block():
	if frappe.db.exists("Custom HTML Block", BLOCK_NAME):
		block = frappe.get_doc("Custom HTML Block", BLOCK_NAME)
	else:
		block = frappe.new_doc("Custom HTML Block")
		block.name = BLOCK_NAME
		block.private = 0

	block.html = """
<div class="laundries-workspace-block" style="padding: 22px;">
	<div style="display:flex; flex-wrap:wrap; justify-content:space-between; gap:18px; align-items:flex-start; margin-bottom:18px;">
		<div>
			<h3 style="margin:0 0 8px; color:#0f172a; font-size:22px; font-weight:700;">Laundry Control Center</h3>
			<p style="margin:0; color:#475467; line-height:1.7; max-width:700px;">
				Track daily laundry IN and OUT transactions, review missing quantities, and jump directly to the dashboard or new entry form.
			</p>
		</div>
		<a href="/app/laundry-dashboard" style="display:inline-flex; align-items:center; justify-content:center; padding:12px 18px; border-radius:12px; background:#2563eb; color:#fff; text-decoration:none; font-weight:700;">
			Open Laundry Dashboard
		</a>
	</div>
	<div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(210px, 1fr)); gap:14px;">
		<a href="/app/laundry-dashboard" style="display:block; padding:16px; border-radius:14px; border:1px solid #bfd5ff; background:#eef4ff; color:#1d4ed8; text-decoration:none;">
			<div style="font-size:13px; opacity:0.8; margin-bottom:6px;">Overview</div>
			<div style="font-size:16px; font-weight:700;">Daily Laundry Report</div>
		</a>
		<a href="/app/laundry/new-laundry" style="display:block; padding:16px; border-radius:14px; border:1px solid #c7ead8; background:#ecfdf3; color:#047857; text-decoration:none;">
			<div style="font-size:13px; opacity:0.8; margin-bottom:6px;">Entry</div>
			<div style="font-size:16px; font-weight:700;">Create Laundry Transaction</div>
		</a>
		<a href="/app/laundry" style="display:block; padding:16px; border-radius:14px; border:1px solid #f6d18b; background:#fffbeb; color:#b45309; text-decoration:none;">
			<div style="font-size:13px; opacity:0.8; margin-bottom:6px;">Records</div>
			<div style="font-size:16px; font-weight:700;">Laundry List</div>
		</a>
	</div>
</div>
"""

	block.style = """
.laundries-workspace-block a:hover {
	transform: translateY(-1px);
	box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}
"""

	if block.is_new():
		block.insert(ignore_permissions=True)
	else:
		block.save(ignore_permissions=True)


def ensure_workspace_block_link(workspace):
	for row in workspace.custom_blocks or []:
		if row.custom_block_name == BLOCK_NAME:
			return

	workspace.append(
		"custom_blocks",
		{
			"custom_block_name": BLOCK_NAME,
			"label": BLOCK_NAME,
		},
	)
	workspace.save(ignore_permissions=True)


def ensure_workspace_content(workspace):
	content = json.loads(workspace.content) if workspace.content else []
	for item in content:
		if item.get("type") == "custom_block" and item.get("data", {}).get("custom_block_name") == BLOCK_NAME:
			return

	content.insert(
		0,
		{
			"type": "custom_block",
			"data": {
				"custom_block_name": BLOCK_NAME,
				"col": 12,
			},
		},
	)
	workspace.content = json.dumps(content)
	workspace.save(ignore_permissions=True)
