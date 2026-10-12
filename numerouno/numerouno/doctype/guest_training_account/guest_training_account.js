frappe.ui.form.on("Guest Training Account", {
	refresh(frm) {
		if (frm.doc.status === "Pending" && !frm.is_new()) {
			frm.add_custom_button(__("Approve"), () => {
				frm.set_value("status", "Approved");
				frm.save();
			}, __("Actions"));
			frm.add_custom_button(__("Reject"), () => {
				frm.set_value("status", "Rejected");
				frm.save();
			}, __("Actions"));
		}
	},
});
