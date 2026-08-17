frappe.ui.form.on("NYC Reassessment Checklist", {
	refresh(frm) {
		if (frm.doc.quiz_activity) {
			frm.add_custom_button(__("Open Quiz Activity"), () => {
				frappe.set_route("Form", "Quiz Activity", frm.doc.quiz_activity);
			});
		}
		if (frm.doc.assessment_result) {
			frm.add_custom_button(__("Open Assessment Result"), () => {
				frappe.set_route("Form", "Assessment Result", frm.doc.assessment_result);
			}, __("Links"));
		}
		if (frm.doc.retest_valid_until) {
			const eligible = frm.doc.retest_status === "Eligible";
			frm.dashboard.set_headline_alert(
				eligible
					? __("Retest allowed until {0}", [frappe.datetime.str_to_user(frm.doc.retest_valid_until)])
					: __("Retest period expired on {0}", [frappe.datetime.str_to_user(frm.doc.retest_valid_until)]),
				eligible ? "blue" : "red"
			);
		}
		if (!frm.doc.assessor_signature_name && frm.doc.assessor_name) {
			frm.set_value("assessor_signature_name", frm.doc.assessor_name);
		}
	},
	assessor_signature(frm) {
		if (frm.doc.assessor_signature && !frm.doc.assessor_signature_date) {
			frm.set_value("assessor_signature_date", frappe.datetime.get_today());
		}
		if (frm.doc.assessor_signature && !frm.doc.assessor_signature_name && frm.doc.assessor_name) {
			frm.set_value("assessor_signature_name", frm.doc.assessor_name);
		}
	},
});
