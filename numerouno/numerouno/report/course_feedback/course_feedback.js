// Copyright (c) 2025, mohtashim and contributors
// For license information, please see license.txt

frappe.query_reports["Course Feedback"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 0
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 0
		},
		{
			"fieldname": "student",
			"label": __("Student"),
			"fieldtype": "Link",
			"options": "Student",
			"reqd": 0,
			"get_query": function() {
				return {
					filters: {
						"enabled": 1
					}
				}
			}
		},
		{
			"fieldname": "student_group",
			"label": __("Student Group"),
			"fieldtype": "Link",
			"options": "Student Group",
			"reqd": 0,
			"get_query": function() {
				return {
					filters: {
						"group_based_on": "Course"
					}
				}
			}
		},
		{
			"fieldname": "feedback_category",
			"label": __("Course Feedback Type"),
			"fieldtype": "Link",
			"options": "Course Feedback Type",
			"reqd": 0
		}
	],
	
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		// Color code feedback categories
		if (column.fieldname === "feedback_category") {
			const colors = {
				"Positive": "green",
				"Negative": "red", 
				"Suggestions": "blue",
				"Technical": "purple",
				"General": "gray",
				"Empty": "light-gray"
			};
			
			if (colors[data.feedback_category]) {
				value = `<span class="text-${colors[data.feedback_category]}">${value}</span>`;
			}
		}
		
		// Highlight long feedback
		if (column.fieldname === "feedback_length" && data.feedback_length > 100) {
			value = `<span class="text-bold">${value}</span>`;
		}
		
		return value;
	},
	
	"initial_depth": 0,
	
	"onload": function(report) {
		// Add custom button for export
		report.page.add_inner_button(__("Export to Excel"), function() {
			report.export_to_excel();
		});
		
		// Add custom button for feedback analysis
		report.page.add_inner_button(__("Feedback Analysis"), function() {
			show_feedback_analysis(report);
		});
	}
};

function show_feedback_analysis(report) {
	// Get the current data
	const data = report.data;
	
	if (!data || data.length === 0) {
		frappe.msgprint(__("No data available for analysis"));
		return;
	}
	
	// Calculate insights
	const insights = calculate_insights(data);
	
	// Show insights in a dialog
	const dialog = new frappe.ui.Dialog({
		title: __("Feedback Analysis Insights"),
		fields: [
			{
				fieldname: "insights",
				fieldtype: "HTML",
				options: insights
			}
		],
		size: "large"
	});
	
	dialog.show();
}

function calculate_insights(data) {
	let insights = "<div style='padding: 20px;'>";
	
	// Total feedback count
	insights += `<h4>📊 Overall Statistics</h4>`;
	insights += `<p><strong>Total Feedback:</strong> ${data.length}</p>`;
	
	// Unique students
	const unique_students = [...new Set(data.map(row => row.student))];
	insights += `<p><strong>Unique Students:</strong> ${unique_students.length}</p>`;
	
	// Category breakdown
	const categories = {};
	data.forEach(row => {
		const category = row.feedback_category || "Unknown";
		categories[category] = (categories[category] || 0) + 1;
	});
	
	insights += `<h4>📈 Category Breakdown</h4>`;
	Object.entries(categories).forEach(([category, count]) => {
		const percentage = ((count / data.length) * 100).toFixed(1);
		insights += `<p><strong>${category}:</strong> ${count} (${percentage}%)</p>`;
	});
	
	// Feedback length analysis
	const lengths = data.map(row => row.feedback_length || 0);
	const avgLength = (lengths.reduce((a, b) => a + b, 0) / lengths.length).toFixed(1);
	const maxLength = Math.max(...lengths);
	const minLength = Math.min(...lengths);
	
	insights += `<h4>📏 Feedback Length Analysis</h4>`;
	insights += `<p><strong>Average Length:</strong> ${avgLength} characters</p>`;
	insights += `<p><strong>Longest Feedback:</strong> ${maxLength} characters</p>`;
	insights += `<p><strong>Shortest Feedback:</strong> ${minLength} characters</p>`;
	
	// Most active students
	const studentCounts = {};
	data.forEach(row => {
		studentCounts[row.student] = (studentCounts[row.student] || 0) + 1;
	});
	
	const topStudents = Object.entries(studentCounts)
		.sort((a, b) => b[1] - a[1])
		.slice(0, 5);
	
	insights += `<h4>👥 Most Active Students</h4>`;
	topStudents.forEach(([student, count]) => {
		insights += `<p><strong>${student}:</strong> ${count} feedback</p>`;
	});
	
	// Date analysis
	const dates = data.map(row => row.posting_date).filter(Boolean);
	if (dates.length > 0) {
		const sortedDates = dates.sort();
		const firstDate = sortedDates[0];
		const lastDate = sortedDates[sortedDates.length - 1];
		
		insights += `<h4>📅 Date Range</h4>`;
		insights += `<p><strong>From:</strong> ${firstDate}</p>`;
		insights += `<p><strong>To:</strong> ${lastDate}</p>`;
	}
	
	insights += "</div>";
	return insights;
}
