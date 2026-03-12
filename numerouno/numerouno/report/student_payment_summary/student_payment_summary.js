frappe.query_reports["Student Payment Summary"] = {
    "filters": [
        {
            "fieldname": "program",
            "label": __("Program"),
            "fieldtype": "Link",
            "options": "Program",
            "reqd": 0
        },
        {
            "fieldname": "course",
            "label": __("Course"),
            "fieldtype": "Link", 
            "options": "Course",
            "reqd": 0
        }
    ],
    
    // "formatter": function(value, row, column, data, default_formatter) {
    //     value = default_formatter(value, row, column, data);
        
    //     // Color code payment status with better alignment
    //     if (column.fieldname === "payment_status") {
    //         if (data.payment_status === "Paid") {
    //             value = `<span style="color: #27ae60; font-weight: bold; text-align: center; display: inline-block; width: 100%;">${value}</span>`;
    //         } else {
    //             value = `<span style="color: #e74c3c; font-weight: bold; text-align: center; display: inline-block; width: 100%;">${value}</span>`;
    //         }
    //     }
        
    //     // Color code days unpaid with better alignment
    //     if (column.fieldname === "days_unpaid" && data.days_unpaid > 0) {
    //         if (data.days_unpaid > 30) {
    //             value = `<span style="color: #e74c3c; font-weight: bold; text-align: center; display: inline-block; width: 100%;">${value}</span>`;
    //         } else if (data.days_unpaid > 15) {
    //             value = `<span style="color: #f39c12; font-weight: bold; text-align: center; display: inline-block; width: 100%;">${value}</span>`;
    //         } else {
    //             value = `<span style="color: #3498db; font-weight: bold; text-align: center; display: inline-block; width: 100%;">${value}</span>`;
    //         }
    //     }
        
    //     // Add subtle background color for alternating rows
    //     if (row.idx % 2 === 0) {
    //         value = `<div style="background-color: #f8f9fa; padding: 2px;">${value}</div>`;
    //     }
        
    //     return value;
    // },
    
    // "initial_depth": 0,
    // "is_tree": false,
    // "name_field": "student",
    // "parent_field": "student_group_name"
}; 