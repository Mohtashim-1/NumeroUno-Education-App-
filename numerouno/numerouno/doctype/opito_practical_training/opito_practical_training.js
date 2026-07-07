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
});
