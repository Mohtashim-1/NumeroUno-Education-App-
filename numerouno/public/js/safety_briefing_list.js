frappe.listview_settings["Safety Briefing"] = {
	onload(listview) {
		listview.page.add_inner_button(__("New Document View"), () => {
			frappe.set_route("safety-briefing-form");
		});
	},
	buttons: [
		{
			get_label() {
				return __("Document View");
			},
			get_description(doc) {
				return __("Open Word-style form for {0}", [doc.name]);
			},
			action(doc) {
				frappe.set_route("safety-briefing-form", doc.name);
			},
		},
	],
};
