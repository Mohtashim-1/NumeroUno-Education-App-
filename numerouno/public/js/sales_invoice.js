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
				'student_group': stud_grp
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
					frappe.msgprint(__('No students found in selected Student Groups'));
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
	}
}); 