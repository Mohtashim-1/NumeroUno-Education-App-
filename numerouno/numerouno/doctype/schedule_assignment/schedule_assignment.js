// Copyright (c) 2026, mohtashim and contributors
// For license information, please see license.txt

frappe.ui.form.on("Schedule Assignment", {
	onload(frm) {
		if (!frm.is_new() || has_meaningful_entries(frm)) return;
		populate_default_instructors(frm);
	},

	refresh(frm) {
		if (frm.is_new() && !has_meaningful_entries(frm)) {
			populate_default_instructors(frm);
			return;
		}

		if (frm.is_new()) return;

		frm.add_custom_button(__("Print Schedule"), () => {
			const params = new URLSearchParams({
				doctype: frm.doc.doctype,
				name: frm.doc.name,
				format: "Schedule Assignment Sheet",
				no_letterhead: 1,
			});

			window.open(`/printview?${params.toString()}`, "_blank");
		});
	},
});

frappe.ui.form.on("Schedule Assignment Item", {
	instructor(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.instructor) return;

		frappe.db.get_value("Instructor", row.instructor, "instructor_name").then((r) => {
			if (!r.message) return;
			frappe.model.set_value(cdt, cdn, "assignee_name", r.message.instructor_name || "");
		});
	},
});

function populate_default_instructors(frm) {
	frappe.call({
		method: "numerouno.numerouno.doctype.schedule_assignment.schedule_assignment.get_default_instructors",
		callback: (r) => {
			const instructors = r.message || [];
			if (!frm.is_new() || has_meaningful_entries(frm) || !instructors.length) return;

			(frm.doc.entries || []).forEach((row) => {
				if (row.name) {
					frappe.model.clear_doc(row.doctype, row.name);
				}
			});
			frm.doc.entries = [];

			instructors.forEach((instructor) => {
				const row = frm.add_child("entries");
				row.session = "Morning";
				row.instructor = instructor.name;
				row.assignee_name = instructor.instructor_name;
				// row.assignment_details = "TBA";
			});

			frm.refresh_field("entries");
		},
	});
}

function has_meaningful_entries(frm) {
	return (frm.doc.entries || []).some((row) => {
		return Boolean(
			(row.instructor || "").trim() ||
			(row.assignee_name || "").trim() ||
			(row.assignment_details || "").trim() ||
			(row.room_or_batch || "").trim()
		);
	});
}
