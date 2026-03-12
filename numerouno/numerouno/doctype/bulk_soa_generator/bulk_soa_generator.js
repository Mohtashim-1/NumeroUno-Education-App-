// Copyright (c) 2025, Numero Uno and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bulk SOA Generator", {
    refresh: function(frm) {
        if (!frm.doc.__islocal) {
            // Add Generate PDF button
            frm.add_custom_button(__("Generate PDF"), function() {
                if (frm.is_dirty()) {
                    frappe.throw(__("Please save before proceeding."));
                }
                
                frappe.call({
                    method: "numerouno.numerouno.doctype.bulk_soa_generator.bulk_soa_generator.generate_bulk_soa_pdf",
                    args: {
                        doc_name: frm.doc.name
                    },
                    callback: function(r) {
                        if (r.exc) {
                            frappe.msgprint(__("Error generating PDF: ") + r.exc);
                        } else {
                            frappe.msgprint(__("PDF generation completed successfully!"));
                        }
                    }
                });
            });
            
            // Add Send Emails button
            frm.add_custom_button(__("Send Emails"), function() {
                if (frm.is_dirty()) {
                    frappe.throw(__("Please save before proceeding."));
                }
                
                frappe.confirm(
                    __("Are you sure you want to send SOA emails to all selected customers?"),
                    function() {
                        frappe.call({
                            method: "numerouno.numerouno.doctype.bulk_soa_generator.bulk_soa_generator.send_bulk_soa_emails",
                            args: {
                                doc_name: frm.doc.name
                            },
                            callback: function(r) {
                                if (r.exc) {
                                    frappe.msgprint(__("Error sending emails: ") + r.exc);
                                } else {
                                    frappe.msgprint(__("Email sending completed! ") + r.message.message);
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                );
            });
            
            // Add Download PDF button
            frm.add_custom_button(__("Download PDF"), function() {
                if (frm.is_dirty()) {
                    frappe.throw(__("Please save before proceeding."));
                }
                
                let url = frappe.urllib.get_full_url(
                    "/api/method/numerouno.numerouno.doctype.bulk_soa_generator.bulk_soa_generator.download_bulk_soa_pdf?" +
                    "doc_name=" + encodeURIComponent(frm.doc.name)
                );
                
                window.open(url, '_blank');
            });
        }
    },
    
    onload: function(frm) {
        // Set default dates
        if (frm.doc.__islocal) {
            frm.set_value("from_date", frappe.datetime.add_months(frappe.datetime.get_today(), -1));
            frm.set_value("to_date", frappe.datetime.get_today());
        }
        // Set default subject, body, sender
        if (!frm.doc.subject) {
            frm.set_value("subject", "Statement of Account - {{ customer.customer_name }}");
        }
        if (!frm.doc.body) {
            frm.set_value("body", `<p>Dear {{ customer.customer_name }},</p>\n<p>Please find attached your Statement of Account for the period from {{ doc.from_date }} to {{ doc.to_date }}.</p>\n<p>Best regards,<br>{{ doc.company }}</p>`);
        }
        if (!frm.doc.sender) {
            frappe.db.get_value("Email Account", {"default_outgoing": 1}, "email_id", function(r) {
                if (r && r.email_id) {
                    frm.set_value("sender", r.email_id);
                }
            });
        }
        
        // Set up field queries
        frm.set_query("account", function() {
            return {
                filters: {
                    company: frm.doc.company,
                    account_type: "Receivable"
                }
            };
        });
        
        frm.set_query("currency", function() {
            return {
                filters: {
                    enabled: 1
                }
            };
        });
    },
    
    company: function(frm) {
        // Clear account when company changes
        frm.set_value("account", "");
    },
    
    report_type: function(frm) {
        // Update account query based on report type
        if (frm.doc.report_type == "Accounts Receivable") {
            frm.set_query("account", function() {
                return {
                    filters: {
                        company: frm.doc.company,
                        account_type: "Receivable"
                    }
                };
            });
        } else {
            frm.set_query("account", function() {
                return {
                    filters: {
                        company: frm.doc.company
                    }
                };
            });
        }
    },
    
    fetch_customers: function(frm) {
        // This will be handled by the server method
        frappe.call({
            method: "numerouno.numerouno.doctype.bulk_soa_generator.bulk_soa_generator.fetch_customers_by_criteria",
            args: {
                doc_name: frm.doc.name
            },
            callback: function(r) {
                if (r.exc) {
                    frappe.msgprint(__("Error fetching customers: ") + r.exc);
                } else {
                    frappe.msgprint(r.message.message);
                    frm.reload_doc();
                    frm.refresh_field("customers");
                }
            }
        });
    }
});

// Child table events
frappe.ui.form.on("Bulk SOA Generator Customer", {
    customer: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.customer) {
            frappe.db.get_value("Customer", row.customer, "customer_name", function(r) {
                if (r) {
                    row.customer_name = r.customer_name;
                    frm.refresh_field("customers");
                }
            });
        }
    }
}); 