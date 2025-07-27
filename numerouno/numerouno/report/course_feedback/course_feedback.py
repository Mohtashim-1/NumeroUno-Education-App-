# Copyright (c) 2025, mohtashim and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime, timedelta

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	
	# Add summary data
	summary = get_summary(data, filters)
	
	return columns, data, None, None, summary

def get_columns():
	return [
		{
			"fieldname": "posting_date",
			"label": _("Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "student",
			"label": _("Student"),
			"fieldtype": "Link",
			"options": "Student",
			"width": 150
		},
		{
			"fieldname": "student_name",
			"label": _("Student Name"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "student_group",
			"label": _("Student Group"),
			"fieldtype": "Link",
			"options": "Student Group",
			"width": 150
		},
		{
			"fieldname": "feedback",
			"label": _("Feedback"),
			"fieldtype": "Text",
			"width": 300
		},
		{
			"fieldname": "feedback_length",
			"label": _("Feedback Length"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "feedback_category",
			"label": _("Category"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "posting_time",
			"label": _("Time"),
			"fieldtype": "Time",
			"width": 100
		}
	]

def get_data(filters):
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("cf.posting_date >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("cf.posting_date <= %(to_date)s")
	if filters.get("student"):
		conditions.append("cf.student = %(student)s")
	if filters.get("student_group"):
		conditions.append("cf.student_group = %(student_group)s")
	if filters.get("feedback_category"):
		conditions.append("cf.course_feedback_type = %(feedback_category)s")
	
	where_clause = " AND ".join(conditions) if conditions else "1=1"
	
	query = f"""
		SELECT 
			cf.posting_date,
			cf.student,
			s.student_name,
			cf.student_group,
			cf.feedback,
			LENGTH(cf.feedback) as feedback_length,
			cf.course_feedback_type,
			cf.posting_time
		FROM `tabCourse Feedback` cf
		LEFT JOIN `tabStudent` s ON cf.student = s.name
		WHERE {where_clause}
		ORDER BY cf.posting_date DESC, cf.posting_time DESC
	"""
	
	data = frappe.db.sql(query, filters, as_dict=1)
	
	# Add feedback category analysis if course_feedback_type is empty
	for row in data:
		if not row.get("course_feedback_type"):
			row["feedback_category"] = analyze_feedback_category(row.get("feedback", ""))
		else:
			row["feedback_category"] = row.get("course_feedback_type")
	
	return data

def analyze_feedback_category(feedback):
	"""Analyze feedback and categorize it based on content"""
	if not feedback:
		return "Empty"
	
	feedback_lower = feedback.lower()
	
	# Define categories based on keywords
	categories = {
		"Positive": ["good", "great", "excellent", "amazing", "wonderful", "fantastic", "love", "enjoy", "helpful", "useful"],
		"Negative": ["bad", "poor", "terrible", "awful", "hate", "dislike", "difficult", "confusing", "boring", "useless"],
		"Suggestions": ["suggest", "improve", "better", "change", "modify", "add", "remove", "update"],
		"Technical": ["technical", "code", "programming", "software", "system", "bug", "error", "issue"],
		"General": ["course", "class", "learning", "study", "education", "teacher", "instructor"]
	}
	
	for category, keywords in categories.items():
		if any(keyword in feedback_lower for keyword in keywords):
			return category
	
	return "General"

def get_summary(data, filters):
	"""Generate summary statistics"""
	if not data:
		return []
	
	total_feedback = len(data)
	total_students = len(set(row.get("student") for row in data))
	total_groups = len(set(row.get("student_group") for row in data))
	
	# Calculate average feedback length
	feedback_lengths = [row.get("feedback_length", 0) for row in data]
	avg_length = sum(feedback_lengths) / len(feedback_lengths) if feedback_lengths else 0
	
	# Category distribution
	categories = {}
	for row in data:
		category = row.get("feedback_category", "Unknown")
		categories[category] = categories.get(category, 0) + 1
	
	# Most active students
	student_counts = {}
	for row in data:
		student = row.get("student")
		student_counts[student] = student_counts.get(student, 0) + 1
	
	most_active_student = max(student_counts.items(), key=lambda x: x[1]) if student_counts else ("None", 0)
	
	# Date range
	dates = [row.get("posting_date") for row in data if row.get("posting_date")]
	min_date = min(dates) if dates else None
	max_date = max(dates) if dates else None
	
	summary = [
		{
			"value": total_feedback,
			"label": _("Total Feedback"),
			"datatype": "Int",
			"indicator": "Blue"
		},
		{
			"value": total_students,
			"label": _("Unique Students"),
			"datatype": "Int",
			"indicator": "Green"
		},
		{
			"value": total_groups,
			"label": _("Student Groups"),
			"datatype": "Int",
			"indicator": "Orange"
		},
		{
			"value": round(avg_length, 1),
			"label": _("Avg Feedback Length"),
			"datatype": "Float",
			"indicator": "Purple"
		}
	]
	
	# Add category breakdown
	for category, count in categories.items():
		percentage = (count / total_feedback) * 100 if total_feedback > 0 else 0
		summary.append({
			"value": f"{count} ({percentage:.1f}%)",
			"label": f"{category} Feedback",
			"datatype": "Data",
			"indicator": "Gray"
		})
	
	# Add most active student
	if most_active_student[1] > 1:
		summary.append({
			"value": f"{most_active_student[0]} ({most_active_student[1]} feedback)",
			"label": _("Most Active Student"),
			"datatype": "Data",
			"indicator": "Yellow"
		})
	
	# Add date range
	if min_date and max_date:
		summary.append({
			"value": f"{min_date} to {max_date}",
			"label": _("Date Range"),
			"datatype": "Data",
			"indicator": "Gray"
		})
	
	return summary
