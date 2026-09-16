frappe.ready(function () {
	const form = frappe.web_form;
	if (!form) {
		return;
	}

	function set_trainee_query() {
		form.set_query("trainee_name", () => {
			const filters = {};
			if (form.doc.student_group) {
				filters.student_group = form.doc.student_group;
			}
			return {
				query: "numerouno.numerouno.doctype.course_evaluation.course_evaluation.get_trainee_query",
				filters,
			};
		});
	}

	function set_student_group_query() {
		form.set_query("student_group", () => {
			const filters = {};
			if (form.doc.trainee_name) {
				filters.student = form.doc.trainee_name;
			}
			return {
				query: "numerouno.numerouno.doctype.course_evaluation.course_evaluation.get_student_group_query",
				filters,
			};
		});
	}

	function apply_details() {
		if (!form.doc.student_group) {
			return;
		}
		frappe.call({
			method: "numerouno.numerouno.doctype.course_evaluation.course_evaluation.apply_student_group_details",
			args: {
				student_group: form.doc.student_group,
				student: form.doc.trainee_name,
			},
			callback(r) {
				if (!r.message) {
					return;
				}
				Object.entries(r.message).forEach(([field, value]) => {
					if (field === "student_group") {
						return;
					}
					if (value !== undefined && value !== null && form.fields_dict[field]) {
						form.set_value(field, value);
					}
				});
			},
		});
	}

	set_trainee_query();
	set_student_group_query();

	form.on("trainee_name", () => {
		if (!form.doc.trainee_name) {
			form.set_value("student_group", "");
			return;
		}
		frappe.call({
			method: "numerouno.numerouno.doctype.course_evaluation.course_evaluation.get_student_groups_for_student",
			args: { student: form.doc.trainee_name },
			callback(r) {
				const groups = r.message || [];
				if (groups.length === 1) {
					form.set_value("student_group", groups[0]).then(() => apply_details());
				} else if (
					form.doc.student_group &&
					!groups.includes(form.doc.student_group)
				) {
					form.set_value("student_group", "");
				}
			},
		});
	});

	form.on("student_group", apply_details);
});
