// Copyright (c) 2025, mohtashim and contributors
// For license information, please see license.txt

frappe.ui.form.on("Practical Assesment", {
	refresh(frm) {
		// Set up student filtering when form loads
		setupStudentFiltering(frm);
		
		// Set up student group filtering based on instructor assignment
		setupStudentGroupFiltering(frm);
	},

	student_group(frm) {
		// Clear student selection when student group changes
		frm.set_value('student', '');
		
		// Update student filter based on new student group
		updateStudentFilter(frm);
	}
});

// Handle changes in the practical assessment table
frappe.ui.form.on("Practical Assesment Table", {
	mark(frm, cdt, cdn) {
		// When mark checkbox changes, update total_marks
		updateTotalMarks(frm);
	},
	
	assesment_type(frm, cdt, cdn) {
		// When assessment type changes, update total_marks
		updateTotalMarks(frm);
	}
});

function updateTotalMarks(frm) {
	// Calculate total marks from checked items using the formula
	// Formula: total_marks = (maximum_score / total_items) * checked_items
	let checked_items = 0;
	let total_items = 0;
	
	if (frm.doc.practical_assesment_table) {
		frm.doc.practical_assesment_table.forEach(function(row) {
			if (row.mark) {
				checked_items += 1;
			}
			total_items += 1;
		});
	}
	
	// Calculate total marks using the formula
	let total_marks = 0;
	if (total_items > 0 && frm.doc.maximum_score) {
		const marks_per_item = frm.doc.maximum_score / total_items;
		total_marks = marks_per_item * checked_items;
		total_marks = Math.round(total_marks * 100) / 100; // Round to 2 decimal places
	}
	
	// Update the total_marks field (only if it exists)
	if (frm.get_field('total_marks')) {
		frm.set_value('total_marks', total_marks);
		frm.refresh_field('total_marks');
	}
	
	// Update total_score field (only if it exists)
	if (frm.get_field('total_score')) {
		frm.set_value('total_score', total_marks);
		frm.refresh_field('total_score');
	}
}

function setupStudentFiltering(frm) {
	updateStudentFilter(frm);
}

function setupStudentGroupFiltering(frm) {
	// Set the get_query function for student_group field
	// This will filter student groups to only show those where the user is assigned as instructor
	frm.set_query('student_group', function() {
		return {
			query: "numerouno.numerouno.doctype.practical_assesment.practical_assesment.get_student_groups_for_instructor"
		};
	});
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
