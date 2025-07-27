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
		
		// Color code sentiment scores
		if (column.fieldname === "sentiment_score") {
			const score = parseFloat(data.sentiment_score);
			if (score > 0.3) {
				value = `<span class="text-green">${value}</span>`;
			} else if (score < -0.3) {
				value = `<span class="text-red">${value}</span>`;
			} else {
				value = `<span class="text-gray">${value}</span>`;
			}
		}
		
		// Color code priority levels
		if (column.fieldname === "priority_level") {
			const colors = {
				"High": "red",
				"Medium": "orange", 
				"Low": "green",
				"Positive": "blue"
			};
			
			if (colors[data.priority_level]) {
				value = `<span class="text-${colors[data.priority_level]} text-bold">${value}</span>`;
			}
		}
		
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
		// Add custom buttons
		report.page.add_inner_button(__("Export to Excel"), function() {
			report.export_to_excel();
		});
		
		report.page.add_inner_button(__("Business Insights"), function() {
			show_business_insights(report);
		});
		
		report.page.add_inner_button(__("Issue Analysis"), function() {
			show_issue_analysis(report);
		});
		
		report.page.add_inner_button(__("Trend Analysis"), function() {
			show_trend_analysis(report);
		});
	}
};

function show_business_insights(report) {
	const data = report.data;
	
	if (!data || data.length === 0) {
		frappe.msgprint(__("No data available for analysis"));
		return;
	}
	
	const insights = calculate_business_insights(data);
	
	const dialog = new frappe.ui.Dialog({
		title: __("Business Intelligence Dashboard"),
		fields: [
			{
				fieldname: "insights",
				fieldtype: "HTML",
				options: insights
			}
		],
		size: "extra-large"
	});
	
	dialog.show();
}

function calculate_business_insights(data) {
	let insights = "<div style='padding: 20px;'>";
	
	// Executive Summary
	insights += `<h3 style='color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;'>📊 Executive Summary</h3>`;
	insights += `<p><strong>Total Feedback Analyzed:</strong> ${data.length}</p>`;
	
	// Sentiment Analysis
	const sentiment_scores = data.map(row => row.sentiment_score || 0);
	const avg_sentiment = (sentiment_scores.reduce((a, b) => a + b, 0) / sentiment_scores.length).toFixed(2);
	const positive_count = sentiment_scores.filter(s => s > 0.3).length;
	const negative_count = sentiment_scores.filter(s => s < -0.3).length;
	const neutral_count = sentiment_scores.filter(s => s >= -0.3 && s <= 0.3).length;
	
	insights += `<h4>🎯 Sentiment Analysis</h4>`;
	insights += `<p><strong>Average Sentiment:</strong> <span style='color: ${avg_sentiment > 0 ? 'green' : 'red'}; font-weight: bold;'>${avg_sentiment}</span></p>`;
	insights += `<p><strong>Positive Feedback:</strong> ${positive_count} (${((positive_count/data.length)*100).toFixed(1)}%)</p>`;
	insights += `<p><strong>Negative Feedback:</strong> ${negative_count} (${((negative_count/data.length)*100).toFixed(1)}%)</p>`;
	insights += `<p><strong>Neutral Feedback:</strong> ${neutral_count} (${((neutral_count/data.length)*100).toFixed(1)}%)</p>`;
	
	// Priority Analysis
	const priorities = {};
	data.forEach(row => {
		const priority = row.priority_level || "Low";
		priorities[priority] = (priorities[priority] || 0) + 1;
	});
	
	insights += `<h4>🚨 Priority Analysis</h4>`;
	Object.entries(priorities).forEach(([priority, count]) => {
		const percentage = ((count / data.length) * 100).toFixed(1);
		const color = priority === "High" ? "red" : priority === "Medium" ? "orange" : "green";
		insights += `<p><strong style='color: ${color};'>${priority} Priority:</strong> ${count} (${percentage}%)</p>`;
	});
	
	// Student Engagement
	const student_counts = {};
	data.forEach(row => {
		student_counts[row.student] = (student_counts[row.student] || 0) + 1;
	});
	
	const unique_students = Object.keys(student_counts).length;
	const avg_feedback_per_student = (data.length / unique_students).toFixed(1);
	const most_engaged = Object.entries(student_counts).sort((a, b) => b[1] - a[1])[0];
	
	insights += `<h4>👥 Student Engagement</h4>`;
	insights += `<p><strong>Unique Students:</strong> ${unique_students}</p>`;
	insights += `<p><strong>Average Feedback per Student:</strong> ${avg_feedback_per_student}</p>`;
	insights += `<p><strong>Most Engaged Student:</strong> ${most_engaged[0]} (${most_engaged[1]} feedback)</p>`;
	
	// Category Analysis
	const categories = {};
	data.forEach(row => {
		const category = row.feedback_category || "Unknown";
		categories[category] = (categories[category] || 0) + 1;
	});
	
	insights += `<h4>📋 Category Distribution</h4>`;
	Object.entries(categories).forEach(([category, count]) => {
		const percentage = ((count / data.length) * 100).toFixed(1);
		insights += `<p><strong>${category}:</strong> ${count} (${percentage}%)</p>`;
	});
	
	insights += "</div>";
	return insights;
}

