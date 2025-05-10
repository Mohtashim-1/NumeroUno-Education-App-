// Copyright (c) 2025, mohtashim and contributors
// For license information, please see license.txt

frappe.query_reports["Pending Invoices"] = {
	filters: [
    {
      fieldname: "program",
      label: __("Program"),
      fieldtype: "Link",
      options: "Program"
    },
    {
      fieldname: "course",
      label: __("Course"),
      fieldtype: "Link",
      options: "Course"
    },
    {
      fieldname: "customer",
      label: __("Customer"),
      fieldtype: "Link",
      options: "Customer"
    },
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date"
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date"
    }
  ]
};
