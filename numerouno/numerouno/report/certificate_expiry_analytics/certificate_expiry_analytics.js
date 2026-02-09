// Copyright (c) 2026, mohtashim and contributors
// For license information, please see license.txt

frappe.query_reports["Certificate Expiry Analytics"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": "Validity From",
			"fieldtype": "Date",
			"default": frappe.datetime.month_start()
		},
		{
			"fieldname": "to_date",
			"label": "Validity To",
			"fieldtype": "Date",
			"default": frappe.datetime.nowdate()
		},
		{
			"fieldname": "student",
			"label": "Student",
			"fieldtype": "Link",
			"options": "Student"
		},
		{
			"fieldname": "course",
			"label": "Course",
			"fieldtype": "Link",
			"options": "Course"
		},
		{
			"fieldname": "customer",
			"label": "Customer",
			"fieldtype": "Data"
		},
		
	]
};
