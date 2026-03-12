# Copyright (c) 2025, mohtashim and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime, timedelta
import requests
import json
import time
from .ai_config import get_ai_config, is_ai_available

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	summary = get_feedback_type_summary(data, filters)
	
	return columns, data, None, None, summary

def print_report():
	"""Print the course feedback report to console"""
	
	print("=" * 80)
	print("📊 COURSE FEEDBACK REPORT")
	print("=" * 80)
	
	try:
		# Get raw data from database
		query = """
			SELECT 
				cf.course_feedback_type,
				cf.feedback,
				cf.posting_date,
				cf.student,
				cf.student_group,
				LENGTH(cf.feedback) as feedback_length
			FROM `tabCourse Feedback` cf
			WHERE cf.course_feedback_type IS NOT NULL
			ORDER BY cf.course_feedback_type, cf.posting_date DESC
		"""
		
		raw_data = frappe.db.sql(query, as_dict=1)
		
		print(f"\n📈 RAW DATA FOUND: {len(raw_data)} feedback entries")
		
		if not raw_data:
			print("❌ No course feedback data found in database!")
			return
		
		# Group by feedback type
		feedback_types = {}
		for row in raw_data:
			feedback_type = row.get("course_feedback_type")
			if feedback_type not in feedback_types:
				feedback_types[feedback_type] = []
			feedback_types[feedback_type].append(row)
		
		print(f"\n📋 FEEDBACK TYPES FOUND: {len(feedback_types)}")
		print("-" * 50)
		
		for feedback_type, entries in feedback_types.items():
			print(f"\n🎯 {feedback_type.upper()}:")
			print(f"   Total Entries: {len(entries)}")
			
			# Analyze sentiment
			negative_count = 0
			sentiment_scores = []
			
			for entry in entries:
				feedback = entry.get("feedback", "")
				sentiment = analyze_sentiment(feedback)
				sentiment_scores.append(sentiment)
				
				if sentiment < -0.3:
					negative_count += 1
			
			negative_percentage = (negative_count / len(entries)) * 100 if entries else 0
			avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
			
			print(f"   Negative Count: {negative_count}")
			print(f"   Negative Percentage: {negative_percentage:.1f}%")
			print(f"   Average Sentiment: {avg_sentiment:.2f}")
			
			# Priority level
			if negative_percentage >= 50 or avg_sentiment <= -0.5:
				priority = "🔴 HIGH"
			elif negative_percentage >= 25 or avg_sentiment <= -0.2:
				priority = "🟡 MEDIUM"
			else:
				priority = "🟢 LOW"
			
			print(f"   Priority Level: {priority}")
			
			# Show sample feedback
			print(f"   Sample Feedback:")
			for i, entry in enumerate(entries[:3]):  # Show first 3
				feedback = entry.get("feedback", "")
				student = entry.get("student", "")
				sentiment = sentiment_scores[i]
				sentiment_emoji = "😞" if sentiment < -0.3 else "😊" if sentiment > 0.3 else "😐"
				print(f"     {sentiment_emoji} {student}: {feedback[:100]}{'...' if len(feedback) > 100 else ''}")
		
		# Summary
		print(f"\n📊 OVERALL SUMMARY:")
		print("-" * 30)
		total_feedback = len(raw_data)
		total_negative = sum(1 for row in raw_data if analyze_sentiment(row.get("feedback", "")) < -0.3)
		overall_negative_percentage = (total_negative / total_feedback) * 100 if total_feedback > 0 else 0
		
		print(f"Total Feedback: {total_feedback}")
		print(f"Total Negative: {total_negative}")
		print(f"Overall Negative Rate: {overall_negative_percentage:.1f}%")
		
		# Most problematic type
		most_problematic = max(feedback_types.items(), 
							 key=lambda x: sum(1 for entry in x[1] if analyze_sentiment(entry.get("feedback", "")) < -0.3) / len(x[1]) * 100)
		
		problematic_percentage = (sum(1 for entry in most_problematic[1] if analyze_sentiment(entry.get("feedback", "")) < -0.3) / len(most_problematic[1])) * 100
		
		print(f"Most Problematic Type: {most_problematic[0]} ({problematic_percentage:.1f}% negative)")
		
		print("\n" + "=" * 80)
		print("✅ Report printed successfully!")
		
	except Exception as e:
		print(f"❌ Error: {str(e)}")
		import traceback
		traceback.print_exc()

