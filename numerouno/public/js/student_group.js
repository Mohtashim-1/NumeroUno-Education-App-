frappe.ui.form.on('Student Group', {
    refresh: function(frm) {
        frm.add_custom_button(__('Create Coarse Schedule'), () => {
            show_coarse_dialog(frm);
        }, __('Actions'));

        frm.add_custom_button(__('Create Attendance'), () => {
            show_attendance_dialog(frm);
        }, __('Actions'));

        
    }
});

function show_coarse_dialog(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __('Create Student Schedule'),
        fields: [
            {
                label: __('From Time'),
                fieldname: 'from_time',
                fieldtype: 'Time',
                reqd: 1,
            },
            {
                label: __('To Time'),
                fieldname: 'to_time',
                fieldtype: 'Time',
                reqd: 1,
            }
        ],
        primary_action_label: __('Create'),
        primary_action(values) {
            if (!values) return;

            frappe.call({
                method: "numerouno.numerouno.doctype.student_group.student_group.   ",
                args: {
                    student_group: frm.doc.name,
                    from_time: values.from_time,
                    to_time: values.to_time
                },
                callback: function(r) {
                    if (!r.exc) {
                        frappe.show_alert({
                            message: __('Coarse Schedule Created'),
                            indicator: 'green'
                        });
                    }
                },
                freeze: true,
                freeze_message: __('Creating Coarse Schedule...')
            });

            dialog.hide();
        }
    });

    dialog.show();
}


