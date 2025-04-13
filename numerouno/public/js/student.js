frappe.ui.form.on('Student', {
    refresh: function(frm) {
        frm.add_custom_button(__('Create Student Applicant'), () => {
            show_program_dialog(frm);
        }, __('Actions'));
    }
});

function show_program_dialog(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __('Create Student Applicant'),
        fields: [
            {
                label: __('Program'),
                fieldname: 'program',
                fieldtype: 'Link',
                options: 'Program',
                reqd: 1,
            }
        ],
        primary_action_label: __('Create'),
        primary_action(values) {
            if (!values) return;

            frappe.call({
                method: "numerouno.numerouno.doctype.student.student.create_student_applicant",
                args: {
                    student: frm.doc.name,
                    program: values.program
                },
                callback: function(r) {
                    if (!r.exc && r.message && r.message.name) {
                        frappe.show_alert({
                            message: __('Student Applicant created'),
                            indicator: 'green'
                        });
                        // Navigate to the new Student Applicant form
                        frappe.set_route('Form', 'Student Applicant', r.message.name);
                    }
                },
                freeze: true,
                freeze_message: __('Creating Student Applicant...')
            });

            dialog.hide();
        }
    });

    dialog.show();
}