function show_issue_analysis(report) {
	const data = report.data;
	
	if (!data || data.length === 0) {
		frappe.msgprint(__("No data available for analysis"));
		return;
	}
	
	const issues = identify_issues(data);
	
	const dialog = new frappe.ui.Dialog({
		title: __("Issue Analysis & Action Items"),
		fields: [
			{
				fieldname: "issues",
				fieldtype: "HTML",
				options: issues
			}
		],
		size: "extra-large"
	});
	
	dialog.show();
}

function identify_issues(data) {
	let issues = "<div style='padding: 20px;'>";
	
	// High Priority Issues
	const high_priority = data.filter(row => row.priority_level === "High");
	if (high_priority.length > 0) {
		issues += `<h3 style='color: #e74c3c; border-bottom: 2px solid #e74c3c; padding-bottom: 10px;'>🚨 Critical Issues Requiring Immediate Attention</h3>`;
		issues += `<p><strong>Count:</strong> ${high_priority.length} high-priority feedback items</p>`;
		issues += `<p><strong>Action Required:</strong> Immediate review and response</p>`;
		issues += `<ul>`;
		high_priority.slice(0, 5).forEach(row => {
			issues += `<li><strong>${row.student_name || row.student}:</strong> "${row.feedback.substring(0, 100)}..."</li>`;
		});
		issues += `</ul>`;
	}
	
	// Negative Sentiment Issues
	const negative_feedback = data.filter(row => (row.sentiment_score || 0) < -0.3);
	if (negative_feedback.length > 0) {
		issues += `<h3 style='color: #f39c12; border-bottom: 2px solid #f39c12; padding-bottom: 10px;'>⚠️ Negative Sentiment Issues</h3>`;
		issues += `<p><strong>Count:</strong> ${negative_feedback.length} negative feedback items</p>`;
		issues += `<p><strong>Action Required:</strong> Root cause analysis and improvement implementation</p>`;
	}
	
	// Student Group Issues
	const group_issues = {};
	data.forEach(row => {
		if (row.student_group) {
			if (!group_issues[row.student_group]) {
				group_issues[row.student_group] = [];
			}
			group_issues[row.student_group].push(row);
		}
	});
	
	const problematic_groups = Object.entries(group_issues).filter(([group, feedback]) => {
		const avg_sentiment = feedback.reduce((sum, row) => sum + (row.sentiment_score || 0), 0) / feedback.length;
		const high_priority_count = feedback.filter(row => row.priority_level === "High").length;
		return avg_sentiment < -0.2 || high_priority_count > 0;
	});
	
	if (problematic_groups.length > 0) {
		issues += `<h3 style='color: #9b59b6; border-bottom: 2px solid #9b59b6; padding-bottom: 10px;'>👥 Student Group Issues</h3>`;
		problematic_groups.forEach(([group, feedback]) => {
			const avg_sentiment = feedback.reduce((sum, row) => sum + (row.sentiment_score || 0), 0) / feedback.length;
			const high_priority_count = feedback.filter(row => row.priority_level === "High").length;
			issues += `<p><strong>${group}:</strong> ${high_priority_count} high-priority issues, avg sentiment: ${avg_sentiment.toFixed(2)}</p>`;
		});
	}
	
	// Engagement Issues
	const student_counts = {};
	data.forEach(row => {
		student_counts[row.student] = (student_counts[row.student] || 0) + 1;
	});
	
	const low_engagement = Object.entries(student_counts).filter(([student, count]) => count === 1);
	if (low_engagement.length > Object.keys(student_counts).length * 0.7) {
		issues += `<h3 style='color: #3498db; border-bottom: 2px solid #3498db; padding-bottom: 10px;'>📉 Engagement Issues</h3>`;
		issues += `<p><strong>Issue:</strong> Low student engagement - ${low_engagement.length} students only provided 1 feedback</p>`;
		issues += `<p><strong>Action Required:</strong> Implement strategies to increase feedback participation</p>`;
	}
	
	// Recommendations
	issues += `<h3 style='color: #27ae60; border-bottom: 2px solid #27ae60; padding-bottom: 10px;'>💡 Strategic Recommendations</h3>`;
	issues += `<ol>`;
	if (high_priority.length > 0) {
		issues += `<li><strong>Immediate Action:</strong> Address all high-priority feedback within 24-48 hours</li>`;
	}
	if (negative_feedback.length > 0) {
		issues += `<li><strong>Process Improvement:</strong> Conduct root cause analysis for negative feedback patterns</li>`;
	}
	if (problematic_groups.length > 0) {
		issues += `<li><strong>Targeted Support:</strong> Provide additional support to problematic student groups</li>`;
	}
	issues += `<li><strong>Feedback Culture:</strong> Encourage more frequent and constructive feedback</li>`;
	issues += `<li><strong>Monitoring:</strong> Set up regular feedback monitoring and alert systems</li>`;
	issues += `</ol>`;
	
	issues += "</div>";
	return issues;
}

