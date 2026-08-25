frappe.ui.form.on("HABC2 Examination Declaration", {
	refresh(frm) {
		if (frm.doc.student_group && !frm.is_new()) {
			frm.add_custom_button(__("Fill from Student Group"), () => {
				frappe.call({
					method:
						"numerouno.numerouno.doctype.habc2_examination_declaration.habc2_examination_declaration.populate_from_student_group",
					args: { docname: frm.doc.name, student_group: frm.doc.student_group },
					freeze: true,
					callback() {
						frm.reload_doc();
					},
				});
			}, __("Actions"));
		}
		if (!frm.is_new()) {
			frm.add_custom_button(__("Open Form View"), () => {
				frappe.set_route("habc2-examination-form", frm.doc.name);
			});
		}
	},

	student_group(frm) {
		if (!frm.doc.student_group) return;
		if (!frm.doc.nominated_tutor) {
			frappe.db
				.get_value("Student Group Instructor", { parent: frm.doc.student_group }, "instructor")
				.then((r) => {
					const instructor = r && r.message && r.message.instructor;
					if (instructor) {
						frm.set_value("nominated_tutor", instructor);
					}
				});
		}
	},
});
