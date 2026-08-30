frappe.ui.form.on("Training Candidate", {
	customer(frm) {
		if (frm.doc.customer && !frm.doc.customer_name) {
			frappe.db.get_value("Customer", frm.doc.customer, "customer_name", (r) => {
				if (r && r.customer_name) frm.set_value("customer_name", r.customer_name);
			});
		}
	},
});
