# Copyright (c) 2025, mohtashim and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime, timedelta
import json

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	
	# Add summary data with business insights
	summary = get_business_insights(data, filters)
	
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
			"label": _("Length"),
			"fieldtype": "Int",
			"width": 80
		},
		{
			"fieldname": "sentiment_score",
			"label": _("Sentiment"),
			"fieldtype": "Float",
			"width": 100
		},
		{
			"fieldname": "feedback_category",
			"label": _("Category"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "priority_level",
			"label": _("Priority"),
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
	
	# Enhanced analysis for each row
	for row in data:
		# Add sentiment analysis
		row["sentiment_score"] = analyze_sentiment(row.get("feedback", ""))
		
		# Add feedback category
		if not row.get("course_feedback_type"):
			row["feedback_category"] = analyze_feedback_category(row.get("feedback", ""))
		else:
			row["feedback_category"] = row.get("course_feedback_type")
		
		# Add priority level
		row["priority_level"] = determine_priority(row.get("sentiment_score", 0), row.get("feedback_length", 0))
	
	return data

def analyze_sentiment(feedback):
	"""Analyze sentiment score from -1 (very negative) to 1 (very positive)"""
	if not feedback:
		return 0
	
	feedback_lower = feedback.lower()
	
	# Positive words with weights
	positive_words = {
		"excellent": 1.0, "amazing": 1.0, "fantastic": 1.0, "wonderful": 1.0,
		"great": 0.8, "good": 0.6, "nice": 0.5, "helpful": 0.7, "useful": 0.6,
		"love": 0.9, "enjoy": 0.7, "like": 0.5, "perfect": 1.0, "outstanding": 1.0
	}
	
	# Negative words with weights
	negative_words = {
		"terrible": -1.0, "awful": -1.0, "horrible": -1.0, "worst": -1.0,
		"bad": -0.6, "poor": -0.7, "hate": -0.9, "dislike": -0.6, "difficult": -0.4,
		"confusing": -0.5, "boring": -0.6, "useless": -0.8, "waste": -0.7
	}
	
	score = 0
	word_count = 0
	
	for word, weight in positive_words.items():
		if word in feedback_lower:
			score += weight
			word_count += 1
	
	for word, weight in negative_words.items():
		if word in feedback_lower:
			score += weight
			word_count += 1
	
	# Normalize score
	if word_count > 0:
		score = score / word_count
	
	# Cap at -1 to 1
	return max(-1.0, min(1.0, score))

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

def determine_priority(sentiment_score, feedback_length):
	"""Determine priority level based on sentiment and length"""
	if sentiment_score <= -0.5 and feedback_length > 50:
		return "High"
	elif sentiment_score <= -0.3 or feedback_length > 100:
		return "Medium"
	elif sentiment_score >= 0.5 and feedback_length > 30:
		return "Positive"
	else:
		return "Low"

def get_business_insights(data, filters):
	"""Generate business-focused insights"""
	if not data:
		return []
	
	total_feedback = len(data)
	
	# Sentiment analysis
	sentiment_scores = [row.get("sentiment_score", 0) for row in data]
	avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
	
	# Category distribution
	categories = {}
	for row in data:
		category = row.get("feedback_category", "Unknown")
		categories[category] = categories.get(category, 0) + 1
	
	# Priority distribution
	priorities = {}
	for row in data:
		priority = row.get("priority_level", "Low")
		priorities[priority] = priorities.get(priority, 0) + 1
	
	# Student engagement
	student_counts = {}
	for row in data:
		student = row.get("student")
		student_counts[student] = student_counts.get(student, 0) + 1
	
	most_engaged = max(student_counts.items(), key=lambda x: x[1]) if student_counts else ("None", 0)
	
	# Business insights
	insights = [
		{
			"value": total_feedback,
			"label": _("Total Feedback"),
			"datatype": "Int",
			"indicator": "Blue"
		},
		{
			"value": f"{avg_sentiment:.2f}",
			"label": _("Avg Sentiment Score"),
			"datatype": "Float",
			"indicator": "Green" if avg_sentiment > 0 else "Red"
		}
	]
	
	# Add priority breakdown
	for priority, count in priorities.items():
		percentage = (count / total_feedback) * 100 if total_feedback > 0 else 0
		indicator = "Red" if priority == "High" else "Orange" if priority == "Medium" else "Green"
		insights.append({
			"value": f"{count} ({percentage:.1f}%)",
			"label": f"{priority} Priority",
			"datatype": "Data",
			"indicator": indicator
		})
	
	# Add category insights
	for category, count in categories.items():
		percentage = (count / total_feedback) * 100 if total_feedback > 0 else 0
		insights.append({
			"value": f"{count} ({percentage:.1f}%)",
			"label": f"{category} Feedback",
			"datatype": "Data",
			"indicator": "Gray"
		})
	
	return insights
