frappe.listview_settings["HABC1 Assessment Pack"] = {
	onload(listview) {
		listview.page.add_inner_button(__("Form View"), () => {
			frappe.set_route("habc1-assessment-form");
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
				frappe.set_route("habc1-assessment-form", doc.name);
			},
		},
	],
};
