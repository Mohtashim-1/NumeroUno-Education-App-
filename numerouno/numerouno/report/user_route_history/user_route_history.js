// Copyright (c) 2026, mohtashim and contributors
// For license information, please see license.txt

frappe.query_reports["User Route History"] = {
	filters: [
		{
			fieldname: "view_mode",
			label: __("View Mode"),
			fieldtype: "Select",
			options: ["Detail", "Summary"],
			default: "Summary",
		},
		{
			fieldname: "user",
			label: __("User"),
			fieldtype: "Link",
			options: "User",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -7),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "access_type",
			label: __("Access Type"),
			fieldtype: "Select",
			options: [
				"",
				"List",
				"Form",
				"Workspaces",
				"Report",
				"print",
			],
		},
		{
			fieldname: "accessed_item",
			label: __("Accessed Item"),
			fieldtype: "Data",
		},
		{
			fieldname: "route_contains",
			label: __("Route Contains"),
			fieldtype: "Data",
		},
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "route" && data.route) {
			return `<code>${frappe.utils.escape_html(data.route)}</code>`;
		}
		if (column.fieldname === "visit_count" && data.visit_count) {
			return `<strong>${data.visit_count}</strong>`;
		}
		return value;
	},
};
