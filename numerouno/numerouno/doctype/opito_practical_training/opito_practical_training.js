// Copyright (c) 2026, mohtashim and contributors
// For license information, please see license.txt

function bind_opito_debug_handlers(frm) {
	const trainerField = frm.get_field("traineraccessor_name");
	if (trainerField && trainerField.$input) {
		trainerField.$input.off("focus.opito_debug input.opito_debug");
		trainerField.$input.on("focus.opito_debug", function () {
			console.log("[OPITO] trainer field focus", {
				currentValue: trainerField.get_value(),
				inputText: $(this).val(),
			});
		});
		trainerField.$input.on("input.opito_debug", function () {
			console.log("[OPITO] trainer field input", {
				inputText: $(this).val(),
				modelValue: trainerField.get_value(),
			});
		});
		console.log("[OPITO] debug handlers bound", { field: "traineraccessor_name" });
	} else {
		console.log("[OPITO] debug handlers not bound yet", { field: "traineraccessor_name" });
	}
}

function apply_student_group_details(frm) {
	if (!frm.doc.student_group) {
		return;
	}

	frappe.call({
		method:
			"numerouno.numerouno.doctype.opito_practical_training.opito_practical_training.get_student_group_details",
		args: { student_group: frm.doc.student_group },
		callback(r) {
			if (r.exc || !r.message) return;
			const data = r.message;
			if (data.course) {
				frm.set_value("course", data.course);
			}
			if (data.total_learners != null) {
				frm.set_value("total_no_of_learner", data.total_learners);
			}
		},
	});
}

frappe.ui.form.on("OPITO Practical Training", {
	onload(frm) {
		console.log("[OPITO] onload", {
			user: frappe.session && frappe.session.user,
			doctype: frm.doctype,
			docname: frm.docname,
			traineraccessor_name: frm.doc.traineraccessor_name,
			technician_name: frm.doc.technician_name,
		});

		if (frm.is_new()) {
			if (frm.doc.traineraccessor_name) frm.set_value("traineraccessor_name", "");
			if (frm.doc.technician_name) frm.set_value("technician_name", "");

			if (frappe.route_options) {
				if (frappe.route_options.student_group && !frm.doc.student_group) {
					frm.set_value("student_group", frappe.route_options.student_group);
				}
				if (frappe.route_options.course && !frm.doc.course) {
					frm.set_value("course", frappe.route_options.course);
				}
				delete frappe.route_options.student_group;
				delete frappe.route_options.course;
			}
		}

		frm.set_query("traineraccessor_name", () => ({
			query: "numerouno.numerouno.doctype.attendance_staff.attendance_staff.get_staff_by_role",
			filters: { role: "Lead Instructor" },
		}));

		frm.set_query("technician_name", () => ({
			query: "numerouno.numerouno.doctype.attendance_staff.attendance_staff.get_staff_by_role",
			filters: { role: "Diver" },
		}));

		frappe.call({
			method: "numerouno.numerouno.doctype.attendance_staff.attendance_staff.get_staff_by_role",
			args: {
				doctype: "Attendance Staff",
				txt: "",
				searchfield: "name",
				start: 0,
				page_len: 20,
				filters: { role: "Lead Instructor" },
			},
			callback: (r) => {
				console.log("[OPITO] traineraccessor_name backend options", {
					count: (r.message || []).length,
					rows: r.message || [],
				});
			},
		});
	},

	refresh(frm) {
		bind_opito_debug_handlers(frm);
	},

	student_group(frm) {
		if (frm.doc.student_group) {
			apply_student_group_details(frm);
		}
	},
});
