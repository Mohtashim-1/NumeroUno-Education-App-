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
		}
	],
	
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		// Color code priority levels
		if (column.fieldname === "priority_level" && data && data.priority_level) {
			const colors = {
				"High": "red",
				"Medium": "orange", 
				"Low": "green"
			};
			
			if (colors[data.priority_level]) {
				value = `<span class="text-${colors[data.priority_level]} text-bold">${value}</span>`;
			}
		}
		
		// Color code negative percentage
		if (column.fieldname === "negative_percentage" && data && data.negative_percentage !== undefined) {
			const percentage = parseFloat(data.negative_percentage);
			if (!isNaN(percentage)) {
				if (percentage >= 50) {
					value = `<span class="text-red text-bold">${value}</span>`;
				} else if (percentage >= 25) {
					value = `<span class="text-orange text-bold">${value}</span>`;
				} else {
					value = `<span class="text-green">${value}</span>`;
				}
			}
		}
		
		// Color code average sentiment
		if (column.fieldname === "avg_sentiment" && data && data.avg_sentiment !== undefined) {
			const sentiment = parseFloat(data.avg_sentiment);
			if (!isNaN(sentiment)) {
				if (sentiment < -0.3) {
					value = `<span class="text-red">${value}</span>`;
				} else if (sentiment > 0.3) {
					value = `<span class="text-green">${value}</span>`;
				} else {
					value = `<span class="text-gray">${value}</span>`;
				}
			}
		}
		
		// Highlight action required based on priority
		if (column.fieldname === "action_required" && data && data.priority_level) {
			if (data.priority_level === "High") {
				value = `<span class="text-red text-bold">${value}</span>`;
			} else if (data.priority_level === "Medium") {
				value = `<span class="text-orange text-bold">${value}</span>`;
			} else {
				value = `<span class="text-green">${value}</span>`;
			}
		}
		
		return value;
	},
	
	"initial_depth": 0,
	
	"onload": function(report) {
		// Add custom buttons
		report.page.add_inner_button(__("Export to Excel"), function() {
			report.export_to_excel();
		});
		
		report.page.add_inner_button(__("Issue Summary"), function() {
			show_issue_summary(report);
		});
		
		report.page.add_inner_button(__("Action Plan"), function() {
			show_action_plan(report);
		});
	}
};

function show_issue_summary(report) {
	const data = report.data;
	
	if (!data || data.length === 0) {
		frappe.msgprint(__("No data available for analysis"));
		return;
	}
	
	const summary = generate_issue_summary(data);
	
	const dialog = new frappe.ui.Dialog({
		title: __("Feedback Type Issue Summary"),
		fields: [
			{
				fieldname: "summary",
				fieldtype: "HTML",
				options: summary
			}
		],
		size: "extra-large"
	});
	
	dialog.show();
}

