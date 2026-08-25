frappe.listview_settings["HABC2 Examination Declaration"] = {
	onload(listview) {
		listview.page.add_inner_button(__("Form View"), () => {
			frappe.set_route("habc2-examination-form");
		});
	},
	buttons: [
		{
			show(doc) {
				return !doc.__islocal;
			},
			get_label() {
				return __("Form View");
			},
			action(doc) {
				frappe.set_route("habc2-examination-form", doc.name);
			},
		},
	],
};
