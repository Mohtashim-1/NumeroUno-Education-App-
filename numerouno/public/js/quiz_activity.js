// Copyright (c) 2025, Numerouno and contributors
// Custom Quiz Activity functionality for Numerouno

frappe.ui.form.on('Quiz Activity', {
	refresh: function(frm) {
		// Add button to create Assessment Result manually.
		frm.add_custom_button(__('Create Assessment Result'), function() {
			create_assessment_result(frm);
		}, __('Actions'));

		frm.page.add_inner_button(__('Create Assessment Result'), function() {
			create_assessment_result(frm);
		});

		// Admin/System Manager can manually correct answers and re-sync score/result.
		if (can_edit_quiz_answers() && !frm.is_new() && Array.isArray(frm.doc.result) && frm.doc.result.length) {
			frm.add_custom_button(__('Update Answers & Recalculate'), function() {
				open_admin_answer_editor(frm);
			}, __('Actions'));
		}
	}
});

function can_edit_quiz_answers() {
	return frappe.user.has_role('Administrator') || frappe.user.has_role('System Manager');
}

function open_admin_answer_editor(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __('Admin Answer Correction'),
		size: 'extra-large',
		fields: [
			{
				fieldname: 'reason',
				fieldtype: 'Small Text',
				label: __('Reason'),
				reqd: 1,
				description: __('This reason will be written to comments for audit.')
			},
			{
				fieldname: 'answer_editor_html',
				fieldtype: 'HTML',
				label: __('Answer Updates')
			}
		],
		primary_action_label: __('Apply Changes'),
		primary_action(values) {
			const updates = collect_answer_updates(dialog);
			if (!updates.length) {
				frappe.msgprint(__('No answer rows found to update.'));
				return;
			}

			frappe.call({
				method: 'numerouno.numerouno.api.quiz_api.admin_update_quiz_activity_answers',
				args: {
					quiz_activity_name: frm.doc.name,
					reason: values.reason,
					updates: updates
				},
				freeze: true,
				freeze_message: __('Updating quiz answers and assessment result...'),
				callback(r) {
					const msg = r.message || {};
					if (msg.status === 'success') {
						frappe.show_alert({
							message: __('Updated: Score {0}, Status {1}', [msg.score || '-', msg.status_value || '-']),
							indicator: 'green'
						}, 7);
						dialog.hide();
						frm.reload_doc();
						return;
					}

					frappe.msgprint({
						title: __('Update Failed'),
						indicator: 'red',
						message: msg.message || __('Unable to update quiz answers.')
					});
				},
				error() {
					frappe.msgprint({
						title: __('Update Failed'),
						indicator: 'red',
						message: __('Server error while updating answers.')
					});
				}
			});
		}
	});

	dialog.fields_dict.answer_editor_html.$wrapper.html('<div class="text-muted small">Loading correct options...</div>');
	load_answer_reference_and_render(frm, dialog);
	dialog.show();
}

function load_answer_reference_and_render(frm, dialog) {
	frappe.call({
		method: 'numerouno.numerouno.api.quiz_api.get_quiz_activity_answer_reference',
		args: { quiz_activity_name: frm.doc.name },
		callback(r) {
			const message = r.message || {};
			const reference = message.reference || {};
			dialog.fields_dict.answer_editor_html.$wrapper.html(render_answer_editor_table(frm.doc.result || [], reference));
			attach_set_correct_handlers(dialog);
		},
		error() {
			dialog.fields_dict.answer_editor_html.$wrapper.html(render_answer_editor_table(frm.doc.result || [], {}));
			attach_set_correct_handlers(dialog);
		}
	});
}

function render_answer_editor_table(rows, reference) {
	const body = rows.map((row, index) => {
		const ref = reference[row.question] || {};
		const questionLabel = ref.question_text || row.question || '';
		const questionText = frappe.utils.escape_html(questionLabel);
		const selectedOption = frappe.utils.escape_html(row.selected_option || '');
		const correctOption = frappe.utils.escape_html(ref.correct_option || '-');
		const isCorrect = (row.quiz_result || '').toLowerCase() === 'correct';

		return `
			<tr data-row-name="${frappe.utils.escape_html(row.name)}">
				<td style="vertical-align:top; min-width: 240px;">${index + 1}. ${questionText}</td>
				<td><input type="text" class="form-control qa-selected-option" value="${selectedOption}"></td>
				<td>
					<div class="qa-correct-option" style="padding: 8px 10px; background: #f8f9fa; border-radius: 4px; min-height: 36px;">${correctOption}</div>
				</td>
				<td>
					<button type="button" class="btn btn-xs btn-default qa-set-correct" ${ref.correct_option ? '' : 'disabled'}>
						${__('Set Correct')}
					</button>
				</td>
				<td>
					<select class="form-control qa-quiz-result">
						<option value="Correct" ${isCorrect ? 'selected' : ''}>Correct</option>
						<option value="Wrong" ${!isCorrect ? 'selected' : ''}>Wrong</option>
					</select>
				</td>
			</tr>
		`;
	}).join('');

	return `
		<div style="max-height: 460px; overflow:auto; border: 1px solid #d1d8dd; border-radius: 6px;">
			<table class="table table-bordered" style="margin-bottom:0;">
				<thead>
					<tr>
						<th style="width: 32%;">Question</th>
						<th style="width: 24%;">Selected Option</th>
						<th style="width: 24%;">Correct Option</th>
						<th style="width: 10%;">Action</th>
						<th style="width: 10%;">Result</th>
					</tr>
				</thead>
				<tbody>${body}</tbody>
			</table>
		</div>
	`;
}

function attach_set_correct_handlers(dialog) {
	dialog.$wrapper.find('.qa-set-correct').on('click', function() {
		const $row = $(this).closest('tr');
		const correctText = ($row.find('.qa-correct-option').text() || '').trim();
		if (!correctText || correctText === '-') {
			return;
		}
		$row.find('.qa-selected-option').val(correctText);
		$row.find('.qa-quiz-result').val('Correct');
	});
}

function collect_answer_updates(dialog) {
	const updates = [];
	dialog.$wrapper.find('tr[data-row-name]').each(function() {
		const $row = $(this);
		updates.push({
			row_name: $row.attr('data-row-name'),
			selected_option: ($row.find('.qa-selected-option').val() || '').trim(),
			quiz_result: ($row.find('.qa-quiz-result').val() || 'Wrong').trim()
		});
	});
	return updates;
}

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
