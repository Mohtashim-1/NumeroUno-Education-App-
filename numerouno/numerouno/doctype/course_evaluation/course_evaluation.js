// Copyright (c) 2025, mohtashim and contributors

const COURSE_EVAL_PREFILL_FIELDS = [
	"course_name",
	"company",
	"instructor_name",
	"dates",
	"email_id",
	"trainee_mobile",
];

function set_trainee_query(frm) {
	frm.set_query("trainee_name", () => {
		const filters = {};
		if (frm.doc.student_group) {
			filters.student_group = frm.doc.student_group;
		}
		return {
			query: "numerouno.numerouno.doctype.course_evaluation.course_evaluation.get_trainee_query",
			filters,
		};
	});
}

function set_student_group_query(frm) {
	frm.set_query("student_group", () => {
		const filters = {};
		if (frm.doc.trainee_name) {
			filters.student = frm.doc.trainee_name;
		}
		return {
			query: "numerouno.numerouno.doctype.course_evaluation.course_evaluation.get_student_group_query",
			filters,
		};
	});
}

function apply_student_group_details(frm) {
	if (!frm.doc.student_group) {
		return;
	}

	frappe.call({
		method: "numerouno.numerouno.doctype.course_evaluation.course_evaluation.apply_student_group_details",
		args: {
			student_group: frm.doc.student_group,
			student: frm.doc.trainee_name,
		},
		freeze: true,
		freeze_message: __("Loading course details..."),
		callback(r) {
			if (!r.message) {
				return;
			}
			const data = r.message;
			COURSE_EVAL_PREFILL_FIELDS.forEach((field) => {
				if (data[field] !== undefined && data[field] !== null) {
					frm.set_value(field, data[field]);
				}
			});
		},
	});
}

function auto_select_single_student_group(frm) {
	if (!frm.doc.trainee_name || frm.doc.student_group) {
		return;
	}

	frappe.call({
		method: "numerouno.numerouno.doctype.course_evaluation.course_evaluation.get_student_groups_for_student",
		args: { student: frm.doc.trainee_name },
		callback(r) {
			const groups = r.message || [];
			if (groups.length === 1) {
				frm.set_value("student_group", groups[0]).then(() => apply_student_group_details(frm));
			}
		},
	});
}

frappe.ui.form.on("Course Evaluation", {
	refresh(frm) {
		set_trainee_query(frm);
		set_student_group_query(frm);
	},

	trainee_name(frm) {
		if (frm.doc.student_group && frm.doc.trainee_name) {
			frappe.db
				.exists("Student Group Student", {
					parent: frm.doc.student_group,
					student: frm.doc.trainee_name,
				})
				.then((exists) => {
					if (!exists) {
						frm.set_value("student_group", "");
					}
				});
		} else if (!frm.doc.trainee_name) {
			frm.set_value("student_group", "");
		}
		auto_select_single_student_group(frm);
	},

	student_group(frm) {
		if (frm.doc.student_group && frm.doc.trainee_name) {
			frappe.db
				.exists("Student Group Student", {
					parent: frm.doc.student_group,
					student: frm.doc.trainee_name,
				})
				.then((exists) => {
					if (!exists) {
						frm.set_value("trainee_name", "");
					}
				});
		}
		apply_student_group_details(frm);
	},
});
