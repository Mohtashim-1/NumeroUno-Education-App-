frappe.ui.form.on("ROSPA Learning Outcome Assessment", {
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
						"numerouno.numerouno.doctype.rospa_learning_outcome_assessment.rospa_learning_outcome_assessment.populate_from_student_group",
					args: { docname: frm.doc.name, student_group: frm.doc.student_group },
					callback() {
						frm.reload_doc();
					},
				});
			}, __("Actions"));
		}
		if (!frm.is_new()) {
			frm.add_custom_button(__("Open Simple Form"), () => {
				frappe.set_route("rospa-learning-outcome-form", frm.doc.name);
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

	student_group(frm) {
		if (frm.doc.assessor || !frm.doc.student_group) return;
		frappe.db.get_value("Student Group Instructor", { parent: frm.doc.student_group }, "instructor").then((r) => {
			const instructor = r && r.message && r.message.instructor;
			if (instructor) {
				frm.set_value("assessor", instructor);
			}
		});
	},

	assessor(frm) {
		if (!frm.doc.assessor) return;
		frappe.db.get_value("Instructor", frm.doc.assessor, ["instructor_name", "image"]).then((r) => {
			const msg = r && r.message;
			if (!msg) return;
			if (msg.instructor_name) {
				frm.set_value("assessor_name", msg.instructor_name);
			}
			if (msg.image && !frm.doc.assessor_signature) {
				frm.set_value("assessor_signature", msg.image);
			}
		});
	},
});

function load_lv_template(frm) {
	const unsaved = frm.is_new() || frm.doc.name?.startsWith("new-");
	frappe.call({
		method: "numerouno.numerouno.rospa_learning_outcome_setup.get_template_rows",
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
