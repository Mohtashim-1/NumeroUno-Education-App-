// Copyright (c) 2026, NumeroUNO and contributors
// License: MIT

frappe.ui.form.on("Payment Entry", {
	onload: function (frm) {
		frm.ignore_doctypes_on_cancel_all = frm.ignore_doctypes_on_cancel_all || [];
		if (!frm.ignore_doctypes_on_cancel_all.includes("Portal Payment Request")) {
			frm.ignore_doctypes_on_cancel_all.push("Portal Payment Request");
		}
	},
});
