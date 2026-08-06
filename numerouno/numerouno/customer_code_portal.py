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


ROLE = "Customer Code Lookup"
WORKSPACE = "Customer Code"

# Staff who should use the lookup portal
ACCESS_USERS = (
	"tenorio.j@numerouno-me.com",  # Jeselle / Jessel
	"a.sravon@numerouno-me.com",  # Afsana
	"f.kaneez@numerouno-me.com",  # Fatima Kaneez
	"s.arshad@numerouno-me.com",  # Syed / Seyad Arshad
	"j.jeyakumar@numerouno-me.com",  # Jebisha
	"m.soortee@numerouno-me.com",  # Mahmood
	"j.carlo@numerouno-me.com",  # Jan Carlo
	"kumar.v@numerouno-me.com",  # Vijay
	"t.anwar@numerouno-me.com",  # Thanooja
	"m.mashood@numerouno-me.com",  # Minhaj
)


def setup_access():
	"""Create role + workspace, grant users, keep Selling shortcut."""
	ensure_role()
	ensure_customer_permission()
	workspace = ensure_workspace()
	selling = setup_workspace_link("Selling")
	granted = grant_users(ACCESS_USERS)
	frappe.clear_cache()
	frappe.db.commit()
	return {
		"role": ROLE,
		"workspace": workspace,
		"selling": selling,
		"granted": granted,
		"url": PORTAL_PATH,
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


def ensure_customer_permission():
	"""Allow the role to read/select Customer for the lookup API."""
	existing = frappe.db.exists(
		"Custom DocPerm",
		{"parent": "Customer", "role": ROLE, "permlevel": 0},
	)
	if existing:
		doc = frappe.get_doc("Custom DocPerm", existing)
		doc.read = 1
		doc.select = 1
		doc.save(ignore_permissions=True)
		return

	frappe.get_doc(
		{
			"doctype": "Custom DocPerm",
			"parent": "Customer",
			"parenttype": "DocType",
			"parentfield": "permissions",
			"role": ROLE,
			"permlevel": 0,
			"read": 1,
			"select": 1,
		}
	).insert(ignore_permissions=True)


def ensure_workspace():
	content = [
		{
			"id": frappe.generate_hash(length=10),
			"type": "header",
			"data": {"text": f'<span class="h4">{PORTAL_LABEL}</span>', "col": 12},
		},
		{
			"id": frappe.generate_hash(length=10),
			"type": "shortcut",
			"data": {"shortcut_name": PORTAL_LABEL, "col": 4},
		},
	]

	if frappe.db.exists("Workspace", WORKSPACE):
		workspace = frappe.get_doc("Workspace", WORKSPACE)
	else:
		workspace = frappe.new_doc("Workspace")
		workspace.name = WORKSPACE
		workspace.label = WORKSPACE
		workspace.title = WORKSPACE
		workspace.public = 1
		workspace.icon = "id-card"
		workspace.indicator_color = "cyan"

	workspace.public = 1
	workspace.is_hidden = 0
	workspace.content = json.dumps(content)

	# shortcut row
	labels = {row.label for row in workspace.shortcuts}
	if PORTAL_LABEL not in labels:
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

	# restrict workspace to this role
	workspace.set("roles", [])
	workspace.append("roles", {"role": ROLE})

	if workspace.is_new():
		workspace.insert(ignore_permissions=True)
	else:
		workspace.save(ignore_permissions=True)
	return WORKSPACE


def grant_users(emails):
	granted = []
	missing = []
	for email in emails:
		if not frappe.db.exists("User", email):
			missing.append(email)
			continue
		user = frappe.get_doc("User", email)
		if not user.enabled:
			user.enabled = 1
		roles = {r.role for r in user.roles}
		if ROLE not in roles:
			user.append("roles", {"role": ROLE})
			user.save(ignore_permissions=True)
		granted.append({"email": email, "full_name": user.full_name})
	return {"users": granted, "missing": missing}


def setup_workspace_link(workspace_name: str = "Selling"):
	"""Add a workspace shortcut to the lookup portal."""
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
	return {"workspace": workspace_name, "added": added, "url": PORTAL_PATH}
