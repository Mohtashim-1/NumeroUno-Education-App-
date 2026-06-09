// Copyright (c) 2026, mohtashim and contributors
// For license information, please see license.txt

frappe.ui.form.on("Attendance Staff", {
	refresh(frm) {
		if (!frm.is_new() && frappe.user.has_role("HR Manager") && !frappe.user.has_role("System Manager")) {
			frm.set_df_property("employee", "read_only", 1);
		}
	},
});