function show_trend_analysis(report) {
	const data = report.data;
	
	if (!data || data.length === 0) {
		frappe.msgprint(__("No data available for analysis"));
		return;
	}
	
	const trends = calculate_trends(data);
	
	const dialog = new frappe.ui.Dialog({
		title: __("Trend Analysis"),
		fields: [
			{
				fieldname: "trends",
				fieldtype: "HTML",
				options: trends
			}
		],
		size: "large"
	});
	
	dialog.show();
}

function calculate_trends(data) {
	let trends = "<div style='padding: 20px;'>";
	
	// Group by date
	const date_groups = {};
	data.forEach(row => {
		const date = row.posting_date;
		if (date) {
			if (!date_groups[date]) {
				date_groups[date] = [];
			}
			date_groups[date].push(row);
		}
	});
	
	const sorted_dates = Object.keys(date_groups).sort();
	
	if (sorted_dates.length > 1) {
		// Sentiment trend
		const first_sentiment = date_groups[sorted_dates[0]].reduce((sum, row) => sum + (row.sentiment_score || 0), 0) / date_groups[sorted_dates[0]].length;
		const last_sentiment = date_groups[sorted_dates[sorted_dates.length - 1]].reduce((sum, row) => sum + (row.sentiment_score || 0), 0) / date_groups[sorted_dates[sorted_dates.length - 1]].length;
		const sentiment_change = last_sentiment - first_sentiment;
		
		trends += `<h3 style='color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;'>📈 Trend Analysis</h3>`;
		
		if (sentiment_change > 0.1) {
			trends += `<p style='color: green; font-weight: bold;'>📈 Sentiment is improving (+${sentiment_change.toFixed(2)})</p>`;
		} else if (sentiment_change < -0.1) {
			trends += `<p style='color: red; font-weight: bold;'>📉 Sentiment is declining (${sentiment_change.toFixed(2)})</p>`;
		} else {
			trends += `<p style='color: gray; font-weight: bold;'>➡️ Sentiment is stable (${sentiment_change.toFixed(2)})</p>`;
		}
		
		// Volume trend
		const first_volume = date_groups[sorted_dates[0]].length;
		const last_volume = date_groups[sorted_dates[sorted_dates.length - 1]].length;
		const volume_change = ((last_volume - first_volume) / first_volume) * 100;
		
		if (volume_change > 20) {
			trends += `<p style='color: green; font-weight: bold;'>📈 Feedback volume is increasing (+${volume_change.toFixed(1)}%)</p>`;
		} else if (volume_change < -20) {
			trends += `<p style='color: red; font-weight: bold;'>📉 Feedback volume is decreasing (${volume_change.toFixed(1)}%)</p>`;
		} else {
			trends += `<p style='color: gray; font-weight: bold;'>➡️ Feedback volume is stable (${volume_change.toFixed(1)}%)</p>`;
		}
		
		// Daily breakdown
		trends += `<h4>📅 Daily Breakdown</h4>`;
		trends += `<table style='width: 100%; border-collapse: collapse;'>`;
		trends += `<tr style='background-color: #f8f9fa;'><th style='border: 1px solid #ddd; padding: 8px;'>Date</th><th style='border: 1px solid #ddd; padding: 8px;'>Count</th><th style='border: 1px solid #ddd; padding: 8px;'>Avg Sentiment</th><th style='border: 1px solid #ddd; padding: 8px;'>High Priority</th></tr>`;
		
		sorted_dates.forEach(date => {
			const day_data = date_groups[date];
			const avg_sentiment = day_data.reduce((sum, row) => sum + (row.sentiment_score || 0), 0) / day_data.length;
			const high_priority = day_data.filter(row => row.priority_level === "High").length;
			
			trends += `<tr>`;
			trends += `<td style='border: 1px solid #ddd; padding: 8px;'>${date}</td>`;
			trends += `<td style='border: 1px solid #ddd; padding: 8px;'>${day_data.length}</td>`;
			trends += `<td style='border: 1px solid #ddd; padding: 8px; color: ${avg_sentiment > 0 ? 'green' : avg_sentiment < 0 ? 'red' : 'gray'};'>${avg_sentiment.toFixed(2)}</td>`;
			trends += `<td style='border: 1px solid #ddd; padding: 8px; color: ${high_priority > 0 ? 'red' : 'green'};'>${high_priority}</td>`;
			trends += `</tr>`;
		});
		
		trends += `</table>`;
	} else {
		trends += `<p>Insufficient data for trend analysis. Need at least 2 days of data.</p>`;
	}
	
	trends += "</div>";
	return trends;
}
