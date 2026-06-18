frappe.ui.form.on("Safety Briefing", {
	onload(frm) {
		frm._safety_briefing_template_loaded = false;
	},

	refresh(frm) {
		frm.add_custom_button(__("Load Template"), () => {
			if (!frm.doc.briefing_type) {
				frappe.msgprint(__("Select a Briefing Type first"));
				return;
			}
			const clear_existing = frm.doc.discussion_points?.length > 0;
			if (clear_existing) {
				frappe.confirm(
					__("Replace existing discussion points and practical exercises with the template?"),
					() => load_safety_briefing_template(frm, true)
				);
			} else {
				load_safety_briefing_template(frm, false);
			}
		}, __("Actions"));

		if (frm.doc.student_group) {
			frm.add_custom_button(__("Populate Attendees from Student Group"), () => {
				populate_attendees_from_student_group(frm);
			}, __("Actions"));
		}

		toggle_attendee_signature_columns(frm);
	},

	student_group(frm) {
		if (frm.doc.student_group) {
			populate_attendees_from_student_group(frm);
		} else {
			ensure_blank_attendee_rows(frm);
		}
	},

	briefing_type(frm) {
		if (!frm.doc.briefing_type) return;
		if (frm._loading_briefing_template) return;

		if (frm.doc.discussion_points?.length) {
			frappe.confirm(
				__("Load the template for {0}?", [frm.doc.briefing_type]),
				() => load_safety_briefing_template(frm, true),
				() => {
					frm.reload_doc();
				}
			);
		} else {
			load_safety_briefing_template(frm, false);
		}
	},

	attendee_signature_mode(frm) {
		toggle_attendee_signature_columns(frm);
	},
});

function populate_attendees_from_student_group(frm) {
	if (!frm.doc.student_group) return;

	const unsaved = is_unsaved_safety_briefing(frm);
	const method = unsaved
		? "numerouno.numerouno.doctype.safety_briefing.safety_briefing.get_attendees_for_student_group"
		: "numerouno.numerouno.doctype.safety_briefing.safety_briefing.populate_attendees_from_student_group";

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
				apply_attendees_to_form(frm, r.message || []);
				frappe.show_alert({
					message: __("Attendees loaded from Student Group"),
					indicator: "green",
				});
				return;
			}

			frm.reload_doc();
		},
	});
}

function apply_attendees_to_form(frm, attendees) {
	frm.clear_table("attendees");
	(attendees || []).forEach((row) => {
		frm.add_child("attendees", {
			learner_name: row.learner_name || "",
			student: row.student || "",
			company: row.company || "",
		});
	});
	while ((frm.doc.attendees || []).length < 16) {
		frm.add_child("attendees", {});
	}
	frm.refresh_field("attendees");
}

function ensure_blank_attendee_rows(frm) {
	if ((frm.doc.attendees || []).length >= 16) return;
	frm.clear_table("attendees");
	for (let i = 0; i < 16; i++) {
		frm.add_child("attendees", {});
	}
	frm.refresh_field("attendees");
}

function is_unsaved_safety_briefing(frm) {
	return frm.is_new() || (frm.doc.name && frm.doc.name.startsWith("new-"));
}

function load_safety_briefing_template(frm, clear_existing) {
	if (!frm.doc.briefing_type) return;

	const unsaved = is_unsaved_safety_briefing(frm);
	const selected_type = frm.doc.briefing_type;
	frm._loading_briefing_template = true;

	frappe.call({
		method: "numerouno.numerouno.doctype.safety_briefing.safety_briefing.load_template",
		args: {
			briefing_type: selected_type,
			docname: unsaved ? null : frm.doc.name,
			clear_existing: clear_existing ? 1 : 0,
		},
		freeze: true,
		callback(r) {
			frm._loading_briefing_template = false;
			if (r.exc) {
				return;
			}

			if (!unsaved) {
				frm.reload_doc();
				return;
			}

			const data = r.message || {};
			frm.set_value("briefing_type", selected_type);
			frm.set_value("form_code", data.form_code);
			frm.set_value("title", data.title);
			frm.set_value("attendee_signature_mode", data.attendee_signature_mode);
			frm.set_value("signature_labels", data.signature_labels);
			frm.set_value("instructor_mode", data.instructor_mode);

			apply_template_child_rows(frm, data);
			frm._safety_briefing_template_loaded = true;
			frm.refresh_fields();
			if (frm.doc.student_group) {
				populate_attendees_from_student_group(frm);
			}
			toggle_attendee_signature_columns(frm);
		},
	});
}

function apply_template_child_rows(frm, data) {
	frm.clear_table("discussion_points");
	(data.discussion_points || []).forEach((row) => {
		frm.add_child("discussion_points", {
			sr_no: row.sr_no,
			discussion_point: row.discussion_point,
			confirmed: row.confirmed ? 1 : 0,
		});
	});

	frm.clear_table("practical_items");
	(data.practical_items || []).forEach((row) => {
		frm.add_child("practical_items", {
			sr_no: row.sr_no,
			exercise_group: row.exercise_group,
			activity_detail: row.activity_detail,
			risk_points: row.risk_points,
			confirmed: row.confirmed ? 1 : 0,
		});
	});

	frm.clear_table("instructors");
	(data.instructors || []).forEach((row) => {
		frm.add_child("instructors", {
			instructor_name: row.instructor_name,
			module: row.module,
		});
	});

	if (!frm.doc.student_group) {
		frm.clear_table("attendees");
		for (let i = 0; i < 16; i++) {
			frm.add_child("attendees", {});
		}
	}
}

function toggle_attendee_signature_columns(frm) {
	const grid = frm.fields_dict.attendees?.grid;
	if (!grid) return;

	const show_modules = frm.doc.attendee_signature_mode === "Module Columns";
	const labels = (frm.doc.signature_labels || "").split(",").map((s) => s.trim()).filter(Boolean);
	const sign_fields = ["sign_col_1", "sign_col_2", "sign_col_3", "sign_col_4", "sign_col_5"];
	const parent_name = is_unsaved_safety_briefing(frm) ? null : frm.doc.name;

	sign_fields.forEach((field, idx) => {
		grid.toggle_display(field, show_modules && idx < labels.length);
		if (labels[idx]) {
			const df = frappe.meta.get_docfield("Safety Briefing Attendee", field, parent_name);
			if (df) df.label = labels[idx];
		}
	});
	grid.toggle_display("signed", !show_modules);
	grid.refresh();
}
