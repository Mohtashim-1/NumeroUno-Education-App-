frappe.ui.form.on("Quotation", {
	before_cancel(frm) {
		return prompt_for_cancellation_reason(frm);
	},

	before_workflow_action(frm) {
		if (!frm.selected_workflow_action) {
			return;
		}

		return frappe
			.xcall("numerouno.numerouno.utils.quotation_workflow.is_cancellation_action", {
				doctype: frm.doctype,
				docname: frm.doc.name,
				action: frm.selected_workflow_action,
			})
			.then((is_cancellation_action) => {
				if (!is_cancellation_action) {
					return;
				}

				return prompt_for_cancellation_reason(frm);
			});
	},
});

function prompt_for_cancellation_reason(frm) {
	return new Promise((resolve, reject) => {
		let reason_provided = false;
		const was_frozen_for_workflow = Boolean(frm.selected_workflow_action);

		if (was_frozen_for_workflow) {
			frappe.dom.unfreeze();
		}

		const dialog = new frappe.ui.Dialog({
			title: __("Cancellation Reason"),
			fields: [
				{
					fieldname: "custom_cancellation_reason",
					fieldtype: "Small Text",
					label: __("Reason"),
					reqd: 1,
					default: frm.doc.custom_cancellation_reason || "",
				},
			],
			primary_action_label: __("Confirm"),
			primary_action(values) {
				const reason = (values.custom_cancellation_reason || "").trim();

				if (!reason) {
					frappe.msgprint(__("Please enter a cancellation reason."));
					return;
				}

				frappe
					.xcall("numerouno.numerouno.utils.quotation_workflow.save_cancellation_reason", {
						doctype: frm.doctype,
						docname: frm.doc.name,
						reason,
					})
					.then(() => frm.set_value("custom_cancellation_reason", reason))
					.then(() => {
						reason_provided = true;
						if (was_frozen_for_workflow) {
							frappe.dom.freeze();
						}
						dialog.hide();
						resolve();
					});
			},
		});

		dialog.onhide = () => {
			if (!reason_provided) {
				frappe.validated = false;
				reject();
			}
		};

		dialog.show();
	});
}
