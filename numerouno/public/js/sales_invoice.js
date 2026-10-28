frappe.ui.form.on('Sales Invoice', {
	fetch_students: function (frm) {
		var stud_grp = []
		if (frm.doc.select_student_group) {
			// Handle multi-select field - extract student group names properly
			$.each(frm.doc.select_student_group, function (k, stud) {
				if (stud.student_group) {
					// Extract the actual student group name from the array
					var student_group_name = stud.student_group;
					// Remove any brackets or quotes if present
					student_group_name = student_group_name.replace(/[\[\]"]/g, '');
					stud_grp.push(student_group_name);
				}
			})
		}
		
		if (stud_grp.length === 0) {
			frappe.msgprint(__('Please select at least one Student Group first.'));
			return;
		}
		
		frappe.call({
			"method": "numerouno.numerouno.doctype.sales_invoice.sales_invoice.fetch_students_from_sg",
			"args": {
				'customer': frm.doc.customer,
				'student_group': stud_grp,
				'current_invoice': frm.doc.docstatus === 0 ? frm.doc.name : null
			},
			callback: function (r) {
				if (r.message && r.message.length > 0) {
					frm.clear_table('student');
					$.each(r.message, function (k, stud) {
						var child = cur_frm.add_child('student');
						child.student = stud.student;
						child.student_name = stud.student_name;
						child.course = stud.course_name;
						child.student_group = stud.student_group;
						child.start_date = stud.start_date;
						child.end_date = stud.end_date;
						frm.refresh_fields("student");
					});
					frappe.show_alert(__('Fetched {0} students', [r.message.length]));
				} else {
					frappe.msgprint(__('No pending students found in selected Student Groups'));
				}
			}
		});
	},

	refresh: function (frm) {
		if (frm.doc.customer) {
		    frappe.call({
		        "method": "numerouno.numerouno.doctype.sales_invoice.sales_invoice.fetch_students_group",
		        "args":{
		            "customer":frm.doc.customer
		        },
		        callback:function(r){
		            if(r.message && r.message.length > 0){
                    frm.set_query("select_student_group", function () {
                        return {
                            "filters": [
                                ['Student Group', 'name', 'in', r.message]
                            ]
                        };
                    });
                    frappe.show_alert(__('Found {0} Student Groups for this customer', [r.message.length]));
                } else {
                    frappe.show_alert(__('No Student Groups found for this customer'));
                }
            	}
		    })
        }

		if (frm.fields_dict.custom_delivery_driver) {
			frm.set_query("custom_delivery_driver", function () {
				return {
					query: "numerouno.numerouno.page.driver_invoice_portal.driver_invoice_portal.get_delivery_driver_users",
				};
			});
		}

		frm.add_custom_button(__("Quick Bulk from Student Groups"), function () {
			nutc_show_quick_bulk_invoice_dialog();
		}, __("Create"));
	}
});

function nutc_show_quick_bulk_invoice_dialog(ondone) {
	const dialog = new frappe.ui.Dialog({
		title: __("Quick Bulk Invoice from Student Groups"),
		fields: [
			{
				fieldtype: "HTML",
				options: `<p>${__(
					"Paste Student Group IDs (one per line). Pending students in those groups will be added to draft Sales Invoice(s)."
				)}</p>`,
			},
			{
				label: __("Student Groups"),
				fieldname: "student_groups",
				fieldtype: "Long Text",
				reqd: 1,
				description: __("Example: STD-GRP-2026-44560"),
			},
			{
				label: __("Rate"),
				fieldname: "rate",
				fieldtype: "Currency",
				reqd: 1,
				default: 1880,
			},
			{
				label: __("Customer (optional)"),
				fieldname: "customer",
				fieldtype: "Link",
				options: "Customer",
				description: __("Leave blank to auto-split by customer."),
			},
		],
		primary_action_label: __("Create Draft Invoice(s)"),
		primary_action(values) {
			frappe.call({
				method: "numerouno.numerouno.page.invoiced_creation.invoiced_creation.create_invoice_from_student_groups",
				args: {
					student_groups: values.student_groups,
					rate: values.rate,
					customer: values.customer,
				},
				freeze: true,
				freeze_message: __("Creating invoice from student groups..."),
				callback(r) {
					if (r.exc) return;
					const msg = r.message || {};
					const invoices = msg.invoices || [];
					dialog.hide();
					let note = __("{0} draft invoice(s), {1} students, {2} groups", [
						msg.invoice_count || 0,
						msg.student_count || 0,
						msg.student_group_count || 0,
					]);
					if ((msg.skipped_groups || []).length) {
						note +=
							"<br>" +
							__("Skipped (already invoiced / no pending): {0}", [
								(msg.skipped_groups || []).slice(0, 15).join(", "),
							]);
					}
					frappe.msgprint({
						title: __("Invoice Created"),
						indicator: "green",
						message: note,
					});
					if (ondone) ondone();
					if (invoices.length === 1) {
						frappe.set_route("Form", "Sales Invoice", invoices[0].sales_invoice);
					} else if (invoices.length > 1) {
						frappe.set_route("List", "Sales Invoice");
					}
				},
			});
		},
	});
	dialog.$wrapper.find(".modal-dialog").css("max-width", "720px");
	dialog.show();
}