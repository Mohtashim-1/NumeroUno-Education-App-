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

	const RATING_FIELDS = [
		"joining_instructions_clear",
		"training_room_environment",
		"administration_support",
		"objectives_clearly_defined",
		"content_organization",
		"materials_aligned",
		"course_pace",
		"presentation_skills",
		"teaching_effectiveness",
		"knowledge_accessibility",
		"assignments_exercises",
		"handouts_tools_equipment",
		"technology_effectiveness",
	];
	
	function missing_ratings() {
		return RATING_FIELDS.filter((fieldname) => {
			const value = flt((form.doc && form.doc[fieldname]) || 0);
			return value <= 0;
		}).map((fieldname) => {
			const field = form.fields_dict[fieldname];
			return (field && field.df && field.df.label) || fieldname;
		});
	}

	form.validate = () => {
		const missing = missing_ratings();
		if (!missing.length) {
			return true;
		}
		frappe.msgprint({
			title: __("Rating required"),
			indicator: "orange",
			message:
				__("Please rate every item before submitting:") +
				"<br><br><ul><li>" +
				missing.join("</li><li>") +
				"</li></ul>",
		});
		return false;
	};

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
