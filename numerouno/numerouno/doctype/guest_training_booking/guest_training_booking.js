frappe.ui.form.on("Guest Training Booking", {
	refresh(frm) {
		if (frm.is_new()) return;
		if (frm.doc.status === "Pending") {
			frm.add_custom_button(__("Confirm booking"), () => {
				frappe.call({
					method: "numerouno.numerouno.api.guest_training_booking.staff_confirm_booking",
					args: { name: frm.doc.name },
					freeze: true,
					callback(r) {
						if (!r.exc) frm.reload_doc();
					},
				});
			}, __("Actions"));
			frm.add_custom_button(__("Reject"), () => {
				frappe.call({
					method: "numerouno.numerouno.api.guest_training_booking.staff_reject_booking",
					args: { name: frm.doc.name },
					freeze: true,
					callback(r) {
						if (!r.exc) frm.reload_doc();
					},
				});
			}, __("Actions"));
		}
	},
});
