# Copyright (c) 2026, mohtashim and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate


def execute(filters=None):
	filters = filters or {}
	view_mode = (filters.get("view_mode") or "Detail").strip()

	if view_mode == "Summary":
		return get_summary_columns(), get_summary_data(filters)

	return get_detail_columns(), get_detail_data(filters)


def get_detail_columns():
	return [
		{
			"fieldname": "accessed_on",
			"label": _("Accessed On"),
			"fieldtype": "Datetime",
			"width": 170,
		},
		{
			"fieldname": "user",
			"label": _("User"),
			"fieldtype": "Link",
			"options": "User",
			"width": 160,
		},
		{
			"fieldname": "full_name",
			"label": _("Full Name"),
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"fieldname": "access_type",
			"label": _("Access Type"),
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"fieldname": "accessed_item",
			"label": _("Accessed Item"),
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"fieldname": "view_type",
			"label": _("View"),
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"fieldname": "document",
			"label": _("Document"),
			"fieldtype": "Dynamic Link",
			"options": "accessed_item",
			"width": 160,
		},
		{
			"fieldname": "route",
			"label": _("Route"),
			"fieldtype": "Data",
			"width": 260,
		},
	]


def get_summary_columns():
	return [
		{
			"fieldname": "user",
			"label": _("User"),
			"fieldtype": "Link",
			"options": "User",
			"width": 160,
		},
		{
			"fieldname": "full_name",
			"label": _("Full Name"),
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"fieldname": "access_type",
			"label": _("Access Type"),
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"fieldname": "accessed_item",
			"label": _("Accessed Item"),
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"fieldname": "view_type",
			"label": _("View"),
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"fieldname": "route",
			"label": _("Route"),
			"fieldtype": "Data",
			"width": 260,
		},
		{
			"fieldname": "visit_count",
			"label": _("Visits"),
			"fieldtype": "Int",
			"width": 90,
		},
		{
			"fieldname": "last_accessed_on",
			"label": _("Last Accessed On"),
			"fieldtype": "Datetime",
			"width": 170,
		},
	]


def _build_conditions(filters):
	conditions = ["rh.route IS NOT NULL", "rh.route != ''"]
	values = {}

	if filters.get("user"):
		conditions.append("rh.user = %(user)s")
		values["user"] = filters["user"]

	if filters.get("from_date"):
		conditions.append("DATE(COALESCE(rh.creation, rh.modified)) >= %(from_date)s")
		values["from_date"] = getdate(filters["from_date"])

	if filters.get("to_date"):
		conditions.append("DATE(COALESCE(rh.creation, rh.modified)) <= %(to_date)s")
		values["to_date"] = getdate(filters["to_date"])

	if filters.get("route_contains"):
		conditions.append("rh.route LIKE %(route_contains)s")
		values["route_contains"] = f"%{filters['route_contains'].strip()}%"

	if filters.get("access_type"):
		if filters["access_type"] == "Report":
			conditions.append("rh.route LIKE 'query-report/%'")
		else:
			conditions.append("rh.route LIKE %(access_type)s")
			values["access_type"] = f"{filters['access_type']}/%"

	if filters.get("accessed_item"):
		conditions.append("rh.route LIKE %(accessed_item)s")
		values["accessed_item"] = f"%/{filters['accessed_item'].strip()}%"

	return conditions, values


def get_detail_data(filters):
	conditions, values = _build_conditions(filters)

	rows = frappe.db.sql(
		f"""
		SELECT
			COALESCE(rh.creation, rh.modified) AS accessed_on,
			rh.user,
			u.full_name,
			rh.route
		FROM `tabRoute History` rh
		LEFT JOIN `tabUser` u ON u.name = rh.user
		WHERE {" AND ".join(conditions)}
		ORDER BY COALESCE(rh.creation, rh.modified) DESC
		LIMIT 5000
		""",
		values,
		as_dict=True,
	)

	for row in rows:
		parsed = parse_route(row.route)
		row.update(parsed)

	return rows


def get_summary_data(filters):
	conditions, values = _build_conditions(filters)

	rows = frappe.db.sql(
		f"""
		SELECT
			rh.user,
			u.full_name,
			rh.route,
			COUNT(*) AS visit_count,
			MAX(COALESCE(rh.creation, rh.modified)) AS last_accessed_on
		FROM `tabRoute History` rh
		LEFT JOIN `tabUser` u ON u.name = rh.user
		WHERE {" AND ".join(conditions)}
		GROUP BY rh.user, rh.route
		ORDER BY visit_count DESC, last_accessed_on DESC
		LIMIT 2000
		""",
		values,
		as_dict=True,
	)

	for row in rows:
		parsed = parse_route(row.route)
		row.update(parsed)

	return rows


def parse_route(route):
	route = (route or "").strip()
	parts = route.split("/")
	access_type = parts[0] if parts else ""
	accessed_item = ""
	view_type = ""
	document = ""

	if access_type == "List" and len(parts) >= 2:
		accessed_item = parts[1]
		view_type = parts[2] if len(parts) > 2 else ""
	elif access_type == "Form" and len(parts) >= 3:
		accessed_item = parts[1]
		document = parts[2]
	elif access_type == "Workspaces" and len(parts) >= 2:
		accessed_item = parts[1]
	elif access_type == "query-report" and len(parts) >= 2:
		access_type = "Report"
		accessed_item = "/".join(parts[1:])
	elif access_type == "print" and len(parts) >= 2:
		accessed_item = parts[1]
		document = parts[2] if len(parts) > 2 else ""
	elif len(parts) >= 2:
		accessed_item = parts[1]
		document = parts[2] if len(parts) > 2 else ""
	elif len(parts) == 1 and parts[0]:
		accessed_item = parts[0]

	return {
		"access_type": access_type,
		"accessed_item": accessed_item,
		"view_type": view_type,
		"document": document,
	}
