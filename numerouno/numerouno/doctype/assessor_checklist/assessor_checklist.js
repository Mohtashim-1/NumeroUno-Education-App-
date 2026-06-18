frappe.ui.form.on("Assessor Checklist", {
	onload(frm) {
		frm._assessor_checklist_template_loaded = false;
	},

	refresh(frm) {
		frm.add_custom_button(__("Load Template"), () => {
			if (!frm.doc.checklist_type) {
				frappe.msgprint(__("Select a Checklist Type first"));
				return;
			}
			const clear_existing = (frm.doc.outcomes || []).length > 0;
			if (clear_existing) {
				frappe.confirm(
					__("Replace existing checklist data with the template for {0}?", [frm.doc.checklist_type]),
					() => load_assessor_checklist_template(frm, true)
				);
			} else {
				load_assessor_checklist_template(frm, false);
			}
		}, __("Actions"));

		if (frm.doc.student_group) {
			frm.add_custom_button(__("Populate Learners from Student Group"), () => {
				populate_learners_from_student_group(frm);
			}, __("Actions"));
		}
	},

	student_group(frm) {
		if (frm.doc.student_group) {
			populate_learners_from_student_group(frm);
		} else {
			ensure_blank_learner_rows(frm);
		}
	},

	checklist_type(frm) {
		if (!frm.doc.checklist_type) return;
		if (frm._loading_assessor_checklist_template) return;

		if ((frm.doc.outcomes || []).length) {
			frappe.confirm(
				__("Load the template for {0}?", [frm.doc.checklist_type]),
				() => load_assessor_checklist_template(frm, true),
				() => frm.reload_doc()
			);
		} else {
			load_assessor_checklist_template(frm, false);
		}
	},
});

function is_unsaved_assessor_checklist(frm) {
	return frm.is_new() || (frm.doc.name && frm.doc.name.startsWith("new-"));
}

function ensure_blank_learner_rows(frm) {
	if ((frm.doc.learners || []).length >= 16) return;
	frm.clear_table("learners");
	for (let i = 1; i <= 16; i++) {
		frm.add_child("learners", { row_no: i, learner_name: "" });
	}
	frm.refresh_field("learners");
}

function populate_learners_from_student_group(frm) {
	if (!frm.doc.student_group) return;

	const unsaved = is_unsaved_assessor_checklist(frm);
	const method = unsaved
		? "numerouno.numerouno.doctype.assessor_checklist.assessor_checklist.get_learners_for_student_group"
		: "numerouno.numerouno.doctype.assessor_checklist.assessor_checklist.populate_learners_from_student_group";

	const args = unsaved
		? { student_group: frm.doc.student_group }
		: { docname: frm.doc.name, student_group: frm.doc.student_group };

	frappe.call({
		method,
		args,
		freeze: true,
		callback(r) {
			if (r.exc) return;
			if (unsaved) {
				apply_learners_to_form(frm, r.message || []);
				frappe.show_alert({ message: __("Learners loaded from Student Group"), indicator: "green" });
				return;
			}
			frm.reload_doc();
		},
	});
}

function apply_learners_to_form(frm, learners) {
	frm.clear_table("learners");
	(learners || []).forEach((row) => {
		frm.add_child("learners", {
			row_no: row.row_no,
			learner_name: row.learner_name || "",
			module_group: row.module_group || "",
		});
	});
	while ((frm.doc.learners || []).length < 16) {
		const idx = frm.doc.learners.length + 1;
		frm.add_child("learners", { row_no: idx, learner_name: "" });
	}
	frm.refresh_field("learners");
}

function load_assessor_checklist_template(frm, clear_existing) {
	if (!frm.doc.checklist_type) return;

	const unsaved = is_unsaved_assessor_checklist(frm);
	const selected_type = frm.doc.checklist_type;
	frm._loading_assessor_checklist_template = true;

	frappe.call({
		method: "numerouno.numerouno.doctype.assessor_checklist.assessor_checklist.load_template",
		args: {
			checklist_type: selected_type,
			docname: unsaved ? null : frm.doc.name,
			clear_existing: clear_existing ? 1 : 0,
		},
		freeze: true,
		callback(r) {
			frm._loading_assessor_checklist_template = false;
			if (r.exc) return;

			if (!unsaved) {
				frm.reload_doc();
				return;
			}

			apply_assessor_checklist_template(frm, r.message || {}, selected_type);
			frm._assessor_checklist_template_loaded = true;
			if (frm.doc.student_group) {
				populate_learners_from_student_group(frm);
			}
		},
	});
}

function apply_assessor_checklist_template(frm, data, checklist_type) {
	frm.doc.checklist_type = checklist_type;
	frm.doc.form_code = data.form_code;
	frm.doc.title = data.title;
	frm.doc.course_code = data.course_code;
	frm.doc.footer_notes = data.footer_notes;
	frm.doc.unit_description = data.unit_description;

	frm.clear_table("module_groups");
	(data.module_groups || []).forEach((row) => {
		frm.add_child("module_groups", {
			module_code: row.module_code,
			module_title: row.module_title,
		});
	});

	frm.clear_table("outcomes");
	(data.outcomes || []).forEach((row) => {
		frm.add_child("outcomes", {
			outcome_code: row.outcome_code,
			assessment_method: row.assessment_method,
			module_group: row.module_group,
		});
	});

	frm.clear_table("assessors");
	(data.assessors || []).forEach((row) => {
		frm.add_child("assessors", {
			sr_no: row.sr_no,
			module: row.module,
			description: row.description,
			assessor_name: row.assessor_name || "",
		});
	});

	frm.clear_table("learners");
	for (let i = 1; i <= 16; i++) {
		frm.add_child("learners", { row_no: i, learner_name: "" });
	}

	frm.refresh_field("module_groups");
	frm.refresh_field("outcomes");
	frm.refresh_field("assessors");
	frm.refresh_field("learners");
	frm.refresh_field("unit_description");
}
