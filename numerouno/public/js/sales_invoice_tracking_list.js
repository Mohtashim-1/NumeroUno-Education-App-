frappe.listview_settings["Sales Invoice Tracking"] = {
	onload() {
		frappe.set_route("invoice-print-tracker");
	},
};
