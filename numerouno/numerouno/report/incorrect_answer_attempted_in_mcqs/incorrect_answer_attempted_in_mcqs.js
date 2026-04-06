// Copyright (c) 2026, mohtashim and contributors
// For license information, please see license.txt

frappe.query_reports["Incorrect Answer attempted in MCQs"] = {
	"filters": [
		{
			"fieldname": "quiz",
			"label": __("Quiz"),
			"fieldtype": "Link",
			"options": "Quiz"
		},
		{
			"fieldname": "course",
			"label": __("Course"),
			"fieldtype": "Link",
			"options": "Course"
		},
		{
			"fieldname": "student",
			"label": __("Student"),
			"fieldtype": "Link",
			"options": "Student"
		},
		{
			"fieldname": "question",
			"label": __("Question"),
			"fieldtype": "Link",
			"options": "Question"
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date"
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date"
		}
	]
};
