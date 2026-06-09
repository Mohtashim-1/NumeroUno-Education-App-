// Copyright (c) 2026, mohtashim and contributors
// For license information, please see license.txt

const STAFF_ROLE_FIELDS = {
	lead_instructor: "Lead Instructor",
	diver_1: "Diver",
	diver_2: "Diver",
	trainee_crane_operator: "Trainee Crane Operator",
	crane_operator: "Crane Operator",
	pool_safety_person: "Pool Safety Person",
};

frappe.ui.form.on("Staff Attendance", {
	onload(frm) {
		Object.entries(STAFF_ROLE_FIELDS).forEach(([fieldname, role]) => {
			frm.set_query(fieldname, () => ({
				query: "numerouno.numerouno.doctype.attendance_staff.attendance_staff.get_staff_by_role",
				filters: { role },
			}));
		});
	},
});
