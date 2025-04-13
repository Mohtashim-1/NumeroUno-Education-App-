frappe.ui.form.on('Student', {
    refresh: function(frm) {
        // Button 1: Create Student Applicant
        frm.add_custom_button(__('Create Student Applicant'), () => {
            show_program_dialog(frm);
        }, __('Actions'));

        // Button 2: Create Student Group
        frm.add_custom_button(__('Create Student Group'), () => {
            show_student_group_dialog(frm);
        }, __('Actions'));

        // Button 2: Create Student Group
        frm.add_custom_button(__('Assign Student Group'), () => {
            assign_student_group(frm);
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

function show_student_group_dialog(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __('Create Student Group'),
        fields: [
            {
                label: __('Academic Year'),
                fieldname: 'academic_year',
                fieldtype: 'Link',
                options: 'Academic Year',
                reqd: 1,
            },
            {
                label: __('Group Based on'),
                fieldname: 'group_based_on',
                fieldtype: 'Select',
                default: "Course",
                options: ['Batch', 'Course', 'Program'].join('\n'),
                reqd: 1,
                onchange: function () {
                    update_required_fields(dialog);
                }
            },
            {
                label: __('Student Group Name'),
                fieldname: 'group_name',
                fieldtype: 'Data',
                reqd: 1,
            },
            {
                label: __('Program'),
                fieldname: 'program',
                fieldtype: 'Link',
                options: "Program",
            },
            {
                label: __('Course'),
                fieldname: 'course',
                fieldtype: 'Link',
                options: "Course",
            },
            {
                label: __('Batch'),
                fieldname: 'batch',
                fieldtype: 'Link',
                options: "Batch",
            },
            {
                fieldtype: 'Column Break'
            },
            {
                label: __('From Date'),
                fieldname: 'from_date',
                fieldtype: 'Date',
                default: frappe.datetime.get_today(),
            },
            {
                label: __('To Date'),
                fieldname: 'to_date',
                fieldtype: 'Date',
                default: frappe.datetime.get_today(),
            },
            {
                label: __('Coarse Location'),
                fieldname: 'coarse_location',
                fieldtype: 'Link',
                options: "Room"
            }
        ],
        primary_action_label: __('Create'),
        primary_action(values) {
            // Validate dynamically required field
            if (values.group_based_on === "Batch" && !values.batch) {
                frappe.throw(__('Batch is required'));
            }
            if (values.group_based_on === "Course" && !values.course) {
                frappe.throw(__('Course is required'));
            }
            if (values.group_based_on === "Program" && !values.program) {
                frappe.throw(__('Program is required'));
            }

            frappe.call({
                method: "numerouno.numerouno.doctype.student.student.create_student_group",
                args: {
                    student: frm.doc.name,
                    group_name: values.group_name,
                    academic_year: values.academic_year,
                    group_based_on: values.group_based_on,
                    course: values.course,
                    program: values.program,
                    batch: values.batch,
                    from_date: values.from_date,
                    to_date: values.to_date,
                    coarse_location: values.coarse_location
                },
                callback: function (r) {
                    if (!r.exc && r.message && r.message.name) {
                        frappe.show_alert({
                            message: __('Student Group created'),
                            indicator: 'green'
                        });
                        frappe.set_route('Form', 'Student Group', r.message.name);
                    }
                },
                freeze: true,
                freeze_message: __('Creating Student Group...')
            });

            dialog.hide();
        }
    });

    dialog.show();

    // Initial required setup
    update_required_fields(dialog);
}

function update_required_fields(dialog) {
    const selected = dialog.get_value('group_based_on');

    // Reset all required states
    ['batch', 'course', 'program'].forEach(field => {
        dialog.set_df_property(field, 'reqd', false);
    });

    // Make relevant field required
    if (selected === 'Batch') {
        dialog.set_df_property('batch', 'reqd', true);
    } else if (selected === 'Course') {
        dialog.set_df_property('course', 'reqd', true);
    } else if (selected === 'Program') {
        dialog.set_df_property('program', 'reqd', true);
    }

    dialog.refresh();
}

function assign_student_group(frm){
    const dialog = new frappe.ui.Dialog({
        title: __('Assign Student Group'),
        fields: [
            {
                label: __('Student Group'),
                fieldname: 'student_group',
                fieldtype: 'Link',
                options: 'Student Group',
                reqd: 1,
            },
        ],
        primary_action_label: __('Assign'),
        primary_action(values) {

            frappe.call({
                method: "numerouno.numerouno.doctype.student.student.assign_student_group",
                args: {
                    student: frm.doc.name,
                    student_group: values.student_group,
                },
                callback: function (r) {
                    if (!r.exc && r.message && r.message.name) {
                        frappe.show_alert({
                            message: __('Student Assigned to Student Group'),
                            indicator: 'green'
                        });
                        frappe.set_route('Form', 'Student Group', r.message.name);
                    }
                },
                freeze: true,
                freeze_message: __('Assigning Student Group...')
            });

            dialog.hide();
        }
    });

    dialog.show();
}