function generate_issue_summary(data) {
	let summary = "<div style='padding: 20px;'>";
	
	// Executive Summary
	summary += `<h3 style='color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;'>📊 Executive Summary</h3>`;
	
	const total_types = data.length;
	const high_priority = data.filter(row => row.priority_level === "High");
	const medium_priority = data.filter(row => row.priority_level === "Medium");
	const total_negative_issues = data.reduce((sum, row) => sum + (row.negative_count || 0), 0);
	
	summary += `<p><strong>Total Feedback Types Analyzed:</strong> ${total_types}</p>`;
	summary += `<p><strong>High Priority Types:</strong> <span style='color: red; font-weight: bold;'>${high_priority.length}</span></p>`;
	summary += `<p><strong>Medium Priority Types:</strong> <span style='color: orange; font-weight: bold;'>${medium_priority.length}</span></p>`;
	summary += `<p><strong>Total Negative Issues:</strong> <span style='color: red; font-weight: bold;'>${total_negative_issues}</span></p>`;
	
	// High Priority Issues
	if (high_priority.length > 0) {
		summary += `<h4 style='color: #e74c3c; border-bottom: 1px solid #e74c3c; padding-bottom: 5px;'>🚨 CRITICAL ISSUES - IMMEDIATE ACTION REQUIRED</h4>`;
		high_priority.forEach(row => {
			summary += `<div style='background-color: #fdf2f2; padding: 10px; margin: 5px 0; border-left: 4px solid #e74c3c;'>`;
			summary += `<p><strong>${row.course_feedback_type || 'Unknown'}</strong></p>`;
			summary += `<p><strong>Negative Issues:</strong> ${row.negative_count || 0} (${(row.negative_percentage || 0).toFixed(1)}%)</p>`;
			summary += `<p><strong>Average Sentiment:</strong> ${row.avg_sentiment || 0}</p>`;
			summary += `<p><strong>Action:</strong> ${row.action_required || 'No action specified'}</p>`;
			summary += `<p><strong>Key Issues:</strong> ${row.key_issues || 'No key issues identified'}</p>`;
			summary += `</div>`;
		});
	}
	
	// Medium Priority Issues
	if (medium_priority.length > 0) {
		summary += `<h4 style='color: #f39c12; border-bottom: 1px solid #f39c12; padding-bottom: 5px;'>⚠️ MODERATE ISSUES - ATTENTION NEEDED</h4>`;
		medium_priority.forEach(row => {
			summary += `<div style='background-color: #fef9e7; padding: 10px; margin: 5px 0; border-left: 4px solid #f39c12;'>`;
			summary += `<p><strong>${row.course_feedback_type || 'Unknown'}</strong></p>`;
			summary += `<p><strong>Negative Issues:</strong> ${row.negative_count || 0} (${(row.negative_percentage || 0).toFixed(1)}%)</p>`;
			summary += `<p><strong>Action:</strong> ${row.action_required || 'No action specified'}</p>`;
			summary += `</div>`;
		});
	}
	
	// Most Problematic Type
	const most_problematic = data.reduce((max, row) => 
		(row.negative_percentage || 0) > (max.negative_percentage || 0) ? row : max, data[0]);
	
	if (most_problematic) {
		summary += `<h4 style='color: #8e44ad; border-bottom: 1px solid #8e44ad; padding-bottom: 5px;'>🎯 MOST PROBLEMATIC FEEDBACK TYPE</h4>`;
		summary += `<div style='background-color: #f4f1f8; padding: 15px; margin: 10px 0; border: 2px solid #8e44ad;'>`;
		summary += `<p><strong>Type:</strong> ${most_problematic.course_feedback_type || 'Unknown'}</p>`;
		summary += `<p><strong>Negative Percentage:</strong> <span style='color: red; font-weight: bold;'>${(most_problematic.negative_percentage || 0).toFixed(1)}%</span></p>`;
		summary += `<p><strong>Total Issues:</strong> ${most_problematic.negative_count || 0}</p>`;
		summary += `<p><strong>Priority:</strong> <span style='color: ${most_problematic.priority_level === "High" ? "red" : "orange"}; font-weight: bold;'>${most_problematic.priority_level || 'Unknown'}</span></p>`;
		summary += `<p><strong>Immediate Action:</strong> ${most_problematic.action_required || 'No action specified'}</p>`;
		summary += `</div>`;
	}
	
	summary += "</div>";
	return summary;
}

function show_action_plan(report) {
	const data = report.data;
	
	if (!data || data.length === 0) {
		frappe.msgprint(__("No data available for analysis"));
		return;
	}
	
	const action_plan = generate_action_plan(data);
	
	const dialog = new frappe.ui.Dialog({
		title: __("Strategic Action Plan"),
		fields: [
			{
				fieldname: "action_plan",
				fieldtype: "HTML",
				options: action_plan
			}
		],
		size: "extra-large"
	});
	
	dialog.show();
}

