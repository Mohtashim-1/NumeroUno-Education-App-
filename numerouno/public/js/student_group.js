frappe.ui.form.on('Student Group', {
    refresh: function(frm) {
        frm.add_custom_button(__('Create Coarse Schedule'), () => {
            show_coarse_dialog(frm);
        }, __('Actions'));

        // create Assessment Plan

        frm.add_custom_button(__('Create Assessment Plan'), () => {
            show_assessment_dialog(frm);
        }, __('Actions'));


        frm.add_custom_button(__('Create Assessment Results (Bulk)'), () => {
            show_bulk_assessment_result_dialog(frm);
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
                method: "numerouno.numerouno.doctype.student_group.student_group.create_coarse_schedule",
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


function show_assessment_dialog(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __('Create Assessment Plan'),
        fields: [
            {
                label: __('Assessment Name'),
                fieldname: 'assessment_name',
                fieldtype: 'Data',
                reqd: 1,
            },
            {
                label: __('Assessment Group'),
                fieldname: 'assessment_group',
                fieldtype: 'Link',
                options: "Assessment Group",
                default: "All Assessment Groups",
                reqd: 1,
            },
            {
                label: __('Grading Scale'),
                fieldname: 'grading_scale',
                fieldtype: 'Link',
                options: "Grading Scale",
                default: "Default Grading",
                reqd: 1,
            },
            { fieldtype: 'Column Break' },
            {
                label: __('Examiner'),
                fieldname: 'examiner',
                fieldtype: 'Link',
                options: "Instructor",
                reqd: 1,
            },
            {
                label: __('Supervisor'),
                fieldname: 'supervisor',
                fieldtype: 'Link',
                options: "Instructor",
                reqd: 1,
            },
            {
                label: __('Schedule Date'),
                fieldname: 'schedule_date',
                fieldtype: 'Date',
                default: frappe.datetime.get_today(),
                reqd: 1,
            },
            { fieldtype: 'Column Break' },
            {
                label: __('From Time'),
                fieldname: 'from_time',
                fieldtype: 'Time',
                default: frappe.datetime.now_time(),
                reqd: 1,
            },
            {
                label: __('To Time'),
                fieldname: 'to_time',
                fieldtype: 'Time',
                default: frappe.datetime.now_time(),
                reqd: 1,
            },
            {
                label: __('Maximum Assessment Score'),
                fieldname: 'maximum_assessment_score',
                fieldtype: 'Float',
                default: 100,
                reqd: 1,
            },
            {
                fieldtype: 'Section Break',
                label: __('Assessment Criteria')
            },
            {
                label: __('Assessment Criteria'),
                fieldname: 'assessment_criteria',
                fieldtype: 'Table',
                reqd: 1,
                fields: [
                    {
                        label: __('Criteria'),
                        fieldname: 'assessment_criteria',
                        fieldtype: 'Link',
                        options: 'Assessment Criteria',
                        in_list_view: 1,
                        reqd: 1
                    },
                    {
                        label: __('Maximum Score'),
                        fieldname: 'maximum_score',
                        fieldtype: 'Float',
                        in_list_view: 1,
                        reqd: 1
                    }
                ]
            }
        ],
        primary_action_label: __('Create'),
        primary_action(values) {
            if (!values) return;

            frappe.call({
                method: "numerouno.numerouno.doctype.assessment_plan.assessment_plan.create_assessment_plan",
                args: {
                    student_group: frm.doc.name,
                    assessment_data: values
                },
                callback: function (r) {
                    if (!r.exc) {
                        frappe.show_alert({
                            message: __('Assessment Plan Created'),
                            indicator: 'green'
                        });
                        dialog.hide();

                        if (r.message) {
                            frappe.set_route('Form', 'Assessment Plan', r.message);
                        }
                    }
                },
                freeze: true,
                freeze_message: __('Creating Assessment Plan...')
            });
        }
    });

    dialog.show();

    // ✅ Use layout_ready to ensure child table is initialized
    dialog.$wrapper.on('shown.bs.modal', () => {
        const table_field = dialog.fields_dict.assessment_criteria.df;
        const table_data = dialog.get_value('assessment_criteria') || [];

        // Only add if no row is already there
        if (table_data.length === 0) {
            dialog.fields_dict.assessment_criteria.df.data = [
                {
                    assessment_criteria: 'Practical Assessment',
                    maximum_score: 100
                }
            ];
            dialog.fields_dict.assessment_criteria.grid.refresh();
        }
    });
}

function force_commit_child_table_edits(grid) {
    grid.grid_rows.forEach(row => {
        if (row.doc && row.doc.__unsaved) {
            row.doc = Object.assign(row.doc, row.get_values());
        }
    });
}

function force_commit_child_table_edits(grid) {
    grid.grid_rows.forEach(row => {
        if (row.doc && row.doc.__unsaved) {
            row.doc = Object.assign(row.doc, row.get_values());
        }
    });
}


function show_bulk_assessment_result_dialog(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __('Create Assessment Results (Bulk)'),
        fields: [
            {
                label: __('Assessment Plan'),
                fieldname: 'assessment_plan',
                fieldtype: 'Link',
                options: 'Assessment Plan',
                reqd: 1,
                get_query: () => ({
                    filters: {
                        docstatus: 1 // ✅ Only show submitted plans
                    }
                }),
                change() {
                    const plan = dialog.get_value('assessment_plan');
                    if (plan) {
                        frappe.call({
                            method: 'numerouno.numerouno.doctype.assessment_result.assessment_result.get_students_for_plan',
                            args: {
                                assessment_plan: plan
                            },
                            callback: function (r) {
                                if (r.message && r.message.length) {
                                    const data = r.message.map(student => ({
                                        student: student.name,
                                        student_name: student.student_name,
                                        assessment_criteria: 'Practical Assessment',
                                        score: '',
                                        comment: ''
                                    }));

                                    dialog.fields_dict.result_details.df.data = data;
                                    dialog.fields_dict.result_details.grid.refresh();
                                }
                            }
                        });
                    }
                }
            },
            {
                fieldtype: 'Section Break',
                label: __('Result Details')
            },
            {
                fieldtype: 'HTML',
                options: '<small style="color: gray;">💡 Tip: Press <b>Enter</b> after entering score/comment to save row.</small>'
            },
            {
                label: __('Student Scores'),
                fieldname: 'result_details',
                fieldtype: 'Table',
                cannot_add_rows: true,
                reqd: 1,
                fields: [
                    {
                        label: __('Student'),
                        fieldname: 'student',
                        fieldtype: 'Link',
                        options: 'Student',
                        in_list_view: 1,
                        read_only: 1
                    },
                    {
                        label: __('Student Name'),
                        fieldname: 'student_name',
                        fieldtype: 'Data',
                        in_list_view: 1,
                        read_only: 1
                    },
                    {
                        label: __('Assessment Criteria'),
                        fieldname: 'assessment_criteria',
                        fieldtype: 'Link',
                        options: 'Assessment Criteria',
                        in_list_view: 1
                    },
                    {
                        label: __('Score'),
                        fieldname: 'score',
                        fieldtype: 'Float',
                        in_list_view: 1,
                        reqd: 1
                    },
                    {
                        label: __('Comment'),
                        fieldname: 'comment',
                        fieldtype: 'Data',  // ✅ Changed to Data so it shows
                        in_list_view: 1
                    }
                ]
            }
        ],
        primary_action_label: __('Create Results'),
        primary_action() {
            const grid = dialog.fields_dict.result_details.grid;
        
            // ✅ Blur the active element to commit any last-moment edits
            document.activeElement.blur();
        
            const result_data = grid.get_data();
        
            console.log("✅ FINAL result_data:", result_data);
        
            if (!result_data || !result_data.length) {
                frappe.msgprint(__('Please fill in result details.'));
                return;
            }
        
            const incomplete = result_data.filter(r => r.score === '' || r.score === null || r.score === undefined);
            if (incomplete.length > 0) {
                frappe.msgprint(__('Some rows are missing score values. Please complete all rows before submitting.'));
                return;
            }
        
            frappe.call({
                method: 'numerouno.numerouno.doctype.assessment_result.assessment_result.create_bulk_assessment_results',
                args: {
                    assessment_plan: dialog.get_value('assessment_plan'),
                    results_data: result_data
                },
                callback: function (r) {
                    if (!r.exc) {
                        frappe.msgprint({
                            title: __('Success'),
                            message: __('Created {0} Assessment Result(s)', [r.message.length]),
                            indicator: 'green'
                        });
                        dialog.hide();
        
                        if (r.message.length) {
                            frappe.set_route('Form', 'Assessment Result', r.message[0]);
                        }
                    }
                },
                freeze: true,
                freeze_message: __('Creating Assessment Results...')
            });
        }
        
        
        
        
    });

    dialog.show();

    // ✅ Make dialog larger
    dialog.$wrapper.css('width', '90%');
    dialog.$wrapper.find('.modal-dialog').css('max-width', '95%');
}
