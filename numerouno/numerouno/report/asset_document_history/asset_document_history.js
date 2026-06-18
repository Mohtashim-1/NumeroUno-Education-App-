// Copyright (c) 2026, mohtashim and contributors
// For license information, please see license.txt

frappe.query_reports["Asset Document History"] = {
	filters: [
		{
			fieldname: "asset",
			label: __("Asset"),
			fieldtype: "Link",
			options: "Asset",
		},
		{
			fieldname: "asset_category",
			label: __("Asset Category"),
			fieldtype: "Link",
			options: "Asset Category",
		},
		{
			fieldname: "location",
			label: __("Location"),
			fieldtype: "Link",
			options: "Location",
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
		},
		{
			fieldname: "document_type",
			label: __("Document Type"),
			fieldtype: "Select",
			options: [
				"",
				"Agreement",
				"Insurance",
				"Registration",
				"Compliance Certificate",
				"Inspection Report",
				"Vendor Contract",
			],
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: ["", "Current", "Archived"],
		},
		{
			fieldname: "from_date",
			label: __("Archived From"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("Archived To"),
			fieldtype: "Date",
		},
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "document" && data.document) {
			const url = frappe.urllib.get_full_url(data.document);
			return `<a href="${url}" target="_blank" rel="noopener">${__("View Document")}</a>`;
		}
		if (column.fieldname === "status" && data.status) {
			const cls = data.status === "Current" ? "green" : "orange";
			return `<span class="indicator-pill ${cls} filterable">${frappe.utils.escape_html(data.status)}</span>`;
		}
		return value;
	},
};
