frappe.ui.form.on("Pre Test ADSD", {
	onload(frm) {
		if (frm.is_new() && questions_need_template(frm)) {
			load_adsd_template(frm);
		}
	},

	refresh(frm) {
		frm.add_custom_button(__("Load Template"), () => load_adsd_template(frm), __("Actions"));
		if (frm.doc.student_group && !frm.is_new()) {
			frm.add_custom_button(__("Fill from Student Group"), () => {
				frappe.call({
					method: "numerouno.numerouno.doctype.pre_test_adsd.pre_test_adsd.populate_from_student_group",
					args: { docname: frm.doc.name, student_group: frm.doc.student_group },
					callback() { frm.reload_doc(); },
				});
			}, __("Actions"));
		}
	},
});

function questions_need_template(frm) {
	const rows = frm.doc.questions || [];
	if (!rows.length) return true;
	return !rows.some((row) => (row.question || "").trim());
}

function load_adsd_template(frm) {
	const unsaved = frm.is_new() || frm.doc.name?.startsWith("new-");
	frappe.call({
		method: "numerouno.numerouno.doctype.pre_test_adsd.pre_test_adsd.load_default_template",
		args: { docname: unsaved ? null : frm.doc.name },
		freeze: true,
		callback(r) {
			if (r.exc) return;
			if (!unsaved) {
				frm.reload_doc();
				return;
			}
			apply_adsd_template(frm, r.message || {});
		},
	});
}

function apply_adsd_template(frm, data) {
	frm.doc.course_title = data.course_title;
	frm.doc.test_name = data.test_name;
	frm.doc.total_marks = data.total_marks;

	frm.clear_table("questions");
	(data.questions || []).forEach((row) => {
		frm.add_child("questions", {
			sr_no: row.sr_no,
			question: row.question,
		});
	});
	frm.refresh_field("questions");
}
