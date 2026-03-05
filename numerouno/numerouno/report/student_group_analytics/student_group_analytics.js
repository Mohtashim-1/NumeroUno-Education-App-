// Copyright (c) 2026, mohtashim and contributors
// For license information, please see license.txt

frappe.query_reports["Student Group Analytics"] = {
	filters: [
		{
			fieldname: "student_group",
			label: __("Student Group"),
			fieldtype: "Link",
			options: "Student Group",
		},
		{
			fieldname: "course",
			label: __("Course"),
			fieldtype: "Link",
			options: "Course",
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "instructor",
			label: __("Instructor"),
			fieldtype: "Link",
			options: "Instructor",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
	],
};
