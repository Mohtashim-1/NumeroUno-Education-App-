// Copyright (c) 2025, mohtashim and contributors
// For license information, please see license.txt

frappe.ui.form.on("Practical Assesment", {
	refresh(frm) {
		// Set up student filtering when form loads
		setupStudentFiltering(frm);
	},

	student_group(frm) {
		// Clear student selection when student group changes
		frm.set_value('student', '');
		
		// Update student filter based on new student group
		updateStudentFilter(frm);
	}
});

function setupStudentFiltering(frm) {
	// Set up the student field with filtering
	updateStudentFilter(frm);
}

function updateStudentFilter(frm) {
	const studentGroup = frm.doc.student_group;
	
	// Set the get_query function for student field
	frm.set_query('student', function() {
		return {
			query: "numerouno.numerouno.doctype.practical_assesment.practical_assesment.get_students_by_group",
			filters: {
				student_group: studentGroup || ''
			}
		};
	});
}
