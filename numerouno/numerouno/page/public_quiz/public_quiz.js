frappe.pages['public-quiz'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Public Quiz',
		single_column: true
	});
}