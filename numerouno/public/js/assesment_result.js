// Copyright (c) 2024, Numerouno and contributors
// For license information, please see license.txt

frappe.ui.form.on('Assessment Result', {
	refresh: function(frm) {
		console.log('Assessment Result refresh called');
		console.log('frm.doc.custom_certificate:', frm.doc.custom_certificate);
		console.log('frm.doc.ocr_extracted_text:', frm.doc.ocr_extracted_text);
		console.log('frm.doc.ocr_confidence:', frm.doc.ocr_confidence);
		
		// Add OCR button if certificate is attached
		if (frm.doc.custom_certificate) {
			console.log('Adding OCR button - certificate found');
			frm.add_custom_button(__('Extract Text (OCR)'), function() {
				console.log('OCR button clicked');
				extract_certificate_text(frm);
			}, __('Actions'));
		} else {
			console.log('No certificate found - OCR button not added');
		}
		
		// Show OCR data if available
		if (frm.doc.ocr_extracted_text) {
			console.log('Showing OCR data - text found');
			show_ocr_data(frm);
		} else {
			console.log('No OCR data to show');
		}
	},
	
	onload: function(frm) {
		console.log('Assessment Result onload called');
		console.log('frm.doc.custom_certificate:', frm.doc.custom_certificate);
	},
	
	custom_certificate: function(frm) {
		// Clear OCR data when certificate changes
		if (frm.doc.custom_certificate) {
			frm.set_value('ocr_extracted_text', '');
			frm.set_value('ocr_confidence', 0);
		}
	}
});

function extract_certificate_text(frm) {
	console.log('extract_certificate_text called');
	console.log('frm.doc.custom_certificate:', frm.doc.custom_certificate);
	console.log('frm.doc.name:', frm.doc.name);
	
	if (!frm.doc.custom_certificate) {
		console.log('No certificate found - showing error message');
		frappe.msgprint(__('Please attach a certificate image first.'));
		return;
	}
	
	console.log('Calling OCR API...');
	frappe.call({
		method: 'numerouno.numerouno.utils.ocr_utils.process_certificate_ocr',
		args: {
			doctype: 'Assessment Result',
			docname: frm.doc.name,
			field_name: 'custom_certificate'
		},
		callback: function(r) {
			console.log('OCR API response:', r);
			console.log('r.message:', r.message);
			
			if (r.message && r.message.success) {
				console.log('OCR successful - updating form');
				console.log('Extracted text:', r.message.extracted_text);
				console.log('Confidence:', r.message.confidence);
				
				// Update the form with OCR data
				frm.set_value('ocr_extracted_text', r.message.extracted_text);
				frm.set_value('ocr_confidence', r.message.confidence);
				
				// Show success message with extracted data
				let message = 'OCR processing completed successfully!';
				if (r.message.extracted_data) {
					message += '\n\nExtracted Data:';
					if (r.message.extracted_data.opito_learner_no) {
						message += `\n• OPITO Learner No: ${r.message.extracted_data.opito_learner_no}`;
					}
					if (r.message.extracted_data.unique_certificate_no) {
						message += `\n• Unique Certificate No: ${r.message.extracted_data.unique_certificate_no}`;
					}
					if (r.message.extracted_data.expiry_date) {
						message += `\n• Expiry Date: ${r.message.extracted_data.expiry_date}`;
					}
				}
				
				frappe.show_alert({
					message: message,
					indicator: 'green'
				});
				
				// Refresh the form to show the new data
				frm.refresh();
			} else {
				console.log('OCR failed:', r.message);
				frappe.msgprint({
					title: __('OCR Error'),
					message: r.message ? r.message.message : __('Failed to process OCR'),
					indicator: 'red'
				});
			}
		},
		error: function(err) {
			console.log('OCR API error:', err);
			frappe.msgprint({
				title: __('Error'),
				message: __('Failed to process OCR: ') + err.message,
				indicator: 'red'
			});
		}
	});
}

function show_ocr_data(frm) {
	// Create a custom HTML to display OCR data
	let ocr_html = `
		<div class="ocr-data-display" style="margin-top: 10px; padding: 10px; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px;">
			<h6 style="margin-bottom: 10px; color: #495057;">
				<i class="fa fa-eye"></i> OCR Extracted Text 
				<span class="badge badge-info" style="margin-left: 5px;">Confidence: ${frm.doc.ocr_confidence || 0}%</span>
			</h6>
			<div style="max-height: 200px; overflow-y: auto; background: white; padding: 10px; border: 1px solid #e9ecef; border-radius: 3px;">
				<pre style="white-space: pre-wrap; font-family: inherit; margin: 0; font-size: 12px;">${frm.doc.ocr_extracted_text || 'No text extracted'}</pre>
			</div>
		</div>
	`;
	
	// Add the OCR data display to the form
	let ocr_field = frm.fields_dict.ocr_extracted_text;
	if (ocr_field && ocr_field.$wrapper) {
		ocr_field.$wrapper.find('.ocr-data-display').remove(); // Remove existing display
		ocr_field.$wrapper.append(ocr_html);
	}
}

// Debug function that can be called from browser console
window.debug_ocr = function() {
	console.log('=== OCR DEBUG INFO ===');
	console.log('Current form:', frappe.get_cur_frm());
	console.log('Custom certificate field:', frappe.get_cur_frm().doc.custom_certificate);
	console.log('OCR extracted text:', frappe.get_cur_frm().doc.ocr_extracted_text);
	console.log('OCR confidence:', frappe.get_cur_frm().doc.ocr_confidence);
	console.log('Form fields:', Object.keys(frappe.get_cur_frm().fields_dict));
	console.log('========================');
};

// Test OCR function that can be called from browser console
window.test_ocr = function() {
	console.log('Testing OCR function...');
	const frm = frappe.get_cur_frm();
	if (frm && frm.doc.custom_certificate) {
		console.log('Certificate found, calling OCR...');
		extract_certificate_text(frm);
	} else {
		console.log('No certificate found or form not loaded');
	}
};
