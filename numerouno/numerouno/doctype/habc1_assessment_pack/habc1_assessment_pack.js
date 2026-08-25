frappe.ui.form.on("HABC1 Assessment Pack", {
	refresh(frm) {
		if (frm.doc.student_group && !frm.is_new()) {
			frm.add_custom_button(__("Fill from Student Group"), () => {
				frappe.call({
					method:
						"numerouno.numerouno.doctype.habc1_assessment_pack.habc1_assessment_pack.populate_from_student_group",
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
				frappe.set_route("habc1-assessment-form", frm.doc.name);
			});
		}
	},

	tutor(frm) {
		_fill_instructor_signature(frm, "tutor", "tutor_signature", "tutor_name");
	},

	assessor(frm) {
		_fill_instructor_signature(frm, "assessor", "assessor_signature", "assessor_name");
	},
});

function _fill_instructor_signature(frm, instructor_field, signature_field, name_field) {
	const instructor = frm.doc[instructor_field];
	if (!instructor) {
		return;
	}
	frappe.db.get_value("Instructor", instructor, ["instructor_name", "image"]).then((r) => {
		const msg = r && r.message;
		if (!msg) {
			return;
		}
		if (msg.instructor_name && !frm.doc[name_field]) {
			frm.set_value(name_field, msg.instructor_name);
		}
		if (msg.image && !frm.doc[signature_field]) {
			frm.set_value(signature_field, msg.image);
		}
	});
}