function generate_action_plan(data) {
	let action_plan = "<div style='padding: 20px;'>";
	
	action_plan += `<h3 style='color: #27ae60; border-bottom: 2px solid #27ae60; padding-bottom: 10px;'>🎯 STRATEGIC ACTION PLAN</h3>`;
	
	// Immediate Actions (High Priority)
	const high_priority = data.filter(row => row.priority_level === "High");
	if (high_priority.length > 0) {
		action_plan += `<h4 style='color: #e74c3c;'>🚨 IMMEDIATE ACTIONS (24-48 HOURS)</h4>`;
		action_plan += `<ol>`;
		high_priority.forEach((row, index) => {
			action_plan += `<li><strong>${row.course_feedback_type || 'Unknown'}:</strong> ${row.action_required || 'No action specified'}</li>`;
			action_plan += `<ul>`;
			action_plan += `<li>Review all negative feedback for this type</li>`;
			action_plan += `<li>Identify root causes of issues</li>`;
			action_plan += `<li>Implement immediate fixes where possible</li>`;
			action_plan += `<li>Assign dedicated resources for improvement</li>`;
			action_plan += `</ul>`;
		});
		action_plan += `</ol>`;
	}
	
	// Short-term Actions (Medium Priority)
	const medium_priority = data.filter(row => row.priority_level === "Medium");
	if (medium_priority.length > 0) {
		action_plan += `<h4 style='color: #f39c12;'>⚠️ SHORT-TERM ACTIONS (1-2 WEEKS)</h4>`;
		action_plan += `<ol>`;
		medium_priority.forEach((row, index) => {
			action_plan += `<li><strong>${row.course_feedback_type || 'Unknown'}:</strong> ${row.action_required || 'No action specified'}</li>`;
			action_plan += `<ul>`;
			action_plan += `<li>Analyze feedback patterns</li>`;
			action_plan += `<li>Develop improvement strategies</li>`;
			action_plan += `<li>Implement targeted solutions</li>`;
			action_plan += `</ul>`;
		});
		action_plan += `</ol>`;
	}
	
	// Long-term Strategy
	action_plan += `<h4 style='color: #3498db;'>📈 LONG-TERM STRATEGY (1-3 MONTHS)</h4>`;
	action_plan += `<ol>`;
	action_plan += `<li><strong>Continuous Monitoring:</strong> Set up regular feedback monitoring systems</li>`;
	action_plan += `<li><strong>Process Improvement:</strong> Establish feedback-driven improvement cycles</li>`;
	action_plan += `<li><strong>Training & Development:</strong> Address skill gaps identified in feedback</li>`;
	action_plan += `<li><strong>Communication:</strong> Improve communication channels with students</li>`;
	action_plan += `<li><strong>Quality Assurance:</strong> Implement quality checks for all feedback types</li>`;
	action_plan += `</ol>`;
	
	// Success Metrics
	action_plan += `<h4 style='color: #27ae60;'>📊 SUCCESS METRICS TO TRACK</h4>`;
	action_plan += `<ul>`;
	action_plan += `<li><strong>Reduction in Negative Feedback:</strong> Target 50% reduction in high-priority types</li>`;
	action_plan += `<li><strong>Improvement in Sentiment Scores:</strong> Target positive sentiment for all types</li>`;
	action_plan += `<li><strong>Response Time:</strong> Address high-priority issues within 48 hours</li>`;
	action_plan += `<li><strong>Student Satisfaction:</strong> Regular satisfaction surveys</li>`;
	action_plan += `</ul>`;
	
	// Resource Allocation
	action_plan += `<h4 style='color: #8e44ad;'>💼 RESOURCE ALLOCATION RECOMMENDATIONS</h4>`;
	action_plan += `<ul>`;
	if (high_priority.length > 0) {
		action_plan += `<li><strong>High Priority Types:</strong> Allocate 60% of resources to immediate fixes</li>`;
	}
	if (medium_priority.length > 0) {
		action_plan += `<li><strong>Medium Priority Types:</strong> Allocate 30% of resources to improvements</li>`;
	}
	action_plan += `<li><strong>Monitoring & Analysis:</strong> Allocate 10% of resources to ongoing monitoring</li>`;
	action_plan += `</ul>`;
	
	action_plan += "</div>";
	return action_plan;
}
