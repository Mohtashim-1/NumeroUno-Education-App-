frappe.listview_settings["Assessment Result"] = {
	add_fields: [
		"custom_certificate",
		"custom_company",
		"course",
		"student",
		"student_name",
		"student_group",
		"assessment_plan",
		"custom_unique_certificate_no",
		"custom_opito_learner_no",
	],
	filters: [
		["custom_certificate", "is", "not set"],
	],
};
