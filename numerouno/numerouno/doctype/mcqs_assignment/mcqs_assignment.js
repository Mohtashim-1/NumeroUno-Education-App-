// Copyright (c) 2025, mohtashim and contributors
// For license information, please see license.txt

frappe.ui.form.on("MCQS Assignment", {
	refresh(frm) {
		set_section_profile_query(frm);
		show_section_setup_help(frm);
	},

	mcqs(frm) {
		set_section_profile_query(frm);
		autofill_section_profile(frm);
	},

	assignment_flow(frm) {
		if (frm.doc.assignment_flow !== "Section Wise MCQs") {
			frm.set_value("quiz_section_profile", "");
		} else {
			autofill_section_profile(frm);
		}
		show_section_setup_help(frm);
	}
});

function set_section_profile_query(frm) {
	frm.set_query("quiz_section_profile", () => {
		const filters = {};
		if (frm.doc.mcqs) {
			filters.quiz = frm.doc.mcqs;
		}
		return { filters };
	});
}

function autofill_section_profile(frm) {
	if (frm.doc.assignment_flow !== "Section Wise MCQs" || !frm.doc.mcqs) {
		return;
	}

	frappe.db.exists("Quiz Section Profile", frm.doc.mcqs).then((exists) => {
		if (exists && !frm.doc.quiz_section_profile) {
			frm.set_value("quiz_section_profile", frm.doc.mcqs);
		}
	});
}

function show_section_setup_help(frm) {
	if (frm.doc.assignment_flow !== "Section Wise MCQs") {
		return;
	}

	frm.dashboard.clear_comment();
	frm.dashboard.add_comment(
		__(
			"Section-wise MCQs use the selected Quiz Section Profile. Make sure every question row in the Quiz has a Section Key matching the profile, like S1, S2, S3."
		),
		"blue",
		true
	);
}
