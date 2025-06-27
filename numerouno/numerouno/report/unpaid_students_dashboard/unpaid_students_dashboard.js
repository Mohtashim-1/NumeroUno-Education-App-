// Copyright (c) 2025, mohtashim and contributors
// For license information, please see license.txt

frappe.query_reports["Unpaid Students Dashboard"] = {
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
      fieldname: "priority",
      label: __("Priority Level"),
      fieldtype: "Select",
      options: "\nAll\nHigh Priority (>30 days)\nMedium Priority (15-30 days)\nLow Priority (<15 days)",
      default: "All"
    }
  ],
  
  onload: function(report) {
    // Add custom buttons for actions
    report.page.add_inner_button(__("Send Email Notifications"), function() {
      frappe.confirm(
        __("Send email notifications to Accounts team for all unpaid students?"),
        function() {
          frappe.call({
            method: "numerouno.numerouno.doctype.student_group.student_group.send_daily_unpaid_notifications",
            callback: function(r) {
              if (r.exc) {
                frappe.msgprint(__("Error sending notifications: ") + r.exc);
              } else {
                frappe.msgprint(__("Email notifications sent successfully!"));
              }
            }
          });
        }
      );
    });
    
    report.page.add_inner_button(__("Export to Excel"), function() {
      frappe.call({
        method: "frappe.desk.query_report.export_query",
        args: {
          report_name: "Unpaid Students Dashboard",
          filters: report.get_values()
        },
        callback: function(r) {
          if (r.message) {
            window.open(r.message, '_blank');
          }
        }
      });
    });
  }
}; 