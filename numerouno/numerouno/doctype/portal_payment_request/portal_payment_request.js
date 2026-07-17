// Copyright (c) 2026, NumeroUNO and contributors
// License: MIT

frappe.ui.form.on("Portal Payment Request", {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.status === "Open") {
			frm.dashboard.set_headline_alert(
				__("Open on customer portal — customer can pay with Stripe.")
			);
		}
		if (frm.doc.docstatus === 1 && frm.doc.status === "Paid" && frm.doc.sales_invoice) {
			frm.add_custom_button(__("Allocate Payment to Invoice"), () => {
				frappe.call({
					method:
						"numerouno.numerouno.doctype.portal_payment_request.portal_payment_request.allocate_to_invoice",
					args: { name: frm.doc.name, sales_invoice: frm.doc.sales_invoice },
					freeze: true,
					callback(r) {
						frm.reload_doc();
					},
				});
			}).addClass("btn-primary");
		}
	},

	customer(frm) {
		if (frm.doc.customer) {
			frappe.db.get_value("Customer", frm.doc.customer, "customer_name", (r) => {
				if (r) frm.set_value("customer_name", r.customer_name);
			});
		}
	},

	company(frm) {
		if (frm.doc.company && !frm.doc.currency) {
			frappe.db.get_value("Company", frm.doc.company, "default_currency", (r) => {
				if (r) frm.set_value("currency", r.default_currency);
			});
		}
	},

	allocate_to_invoice(frm) {
		if (!frm.doc.sales_invoice) {
			frappe.msgprint(__("Select a Sales Invoice first."));
			return;
		}
		frappe.call({
			method:
				"numerouno.numerouno.doctype.portal_payment_request.portal_payment_request.allocate_to_invoice",
			args: { name: frm.doc.name, sales_invoice: frm.doc.sales_invoice },
			freeze: true,
			callback() {
				frm.reload_doc();
			},
		});
	},
});
