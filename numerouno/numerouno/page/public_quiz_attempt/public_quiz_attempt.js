frappe.pages['public-quiz-attempt'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Public Quiz Attempt',
		single_column: true
	});
}