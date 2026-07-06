frappe.ui.form.on("Invoice Delivery Acknowledgement", {
	refresh(frm) {
		if (frm.doc.sales_invoice) {
			frm.add_custom_button(__("Sales Invoice"), () => {
				frappe.set_route("Form", "Sales Invoice", frm.doc.sales_invoice);
			});
		}
	},
});