def get_columns():
	return [
		{
			"fieldname": "course_feedback_type",
			"label": _("Feedback Type"),
			"fieldtype": "Link",
			"options": "Course Feedback Type",
			"width": 200
		},
		{
			"fieldname": "total_feedback",
			"label": _("Total Feedback"),
			"fieldtype": "Int",
			"width": 120
		},
		{
			"fieldname": "negative_count",
			"label": _("Negative Issues"),
			"fieldtype": "Int",
			"width": 120
		},
		{
			"fieldname": "negative_percentage",
			"label": _("Negative %"),
			"fieldtype": "Percent",
			"width": 100
		},
		{
			"fieldname": "avg_sentiment",
			"label": _("Avg Sentiment"),
			"fieldtype": "Float",
			"width": 120
		},
		{
			"fieldname": "priority_level",
			"label": _("Priority Level"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "ai_analysis",
			"label": _("AI Analysis"),
			"fieldtype": "Text",
			"width": 300
		},
		{
			"fieldname": "key_issues",
			"label": _("Key Issues"),
			"fieldtype": "Text",
			"width": 300
		},
		{
			"fieldname": "action_required",
			"label": _("Action Required"),
			"fieldtype": "Text",
			"width": 200
		}
	]

def get_data(filters):
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("cf.posting_date >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("cf.posting_date <= %(to_date)s")
	if filters.get("student_group"):
		conditions.append("cf.student_group = %(student_group)s")
	
	where_clause = " AND ".join(conditions) if conditions else "1=1"
	
	query = f"""
		SELECT 
			cf.course_feedback_type,
			cf.feedback,
			cf.posting_date,
			cf.student,
			cf.student_group,
			LENGTH(cf.feedback) as feedback_length
		FROM `tabCourse Feedback` cf
		WHERE {where_clause} AND cf.course_feedback_type IS NOT NULL
		ORDER BY cf.course_feedback_type, cf.posting_date DESC
	"""
	
	raw_data = frappe.db.sql(query, filters, as_dict=1)
	
	# Group by feedback type and analyze
	feedback_type_analysis = {}
	
	for row in raw_data:
		feedback_type = row.get("course_feedback_type")
		if not feedback_type:
			continue
			
		if feedback_type not in feedback_type_analysis:
			feedback_type_analysis[feedback_type] = {
				"feedbacks": [],
				"total_count": 0,
				"negative_count": 0,
				"sentiment_scores": [],
				"issues": [],
				"all_feedback_text": []
			}
		
		# Analyze sentiment
		sentiment_score = analyze_sentiment(row.get("feedback", ""))
		is_negative = sentiment_score < -0.3
		
		feedback_type_analysis[feedback_type]["feedbacks"].append(row)
		feedback_type_analysis[feedback_type]["total_count"] += 1
		feedback_type_analysis[feedback_type]["sentiment_scores"].append(sentiment_score)
		feedback_type_analysis[feedback_type]["all_feedback_text"].append(row.get("feedback", ""))
		
		if is_negative:
			feedback_type_analysis[feedback_type]["negative_count"] += 1
			feedback_type_analysis[feedback_type]["issues"].append({
				"feedback": row.get("feedback", ""),
				"student": row.get("student"),
				"sentiment": sentiment_score
			})
	
	# Convert to report data
	report_data = []
	
	for feedback_type, analysis in feedback_type_analysis.items():
		total_feedback = analysis["total_count"]
		negative_count = analysis["negative_count"]
		negative_percentage = (negative_count / total_feedback) * 100 if total_feedback > 0 else 0
		avg_sentiment = sum(analysis["sentiment_scores"]) / len(analysis["sentiment_scores"]) if analysis["sentiment_scores"] else 0
		
		# Determine priority level
		priority_level = determine_priority_level(negative_percentage, avg_sentiment, total_feedback)
		
		# Get AI analysis
		ai_analysis = get_ai_analysis(feedback_type, analysis["all_feedback_text"], negative_percentage)
		
		# Extract key issues
		key_issues = extract_key_issues(analysis["issues"])
		
		# Determine action required
		action_required = determine_action_required(priority_level, negative_percentage, avg_sentiment)
		
		report_data.append({
			"course_feedback_type": feedback_type,
			"total_feedback": total_feedback,
			"negative_count": negative_count,
			"negative_percentage": negative_percentage,
			"avg_sentiment": round(avg_sentiment, 2),
			"priority_level": priority_level,
			"ai_analysis": ai_analysis,
			"key_issues": key_issues,
			"action_required": action_required
		})
	
	# Sort by priority (High, Medium, Low)
	priority_order = {"High": 1, "Medium": 2, "Low": 3}
	report_data.sort(key=lambda x: (priority_order.get(x["priority_level"], 4), -x["negative_percentage"]))
	
	return report_data

def get_ai_analysis(feedback_type, feedback_texts, negative_percentage):
	"""Get AI analysis using configured API"""
	try:
		# Combine all feedback texts
		combined_feedback = " ".join([text for text in feedback_texts if text.strip()])
		
		if not combined_feedback:
			return "No feedback content to analyze"
		
		# Check if AI is available
		if not is_ai_available():
			return get_enhanced_fallback_analysis(feedback_type, combined_feedback, negative_percentage, feedback_texts)
		
		config = get_ai_config()
		if not config:
			return get_enhanced_fallback_analysis(feedback_type, combined_feedback, negative_percentage, feedback_texts)
		
		# Try different AI providers based on configuration
		if "gemini" in config.get("api_url", "").lower():
			return call_gemini_api(config, feedback_type, combined_feedback, negative_percentage)
		elif "huggingface" in config.get("api_url", "").lower():
			return call_huggingface_api(config, combined_feedback)
		elif "openai" in config.get("api_url", "").lower():
			return call_openai_api(config, combined_feedback)
		else:
			return call_generic_api(config, combined_feedback)
			
	except Exception as e:
		return get_enhanced_fallback_analysis(feedback_type, combined_feedback, negative_percentage, feedback_texts)

def call_gemini_api(config, feedback_type, combined_feedback, negative_percentage):
	"""Call Google Gemini API"""
	try:
		headers = {
			"Content-Type": "application/json",
			"X-goog-api-key": config["api_key"]
		}
		
		# Prepare the prompt for Gemini
		prompt = f"""
		Analyze this course feedback for '{feedback_type}' type and provide a concise business analysis:

		Feedback Content: {combined_feedback[:2000]}
		
		Negative Percentage: {negative_percentage:.1f}%
		
		Please provide a structured analysis with:
		1. Priority level (Critical/High/Medium/Low)
		2. Key themes and patterns found
		3. Main issues and complaints
		4. Specific recommendations for improvement
		5. Overall sentiment assessment
		
		Format the response with clear sections and bullet points. Keep it concise and actionable for business decision making.
		"""
		
		payload = {
			"contents": [
				{
					"parts": [
						{
							"text": prompt
						}
					]
				}
			],
			"generationConfig": {
				"maxOutputTokens": config.get("max_tokens", 500),
				"temperature": config.get("temperature", 0.7)
			}
		}
		
		response = requests.post(config["api_url"], headers=headers, json=payload, timeout=15)
		
		if response.status_code == 200:
			result = response.json()
			
			# Extract the generated text from Gemini response
			if "candidates" in result and len(result["candidates"]) > 0:
				candidate = result["candidates"][0]
				if "content" in candidate and "parts" in candidate["content"]:
					parts = candidate["content"]["parts"]
					if len(parts) > 0 and "text" in parts[0]:
						return parts[0]["text"]
			
			return "AI analysis completed successfully"
		else:
			error_msg = f"Gemini API Error {response.status_code}: {response.text}"
			print(error_msg)
			return get_enhanced_fallback_analysis(feedback_type, combined_feedback, negative_percentage, [combined_feedback])
			
	except Exception as e:
		error_msg = f"Gemini API error: {str(e)}"
		print(error_msg)
		return get_enhanced_fallback_analysis(feedback_type, combined_feedback, negative_percentage, [combined_feedback])

def get_enhanced_fallback_analysis(feedback_type, feedback_text, negative_percentage, feedback_texts):
	"""Enhanced fallback analysis with better insights"""
	analysis = f"📊 **{feedback_type} Feedback Analysis**\n\n"
	
	# Priority assessment
	if negative_percentage > 50:
		analysis += "🔴 **CRITICAL PRIORITY**\n"
		analysis += "• High negative feedback detected\n"
		analysis += "• Immediate attention required\n"
		analysis += "• Root cause analysis needed\n\n"
	elif negative_percentage > 25:
		analysis += "🟡 **MODERATE PRIORITY**\n"
		analysis += "• Moderate negative feedback\n"
		analysis += "• Review and improvement needed\n"
		analysis += "• Monitor trends closely\n\n"
	else:
		analysis += "🟢 **LOW PRIORITY**\n"
		analysis += "• Low negative feedback\n"
		analysis += "• Continue current practices\n"
		analysis += "• Minor optimizations only\n\n"
	
	# Key themes analysis
	analysis += "🎯 **Key Themes Identified:**\n"
	
	# Common words analysis
	words = feedback_text.lower().split()
	negative_words = ['bad', 'poor', 'terrible', 'awful', 'hate', 'difficult', 'confusing', 'boring', 'useless', 'problem', 'issue', 'complaint', 'disappointed', 'frustrated']
	positive_words = ['good', 'great', 'excellent', 'amazing', 'helpful', 'useful', 'love', 'enjoy', 'like', 'perfect', 'outstanding']
	
	found_negative = [word for word in negative_words if word in words]
	found_positive = [word for word in positive_words if word in words]
	
	if found_negative:
		analysis += f"• Negative themes: {', '.join(found_negative[:5])}\n"
	if found_positive:
		analysis += f"• Positive themes: {', '.join(found_positive[:5])}\n"
	
	# Feedback length analysis
	avg_length = sum(len(text) for text in feedback_texts) / len(feedback_texts) if feedback_texts else 0
	if avg_length > 100:
		analysis += "• Detailed feedback provided\n"
	elif avg_length > 50:
		analysis += "• Moderate feedback detail\n"
	else:
		analysis += "• Brief feedback responses\n"
	
	# Specific issues from negative feedback
	if negative_percentage > 0:
		analysis += f"\n⚠️ **Specific Issues:**\n"
		analysis += f"• {negative_percentage:.1f}% of feedback is negative\n"
		analysis += f"• {len(feedback_texts)} total feedback entries\n"
		analysis += f"• {int(negative_percentage * len(feedback_texts) / 100)} negative responses\n"
	
	# Recommendations
	analysis += f"\n💡 **Recommendations:**\n"
	if negative_percentage > 50:
		analysis += "• Conduct immediate user interviews\n"
		analysis += "• Review and redesign the process\n"
		analysis += "• Implement quick fixes for urgent issues\n"
		analysis += "• Set up monitoring for improvements\n"
	elif negative_percentage > 25:
		analysis += "• Gather more detailed feedback\n"
		analysis += "• Identify specific pain points\n"
		analysis += "• Implement targeted improvements\n"
		analysis += "• Follow up with affected users\n"
	else:
		analysis += "• Continue current practices\n"
		analysis += "• Monitor for any changes\n"
		analysis += "• Consider minor optimizations\n"
	
	return analysis

def call_huggingface_api(config, prompt):
	"""Call Hugging Face API"""
	try:
		headers = {
			"Authorization": f"Bearer {config['api_key']}",
			"Content-Type": "application/json"
		}
		
		# For BART model, we need to use a different payload format
		payload = {
			"inputs": prompt[:1000],  # Limit input length
			"parameters": {
				"max_length": config.get("max_length", 200),
				"do_sample": True,
				"temperature": config.get("temperature", 0.7)
			}
		}
		
		response = requests.post(config["api_url"], headers=headers, json=payload, timeout=15)
		
		# Debug information
		print(f"API URL: {config['api_url']}")
		print(f"Response Status: {response.status_code}")
		print(f"Response Headers: {dict(response.headers)}")
		
		if response.status_code == 200:
			result = response.json()
			print(f"API Response: {result}")
			
			if isinstance(result, list) and len(result) > 0:
				# Handle different response formats
				if 'summary_text' in result[0]:
					return result[0]['summary_text']
				elif 'generated_text' in result[0]:
					return result[0]['generated_text']
				else:
					return str(result[0])
			elif isinstance(result, dict):
				if 'summary_text' in result:
					return result['summary_text']
				elif 'generated_text' in result:
					return result['generated_text']
				else:
					return str(result)
			else:
				return 'AI analysis completed'
		else:
			error_msg = f"AI API Error {response.status_code}: {response.text}"
			print(error_msg)
			return error_msg
			
	except Exception as e:
		error_msg = f"AI service error: {str(e)}"
		print(error_msg)
		return error_msg

def call_openai_api(config, prompt):
	"""Call OpenAI API"""
	try:
		headers = {
			"Authorization": f"Bearer {config['api_key']}",
			"Content-Type": "application/json"
		}
		
		payload = {
			"model": config.get("model", "gpt-3.5-turbo"),
			"messages": [
				{"role": "system", "content": "You are a helpful assistant that analyzes course feedback."},
				{"role": "user", "content": prompt}
			],
			"max_tokens": config.get("max_tokens", 200),
			"temperature": 0.7
		}
		
		response = requests.post(config["api_url"], headers=headers, json=payload, timeout=10)
		if response.status_code == 200:
			result = response.json()
			if "choices" in result and len(result["choices"]) > 0:
				return result["choices"][0]["message"]["content"]
			return 'AI analysis completed'
		else:
			return f"AI API Error: {response.status_code}"
	except:
		return "AI service temporarily unavailable"

def call_generic_api(config, prompt):
	"""Call generic API endpoint"""
	try:
		headers = {"Content-Type": "application/json"}
		payload = {"text": prompt}
		
		response = requests.post(config["api_url"], headers=headers, json=payload, timeout=config.get("timeout", 10))
		if response.status_code == 200:
			result = response.json()
			return result.get("analysis", "AI analysis completed")
		else:
			return f"AI API Error: {response.status_code}"
	except:
		return "AI service temporarily unavailable"

def analyze_sentiment(feedback):
	"""Analyze sentiment score from -1 (very negative) to 1 (very positive)"""
	if not feedback:
		return 0
	
	feedback_lower = feedback.lower()
	
	# Negative words with weights
	negative_words = {
		"terrible": -1.0, "awful": -1.0, "horrible": -1.0, "worst": -1.0,
		"bad": -0.6, "poor": -0.7, "hate": -0.9, "dislike": -0.6, "difficult": -0.4,
		"confusing": -0.5, "boring": -0.6, "useless": -0.8, "waste": -0.7,
		"problem": -0.5, "issue": -0.5, "complaint": -0.6, "disappointed": -0.7,
		"frustrated": -0.6, "annoyed": -0.5, "upset": -0.6, "angry": -0.8
	}
	
	# Positive words with weights
	positive_words = {
		"excellent": 1.0, "amazing": 1.0, "fantastic": 1.0, "wonderful": 1.0,
		"great": 0.8, "good": 0.6, "nice": 0.5, "helpful": 0.7, "useful": 0.6,
		"love": 0.9, "enjoy": 0.7, "like": 0.5, "perfect": 1.0, "outstanding": 1.0
	}
	
	score = 0
	word_count = 0
	
	for word, weight in negative_words.items():
		if word in feedback_lower:
			score += weight
			word_count += 1
	
	for word, weight in positive_words.items():
		if word in feedback_lower:
			score += weight
			word_count += 1
	
	# Normalize score
	if word_count > 0:
		score = score / word_count
	
	# Cap at -1 to 1
	return max(-1.0, min(1.0, score))

def determine_priority_level(negative_percentage, avg_sentiment, total_feedback):
	"""Determine priority level based on negative percentage and sentiment"""
	if negative_percentage >= 50 or avg_sentiment <= -0.5:
		return "High"
	elif negative_percentage >= 25 or avg_sentiment <= -0.2:
		return "Medium"
	else:
		return "Low"

def extract_key_issues(issues):
	"""Extract key issues from negative feedback"""
	if not issues:
		return "No major issues identified"
	
	# Get top 3 most negative issues
	sorted_issues = sorted(issues, key=lambda x: x["sentiment"])[:3]
	
	key_issues = []
	for issue in sorted_issues:
		feedback_text = issue["feedback"][:100] + "..." if len(issue["feedback"]) > 100 else issue["feedback"]
		key_issues.append(f"'{feedback_text}' (Student: {issue['student']})")
	
	return " | ".join(key_issues)

def determine_action_required(priority_level, negative_percentage, avg_sentiment):
	"""Determine specific action required based on analysis"""
	if priority_level == "High":
		if negative_percentage >= 70:
			return "URGENT: Complete process review and immediate fixes required"
		elif negative_percentage >= 50:
			return "CRITICAL: Major improvements needed - allocate resources"
		else:
			return "HIGH PRIORITY: Significant improvements required"
	
	elif priority_level == "Medium":
		if negative_percentage >= 30:
			return "MODERATE: Review and implement targeted improvements"
		else:
			return "MONITOR: Keep track and make minor adjustments"
	
	else:
		return "LOW PRIORITY: Continue monitoring, minor optimizations"

def get_feedback_type_summary(data, filters):
	"""Generate summary focused on feedback types and issues"""
	if not data:
		return []
	
	total_feedback_types = len(data)
	high_priority_count = len([row for row in data if row.get("priority_level") == "High"])
	medium_priority_count = len([row for row in data if row.get("priority_level") == "Medium"])
	total_negative_issues = sum([row.get("negative_count", 0) for row in data])
	
	# Find the most problematic feedback type
	most_problematic = max(data, key=lambda x: x.get("negative_percentage", 0)) if data else None
	
	summary = [
		{
			"value": total_feedback_types,
			"label": _("Feedback Types Analyzed"),
			"datatype": "Int",
			"indicator": "Blue"
		},
		{
			"value": high_priority_count,
			"label": _("High Priority Types"),
			"datatype": "Int",
			"indicator": "Red"
		},
		{
			"value": medium_priority_count,
			"label": _("Medium Priority Types"),
			"datatype": "Int",
			"indicator": "Orange"
		},
		{
			"value": total_negative_issues,
			"label": _("Total Negative Issues"),
			"datatype": "Int",
			"indicator": "Red"
		}
	]
	
	if most_problematic:
		summary.append({
			"value": f"{most_problematic.get('course_feedback_type')} ({most_problematic.get('negative_percentage', 0):.1f}% negative)",
			"label": _("Most Problematic Type"),
			"datatype": "Data",
			"indicator": "Red"
		})
	
	return summary
