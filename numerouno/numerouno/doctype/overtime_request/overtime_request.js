// Copyright (c) 2026, mohtashim and contributors
// For license information, please see license.txt

const DEFAULT_HR_APPROVER = 't.samir@numerouno-me.com';

frappe.ui.form.on('Overtime Request', {
    onload(frm) {
        set_default_hr_approver(frm);
    },
    refresh(frm) {
        set_default_hr_approver(frm);
        format_time_fields(frm);
        add_change_listeners(frm);
    },
    onload_post_render(frm) {
        set_default_hr_approver(frm);
        format_time_fields(frm);
        add_change_listeners(frm);
    },
    validate(frm) {
        format_time_fields(frm);
    }
});

function set_default_hr_approver(frm) {
    if (!frm.doc.hr_approver) {
        frm.set_value('hr_approver', DEFAULT_HR_APPROVER);
    }
}

function format_time_fields(frm) {
    const fields = ['time_from', 'time_to'];

    fields.forEach(fieldname => {
        let value = frm.doc[fieldname];

        if (value && frm.fields_dict[fieldname] && frm.fields_dict[fieldname].$input) {
            let formatted_time = moment(value, ["HH:mm:ss", "HH:mm"]).format("hh:mm A");
            frm.fields_dict[fieldname].$input.val(formatted_time);
        }
    });
}

function add_change_listeners(frm) {
    const fields = ['time_from', 'time_to'];

    fields.forEach(fieldname => {
        if (frm.fields_dict[fieldname] && frm.fields_dict[fieldname].$input) {
            frm.fields_dict[fieldname].$input.off('blur.format12 change.format12');
            frm.fields_dict[fieldname].$input.on('blur.format12 change.format12', function() {
                format_time_fields(frm);
            });
        }
    });
}
