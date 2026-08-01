"""API for the Customer Code lookup portal."""

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import cint

from numerouno.numerouno.customer_code_setup import FIELDNAME

PORTAL_PATH = "/customer-code"
PORTAL_LABEL = "Customer Code Lookup"


@frappe.whitelist()
def lookup_customer(query: str | None = None, mode: str | None = "auto", limit: int = 12):
	"""Search customers by name or code.

	mode: auto | name | code
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in to look up customer codes."), frappe.PermissionError)

	frappe.has_permission("Customer", "read", throw=True)

	query = (query or "").strip()
	if not query:
		return {"results": [], "mode": mode or "auto"}

	mode = (mode or "auto").lower()
	if mode not in {"auto", "name", "code"}:
		mode = "auto"

	limit = max(1, min(cint(limit) or 12, 25))

	if mode == "auto":
		mode = "code" if query.isdigit() else "name"

	results = _search_by_code(query, limit) if mode == "code" else _search_by_name(query, limit)

	# Soft fallback: if code search finds nothing, try name (and vice versa)
	if not results and (mode == "code"):
		results = _search_by_name(query, limit)
		mode = "name"
	elif not results and mode == "name" and any(ch.isdigit() for ch in query):
		results = _search_by_code(query, limit)
		if results:
			mode = "code"

	return {"results": results, "mode": mode, "query": query}


def _search_by_code(query: str, limit: int) -> list[dict]:
	rows = frappe.get_all(
		"Customer",
		fields=[
			"name",
			"customer_name",
			FIELDNAME,
			"customer_group",
			"territory",
			"disabled",
		],
		filters={FIELDNAME: ["like", f"{query}%"]},
		order_by=f"`{FIELDNAME}` asc",
		limit_page_length=limit,
	)
	return [_serialize(row) for row in rows]


def _search_by_name(query: str, limit: int) -> list[dict]:
	like = f"%{query}%"
	rows = frappe.db.sql(
		f"""
		select name, customer_name, {FIELDNAME} as customer_code,
			customer_group, territory, disabled
		from `tabCustomer`
		where customer_name like %(like)s or name like %(like)s
		order by
			case
				when {FIELDNAME} = %(exact)s then 0
				when customer_name like %(starts)s then 1
				else 2
			end,
			customer_name asc
		limit %(limit)s
		""",
		{
			"like": like,
			"exact": query,
			"starts": f"{query}%",
			"limit": limit,
		},
		as_dict=True,
	)
	return [_serialize(row) for row in rows]


def _serialize(row) -> dict:
	code = row.get(FIELDNAME) or row.get("customer_code") or ""
	return {
		"name": row.get("name"),
		"customer_name": row.get("customer_name") or row.get("name"),
		"customer_code": code,
		"customer_group": row.get("customer_group") or "",
		"territory": row.get("territory") or "",
		"disabled": cint(row.get("disabled")),
		"url": f"/app/customer/{row.get('name')}",
	}


def setup_workspace_link(workspace_name: str = "Selling"):
	"""Add a Selling workspace shortcut to the lookup portal."""
	if not frappe.db.exists("Workspace", workspace_name):
		workspace_name = "Forms"
	if not frappe.db.exists("Workspace", workspace_name):
		return {"workspace": None, "added": False}

	workspace = frappe.get_doc("Workspace", workspace_name)
	existing = {row.label for row in workspace.shortcuts}
	added = False
	if PORTAL_LABEL not in existing:
		workspace.append(
			"shortcuts",
			{
				"type": "URL",
				"url": PORTAL_PATH,
				"label": PORTAL_LABEL,
				"color": "Teal",
				"doc_view": "",
			},
		)
		added = True

	content = json.loads(workspace.content or "[]")
	names = {
		block.get("data", {}).get("shortcut_name")
		for block in content
		if block.get("type") == "shortcut"
	}
	if PORTAL_LABEL not in names:
		content.append(
			{
				"id": frappe.generate_hash(length=10),
				"type": "shortcut",
				"data": {"shortcut_name": PORTAL_LABEL, "col": 3},
			}
		)
		workspace.content = json.dumps(content)
		added = True

	if added:
		workspace.save(ignore_permissions=True)
		frappe.db.commit()
	return {"workspace": workspace_name, "added": added, "url": PORTAL_PATH}
