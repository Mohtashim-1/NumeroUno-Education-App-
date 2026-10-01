// Copyright (c) 2026, NumeroUNO and contributors
// License: MIT

frappe.ui.form.on("Training Date Request", {
	refresh(frm) {
		frm.clear_custom_buttons();
		if (frm.is_new()) return;

		if (frm.doc.status === "Open") {
			frm.add_custom_button(__("Accept Preferred Date"), () => {
				frappe.confirm(
					__("Accept {0} and lock this training date?", [
						frappe.datetime.str_to_user(frm.doc.preferred_date),
					]),
					() => {
						frappe.call({
							method:
								"numerouno.numerouno.api.training_date_request.accept_preferred_date",
							args: { name: frm.doc.name },
							freeze: true,
							callback: (r) => {
								if (!r.exc) {
									frm.reload_doc();
									frappe.show_alert({
										message: __("Date accepted and customer notified"),
										indicator: "green",
									});
								}
							},
						});
					}
				);
			}, __("Coordinator"));

			frm.add_custom_button(__("Propose New Date"), () => {
				const d = new frappe.ui.Dialog({
					title: __("Propose New Date"),
					fields: [
						{
							fieldname: "proposed_date",
							fieldtype: "Date",
							label: __("Proposed Date"),
							reqd: 1,
						},
						{
							fieldname: "coordinator_notes",
							fieldtype: "Small Text",
							label: __("Note to customer"),
						},
					],
					primary_action_label: __("Send Proposal"),
					primary_action(values) {
						frappe.call({
							method:
								"numerouno.numerouno.api.training_date_request.propose_new_date",
							args: {
								name: frm.doc.name,
								proposed_date: values.proposed_date,
								coordinator_notes: values.coordinator_notes,
							},
							freeze: true,
							callback: (r) => {
								if (!r.exc) {
									d.hide();
									frm.reload_doc();
									frappe.show_alert({
										message: __("Proposal sent to customer"),
										indicator: "blue",
									});
								}
							},
						});
					},
				});
				d.show();
			}, __("Coordinator"));
		}

		if (frm.doc.status === "Proposed") {
			frm.add_custom_button(__("Propose Another Date"), () => {
				const d = new frappe.ui.Dialog({
					title: __("Propose Another Date"),
					fields: [
						{
							fieldname: "proposed_date",
							fieldtype: "Date",
							label: __("Proposed Date"),
							reqd: 1,
							default: frm.doc.proposed_date,
						},
						{
							fieldname: "coordinator_notes",
							fieldtype: "Small Text",
							label: __("Note to customer"),
							default: frm.doc.coordinator_notes,
						},
					],
					primary_action_label: __("Update Proposal"),
					primary_action(values) {
						frappe.call({
							method:
								"numerouno.numerouno.api.training_date_request.propose_new_date",
							args: {
								name: frm.doc.name,
								proposed_date: values.proposed_date,
								coordinator_notes: values.coordinator_notes,
							},
							freeze: true,
							callback: (r) => {
								if (!r.exc) {
									d.hide();
									frm.reload_doc();
								}
							},
						});
					},
				});
				d.show();
			}, __("Coordinator"));
		}

		if (["Open", "Proposed"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Cancel Request"), () => {
				frappe.prompt(
					{
						fieldname: "coordinator_notes",
						fieldtype: "Small Text",
						label: __("Reason"),
					},
					(values) => {
						frappe.call({
							method:
								"numerouno.numerouno.api.training_date_request.cancel_request",
							args: {
								name: frm.doc.name,
								coordinator_notes: values.coordinator_notes,
							},
							freeze: true,
							callback: (r) => {
								if (!r.exc) frm.reload_doc();
							},
						});
					},
					__("Cancel Request"),
					__("Cancel")
				);
			}, __("Coordinator"));
		}
	},
});
