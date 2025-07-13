// Copyright (c) 2025, mohtashim and contributors
// For license information, please see license.txt

frappe.query_reports["Unpaid Students"] = {
	filters: [
    {
      fieldname: "student_group",
      label: __("Student Group"),
      fieldtype: "Link",
      options: "Student Group",
      get_query: function() {
        return {
          filters: {
            "disabled": 0
          }
        };
      }
    },
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
      fieldname: "instructor",
      label: __("Instructor"),
      fieldtype: "Link",
      options: "Instructor"
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
  ],
  
  onload: function(report) {
    // Add custom button to send email notifications
    report.page.add_inner_button(__("Send Email Notifications"), function() {
      frappe.confirm(
        __("Send email notifications to Accounts team for all unpaid students?"),
        function() {
          // Send email notification
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
    
    // Add test email button
    report.page.add_inner_button(__("Test Email Configuration"), function() {
      frappe.prompt([
        {
          fieldname: "email",
          label: __("Test Email Address"),
          fieldtype: "Data",
          default: frappe.user.email || "",
          reqd: 1
        }
      ], function(values) {
        frappe.call({
          method: "numerouno.numerouno.doctype.student_group.student_group.send_test_email",
          args: {
            recipient_email: values.email
          },
          callback: function(r) {
            if (r.exc) {
              frappe.msgprint(__("Error sending test email: ") + r.exc);
            } else if (r.message && r.message.status === "success") {
              frappe.msgprint(__("Test email sent successfully! Please check your inbox."));
            } else {
              frappe.msgprint(__("Error: ") + (r.message ? r.message.message : "Unknown error"));
            }
          }
        });
      }, __("Send Test Email"), __("Send"));
    });
    
    // Add email queue flush button
    report.page.add_inner_button(__("Flush Email Queue"), function() {
      frappe.confirm(
        __("Flush the email queue to send pending emails?"),
        function() {
          frappe.call({
            method: "numerouno.numerouno.doctype.student_group.student_group.flush_email_queue",
            callback: function(r) {
              if (r.exc) {
                frappe.msgprint(__("Error flushing email queue: ") + r.exc);
              } else {
                frappe.msgprint(__("Email queue flushed successfully!"));
              }
            }
          });
        }
      );
    });
  }
}; 