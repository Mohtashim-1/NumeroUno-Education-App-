frappe.listview_settings["Assessor Checklist"] = {
	onload(listview) {
		listview.page.add_inner_button(__("New Document View"), () => {
			frappe.set_route("course-assessor-checklist-form");
		});
	},
	buttons: [
		{
			show(doc) {
				return !doc.__islocal;
			},
			get_label() {
				return __("Document View");
			},
			get_description(doc) {
				return __("Open {0} in document layout", [doc.name]);
			},
			action(doc) {
				frappe.set_route("course-assessor-checklist-form", doc.name);
			},
		},
	],
};
