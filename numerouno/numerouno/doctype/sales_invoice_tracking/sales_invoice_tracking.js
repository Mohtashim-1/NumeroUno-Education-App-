frappe.ui.form.on("Sales Invoice Tracking", {
	setup(frm) {
		frm.set_query("invoice_number", () => ({
			filters: { docstatus: 1 },
		}));
	},
});
