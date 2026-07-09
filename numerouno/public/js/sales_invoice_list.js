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
