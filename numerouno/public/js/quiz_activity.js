// Copyright (c) 2025, Numerouno and contributors
// Custom Quiz Activity functionality for Numerouno

frappe.ui.form.on('Quiz Activity', {
	refresh: function(frm) {
		// Add button to create Assessment Result manually
		// Show button for submitted Quiz Activities (docstatus === 1)
		// if (frm.doc.docstatus === 1 && !frm.is_new()) {
			// Add button in Actions menu
			frm.add_custom_button(__('Create Assessment Result'), function() {
				create_assessment_result(frm);
			}, __('Actions'));
			
			// Also add it as a primary action button (more visible)
			frm.page.add_inner_button(__('Create Assessment Result'), function() {
				create_assessment_result(frm);
			});
		// }
	}
});

function create_assessment_result(frm) {
	frappe.confirm(
		__('Do you want to create an Assessment Result for this Quiz Activity?'),
		function() {
			// Yes
			frappe.call({
				method: 'numerouno.numerouno.api.quiz_api.create_assessment_result_from_quiz_activity',
				args: {
					quiz_activity_name: frm.doc.name
				},
				freeze: true,
				freeze_message: __('Creating Assessment Result...'),
				callback: function(r) {
					if (r.message) {
						if (r.message.status === 'success') {
							frappe.show_alert({
								message: __('Assessment Result created: {0}', [r.message.assessment_result_id]),
								indicator: 'green'
							}, 5);
							// Reload form to show new comment
							frm.reload_doc();
						} else if (r.message.status === 'info') {
							frappe.show_alert({
								message: r.message.message,
								indicator: 'blue'
							}, 5);
						} else {
							frappe.show_alert({
								message: r.message.message || __('Failed to create Assessment Result'),
								indicator: 'red'
							}, 10);
							// Reload form to show error comment
							frm.reload_doc();
						}
					}
				},
				error: function(r) {
					frappe.show_alert({
						message: __('Error: {0}', [r.message || 'Unknown error']),
						indicator: 'red'
					}, 10);
				}
			});
		},
		function() {
			// No
		}
	);
}

