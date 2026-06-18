frappe.ui.form.on("English Proficiency Test", {
	onload(frm) {
		if (frm.is_new() && questions_need_template(frm)) {
			load_english_template(frm);
		}
	},

	refresh(frm) {
		frm.add_custom_button(__("Load Template"), () => load_english_template(frm), __("Actions"));
		if (frm.doc.student_group && !frm.is_new()) {
			frm.add_custom_button(__("Fill from Student Group"), () => {
				frappe.call({
					method: "numerouno.numerouno.doctype.english_proficiency_test.english_proficiency_test.populate_from_student_group",
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

function load_english_template(frm) {
	const unsaved = frm.is_new() || frm.doc.name?.startsWith("new-");
	frappe.call({
		method: "numerouno.numerouno.doctype.english_proficiency_test.english_proficiency_test.load_default_template",
		args: { docname: unsaved ? null : frm.doc.name },
		freeze: true,
		callback(r) {
			if (r.exc) return;
			if (!unsaved) {
				frm.reload_doc();
				return;
			}
			apply_english_template(frm, r.message || {});
		},
	});
}

function apply_english_template(frm, data) {
	frm.doc.form_title = data.form_title;
	frm.doc.pass_percentage = data.pass_percentage;
	frm.doc.reading_title = data.reading_title;
	frm.doc.reading_passage = data.reading_passage;

	frm.clear_table("questions");
	(data.questions || []).forEach((row) => {
		frm.add_child("questions", {
			sr_no: row.sr_no,
			question: row.question,
			question_type: row.question_type,
			option_1: row.option_1 || "",
			option_2: row.option_2 || "",
			option_3: row.option_3 || "",
			option_4: row.option_4 || "",
			option_5: row.option_5 || "",
			option_6: row.option_6 || "",
		});
	});
	frm.refresh_field("questions");
	frm.refresh_field("reading_passage");
}
