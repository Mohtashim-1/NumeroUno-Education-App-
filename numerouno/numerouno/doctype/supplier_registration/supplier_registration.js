frappe.ui.form.on("Supplier Registration", {
	refresh(frm) {
		frm.clear_custom_buttons();
		if (frm.is_new()) return;

		if (frm.doc.status === "Pending Approval") {
			frm.add_custom_button(__("Approve & Create Supplier"), () => {
				frappe.confirm(
					__("Create an ERPNext Supplier from this registration and mark it Approved?"),
					() => {
						frm.call({
							doc: frm.doc,
							method: "approve_registration",
							freeze: true,
							freeze_message: __("Creating Supplier…"),
							callback(r) {
								if (!r.exc) {
									frm.reload_doc();
								}
							},
						});
					}
				);
			}).addClass("btn-primary");

			frm.add_custom_button(__("Reject"), () => {
				frappe.prompt(
					[
						{
							fieldname: "reason",
							fieldtype: "Small Text",
							label: __("Rejection Reason"),
							reqd: 1,
						},
					],
					(values) => {
						frm.call({
							doc: frm.doc,
							method: "reject_registration",
							args: { reason: values.reason },
							freeze: true,
							callback(r) {
								if (!r.exc) {
									frm.reload_doc();
								}
							},
						});
					},
					__("Reject Supplier Registration"),
					__("Reject")
				);
			});
		}

		if (frm.doc.supplier) {
			frm.add_custom_button(__("Open Supplier"), () => {
				frappe.set_route("Form", "Supplier", frm.doc.supplier);
			});
		}
	},
});
