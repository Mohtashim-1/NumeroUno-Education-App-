frappe.ui.form.on("LV Practical Assessment", {
	onload(frm) {
		if (frm.is_new() && !(frm.doc.criteria || []).length) {
			load_lv_template(frm);
		}
	},

	refresh(frm) {
		frm.add_custom_button(__("Load Template"), () => load_lv_template(frm), __("Actions"));
		if (frm.doc.student_group && !frm.is_new()) {
			frm.add_custom_button(__("Fill from Student Group"), () => {
				frappe.call({
					method:
						"numerouno.numerouno.doctype.lv_practical_assessment.lv_practical_assessment.populate_from_student_group",
					args: { docname: frm.doc.name, student_group: frm.doc.student_group },
					callback() {
						frm.reload_doc();
					},
				});
			}, __("Actions"));
		}
		if (!frm.is_new()) {
			frm.add_custom_button(__("Open Simple Form"), () => {
				frappe.set_route("lv-practical-assessment-form", frm.doc.name);
			}, __("Actions"));
		}
	},

	student(frm) {
		if (!frm.doc.student || frm.doc.candidate_name) return;
		frappe.db.get_value("Student", frm.doc.student, "student_name").then((r) => {
			if (r && r.message) {
				frm.set_value("candidate_name", r.message.student_name || r.message);
			}
		});
	},
});

function load_lv_template(frm) {
	const unsaved = frm.is_new() || frm.doc.name?.startsWith("new-");
	frappe.call({
		method: "numerouno.numerouno.lv_practical_assessment_setup.get_template_rows",
		freeze: true,
		callback(r) {
			if (r.exc) return;
			const data = r.message || {};
			if (data.form_title) frm.set_value("form_title", data.form_title);
			if (data.form_subtitle) frm.set_value("form_subtitle", data.form_subtitle);
			if (!frm.doc.assessment_date) frm.set_value("assessment_date", frappe.datetime.get_today());
			frm.clear_table("criteria");
			(data.criteria || []).forEach((row) => {
				frm.add_child("criteria", row);
			});
			frm.refresh_field("criteria");

			if (!unsaved) {
				frm.save();
			}
		},
	});
}
