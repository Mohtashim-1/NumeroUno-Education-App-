const dip_sales_invoice_base_settings = frappe.listview_settings["Sales Invoice"] || {};
const dip_sales_invoice_base_add_fields = Array.isArray(dip_sales_invoice_base_settings.add_fields)
	? dip_sales_invoice_base_settings.add_fields
	: [];

frappe.listview_settings["Sales Invoice"] = {
	...dip_sales_invoice_base_settings,
	add_fields: Array.from(
		new Set([...dip_sales_invoice_base_add_fields, "custom_delivery_driver", "custom_delivery_acknowledged"])
	),
	onload(listview) {
		if (typeof dip_sales_invoice_base_settings.onload === "function") {
			dip_sales_invoice_base_settings.onload(listview);
		}

		listview.page.add_inner_button(__("Quick Bulk from Student Groups"), () => {
			nutc_show_quick_bulk_invoice_dialog(() => listview.refresh());
		});

		listview.page.add_action_item(__("Assign to Driver"), () => {
			const names = listview.get_checked_items(true);
			if (!names.length) {
				frappe.msgprint(__("Select at least one submitted Sales Invoice."));
				return;
			}
			dip_show_assign_driver_dialog(names, () => listview.refresh());
		});

		listview.page.add_action_item(__("Clear Driver"), () => {
			const names = listview.get_checked_items(true);
			if (!names.length) {
				frappe.msgprint(__("Select at least one Sales Invoice."));
				return;
			}
			frappe.confirm(
				__("Clear Delivery Driver from {0} selected invoice(s)?", [names.length]),
				() => {
					frappe.call({
						method: "numerouno.numerouno.page.driver_invoice_portal.driver_invoice_portal.bulk_clear_delivery_driver",
						args: { sales_invoices: names },
						freeze: true,
						callback(r) {
							if (r.exc) return;
							const msg = r.message || {};
							frappe.show_alert({
								message: __("Cleared driver on {0} invoice(s)", [msg.updated || 0]),
								indicator: "green",
							});
							listview.refresh();
						},
					});
				}
			);
		});
	},
};

function nutc_show_quick_bulk_invoice_dialog(ondone) {
	// Shared with Sales Invoice form JS when available; keep a list-view copy as fallback.
	const dialog = new frappe.ui.Dialog({
		title: __("Quick Bulk Invoice from Student Groups"),
		fields: [
			{
				fieldtype: "HTML",
				options: `<p>${__(
					"Paste Student Group IDs (one per line). Pending students in those groups will be added to draft Sales Invoice(s)."
				)}</p>`,
			},
			{
				label: __("Student Groups"),
				fieldname: "student_groups",
				fieldtype: "Long Text",
				reqd: 1,
				description: __("Example: STD-GRP-2026-44560"),
			},
			{
				label: __("Rate"),
				fieldname: "rate",
				fieldtype: "Currency",
				reqd: 1,
				default: 1880,
			},
			{
				label: __("Customer (optional)"),
				fieldname: "customer",
				fieldtype: "Link",
				options: "Customer",
				description: __("Leave blank to auto-split by customer."),
			},
		],
		primary_action_label: __("Create Draft Invoice(s)"),
		primary_action(values) {
			frappe.call({
				method: "numerouno.numerouno.page.invoiced_creation.invoiced_creation.create_invoice_from_student_groups",
				args: {
					student_groups: values.student_groups,
					rate: values.rate,
					customer: values.customer,
				},
				freeze: true,
				freeze_message: __("Creating invoice from student groups..."),
				callback(r) {
					if (r.exc) return;
					const msg = r.message || {};
					const invoices = msg.invoices || [];
					dialog.hide();
					let note = __("{0} draft invoice(s), {1} students, {2} groups", [
						msg.invoice_count || 0,
						msg.student_count || 0,
						msg.student_group_count || 0,
					]);
					if ((msg.skipped_groups || []).length) {
						note +=
							"<br>" +
							__("Skipped (already invoiced / no pending): {0}", [
								(msg.skipped_groups || []).slice(0, 15).join(", "),
							]);
					}
					frappe.msgprint({
						title: __("Invoice Created"),
						indicator: "green",
						message: note,
					});
					if (ondone) ondone();
					if (invoices.length === 1) {
						frappe.set_route("Form", "Sales Invoice", invoices[0].sales_invoice);
					} else if (invoices.length > 1) {
						frappe.set_route("List", "Sales Invoice");
					}
				},
			});
		},
	});
	dialog.$wrapper.find(".modal-dialog").css("max-width", "720px");
	dialog.show();
}

function dip_show_assign_driver_dialog(sales_invoices, ondone) {
	const dialog = new frappe.ui.Dialog({
		title: __("Assign to Driver"),
		fields: [
			{
				fieldname: "driver",
				fieldtype: "Link",
				options: "User",
				label: __("Delivery Driver"),
				reqd: 1,
				get_query() {
					return {
						query: "numerouno.numerouno.page.driver_invoice_portal.driver_invoice_portal.get_delivery_driver_users",
					};
				},
			},
		],
		primary_action_label: __("Assign"),
		primary_action(values) {
			frappe.call({
				method: "numerouno.numerouno.page.driver_invoice_portal.driver_invoice_portal.bulk_assign_delivery_driver",
				args: {
					sales_invoices,
					driver: values.driver,
				},
				freeze: true,
				callback(r) {
					if (r.exc) return;
					const msg = r.message || {};
					let text = __("Assigned {0} invoice(s) to {1}", [msg.updated || 0, msg.driver_name || values.driver]);
					if (msg.skipped?.length) {
						text += ` (${msg.skipped.length} skipped)`;
					}
					frappe.show_alert({ message: text, indicator: "green" });
					dialog.hide();
					if (ondone) ondone();
				},
			});
		},
	});
	dialog.show();
}
