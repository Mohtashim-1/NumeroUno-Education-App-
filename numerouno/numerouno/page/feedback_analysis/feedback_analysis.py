# Copyright (c) 2025, mohtashim and contributors
# For license information, please see license.txt

import frappe
import requests
import json
import time

def get_context(context):
	context.title = "Feedback Analysis Dashboard"
	
	# Get basic stats
	context.total_feedback = frappe.db.count('Course Feedback')
	context.feedback_types = frappe.db.get_list('Course Feedback Type', fields=['name'], limit=10)

@frappe.whitelist()
def get_feedback_summary(filters=None):
	"""Get summary statistics for feedback analysis"""
	
	# Build conditions
	conditions = []
	if filters:
		filters = frappe.parse_json(filters)
		if filters.get('from_date'):
			conditions.append(f"cf.posting_date >= '{filters['from_date']}'")
		if filters.get('to_date'):
			conditions.append(f"cf.posting_date <= '{filters['to_date']}'")
		if filters.get('student_group'):
			conditions.append(f"cf.student_group = '{filters['student_group']}'")

	where_clause = 'WHERE ' + ' AND '.join(conditions) if conditions else ''

	# Get summary data with improved negative detection
	result = frappe.db.sql(f"""
		SELECT 
			cf.course_feedback_type,
			COUNT(*) as total_count,
			SUM(CASE 
				WHEN cf.feedback LIKE '%not good%' OR cf.feedback LIKE '%not great%' OR cf.feedback LIKE '%not excellent%'
				OR cf.feedback LIKE '%bad attitude%' OR cf.feedback LIKE '%poor attitude%' OR cf.feedback LIKE '%terrible attitude%'
				OR cf.feedback LIKE '%take too much time%' OR cf.feedback LIKE '%takes too long%' OR cf.feedback LIKE '%very slow%'
				OR cf.feedback LIKE '%not satisfied%' OR cf.feedback LIKE '%not happy%' OR cf.feedback LIKE '%disappointed%'
				OR cf.feedback LIKE '%not working%' OR cf.feedback LIKE '%does not work%' OR cf.feedback LIKE '%not functioning%'
				OR cf.feedback LIKE '%not professional%' OR cf.feedback LIKE '%unprofessional%' OR cf.feedback LIKE '%rude%'
				OR cf.feedback LIKE '%bad%' OR cf.feedback LIKE '%poor%' OR cf.feedback LIKE '%terrible%' OR cf.feedback LIKE '%awful%'
				OR cf.feedback LIKE '%hate%' OR cf.feedback LIKE '%difficult%' OR cf.feedback LIKE '%confusing%' OR cf.feedback LIKE '%boring%'
				OR cf.feedback LIKE '%useless%' OR cf.feedback LIKE '%problem%' OR cf.feedback LIKE '%issue%' OR cf.feedback LIKE '%complaint%'
				OR cf.feedback LIKE '%frustrated%' OR cf.feedback LIKE '%annoying%' OR cf.feedback LIKE '%slow%' OR cf.feedback LIKE '%late%'
				OR cf.feedback LIKE '%wrong%' OR cf.feedback LIKE '%incorrect%' OR cf.feedback LIKE '%expensive%' OR cf.feedback LIKE '%costly%'
				OR cf.feedback LIKE '%waste%' OR cf.feedback LIKE '%failed%' OR cf.feedback LIKE '%broken%' OR cf.feedback LIKE '%damaged%'
				OR cf.feedback LIKE '%error%' OR cf.feedback LIKE '%mistake%'
				THEN 1 ELSE 0 END) as negative_count
		FROM `tabCourse Feedback` cf
		{where_clause}
		GROUP BY cf.course_feedback_type
		ORDER BY negative_count DESC
	""", as_dict=True)

	return result

@frappe.whitelist()
def get_feedback_data(filters=None):
	"""Get detailed feedback data for analysis"""
	
	# Build conditions
	conditions = []
	if filters:
		filters = frappe.parse_json(filters)
		if filters.get('from_date'):
			conditions.append(f"cf.posting_date >= '{filters['from_date']}'")
		if filters.get('to_date'):
			conditions.append(f"cf.posting_date <= '{filters['to_date']}'")
		if filters.get('student_group'):
			conditions.append(f"cf.student_group = '{filters['student_group']}'")

	where_clause = 'WHERE ' + ' AND '.join(conditions) if conditions else ''

	# Get detailed data
	result = frappe.db.sql(f"""
		SELECT 
			cf.course_feedback_type,
			cf.feedback,
			cf.posting_date,
			cf.student,
			cf.student_group
		FROM `tabCourse Feedback` cf
		{where_clause}
		ORDER BY cf.course_feedback_type, cf.posting_date DESC
	""", as_dict=True)

	return result

@frappe.whitelist()
def get_ai_analysis(feedback_type, feedback_texts, negative_percentage):
	"""Get AI analysis using Gemini API"""
	try:
		# Import AI config
		from numerouno.numerouno.report.course_feedback.ai_config import GEMINI_CONFIG
		
		if not GEMINI_CONFIG.get("enabled"):
			return get_enhanced_fallback_analysis(feedback_type, feedback_texts, negative_percentage)
		
		# Prepare feedback text
		combined_feedback = "\n".join([f"• {text}" for text in feedback_texts[:5]])  # Limit to 5 feedback entries
		
		# Create prompt for Gemini
		prompt = f"""
Analyze this {feedback_type} feedback and provide a business-focused summary:

Feedback Type: {feedback_type}
Negative Percentage: {negative_percentage}%
Number of Feedback Entries: {len(feedback_texts)}

Feedback Samples:
{combined_feedback}

Please provide a concise analysis in this format:

📊 **{feedback_type} Feedback Analysis**

[Priority Level: High/Medium/Low based on negative percentage]

🎯 **Key Issues Identified:**
• [List 3-4 main problems]

⚠️ **Business Impact:**
• [How this affects operations/customer satisfaction]

💡 **Immediate Actions Required:**
• [3-4 specific, actionable recommendations]

🔍 **Root Cause Analysis:**
• [What's causing these issues]

Keep the response focused, actionable, and business-oriented.
"""
		
		# Call Gemini API
		response = call_gemini_api(GEMINI_CONFIG, feedback_type, combined_feedback, negative_percentage)
		
		if response:
			return response
		else:
			return get_enhanced_fallback_analysis(feedback_type, feedback_texts, negative_percentage)
			
	except Exception as e:
		frappe.log_error(f"AI Analysis Error: {str(e)}", "Feedback Analysis")
		return get_enhanced_fallback_analysis(feedback_type, feedback_texts, negative_percentage)

def call_gemini_api(config, feedback_type, combined_feedback, negative_percentage):
	"""Call Google Gemini API for analysis"""
	try:
		headers = {
			'Content-Type': 'application/json',
			'X-goog-api-key': config['api_key']
		}
		
		payload = {
			"contents": [
				{
					"parts": [
						{
							"text": f"""
Analyze this {feedback_type} feedback and provide a business-focused summary:

Feedback Type: {feedback_type}
Negative Percentage: {negative_percentage}%
Feedback Samples:
{combined_feedback}

Please provide a concise analysis in this format:

📊 **{feedback_type} Feedback Analysis**

[Priority Level: High/Medium/Low based on negative percentage]

🎯 **Key Issues Identified:**
• [List 3-4 main problems]

⚠️ **Business Impact:**
• [How this affects operations/customer satisfaction]

💡 **Immediate Actions Required:**
• [3-4 specific, actionable recommendations]

🔍 **Root Cause Analysis:**
• [What's causing these issues]

Keep the response focused, actionable, and business-oriented.
"""
						}
					]
				}
			],
			"generationConfig": {
				"maxOutputTokens": config.get('max_tokens', 500),
				"temperature": config.get('temperature', 0.7)
			}
		}
		
		response = requests.post(
			config['api_url'],
			headers=headers,
			json=payload,
			timeout=15
		)
		
		if response.status_code == 200:
			result = response.json()
			if 'candidates' in result and len(result['candidates']) > 0:
				content = result['candidates'][0]['content']
				if 'parts' in content and len(content['parts']) > 0:
					return content['parts'][0]['text']
		
		frappe.log_error(f"Gemini API Error: {response.status_code} - {response.text}", "Feedback Analysis")
		return None
		
	except Exception as e:
		frappe.log_error(f"Gemini API Exception: {str(e)}", "Feedback Analysis")
		return None

def get_enhanced_fallback_analysis(feedback_type, feedback_texts, negative_percentage):
	"""Enhanced local analysis when AI is not available"""
	
	# Determine priority level
	if negative_percentage >= 70:
		priority = "🔴 **CRITICAL PRIORITY**"
		priority_desc = "• Extremely high negative feedback\n• Immediate intervention required\n• Process redesign needed"
	elif negative_percentage >= 50:
		priority = "🟠 **HIGH PRIORITY**"
		priority_desc = "• High negative feedback\n• Urgent attention required\n• Major improvements needed"
	elif negative_percentage >= 30:
		priority = "🟡 **MODERATE PRIORITY**"
		priority_desc = "• Moderate negative feedback\n• Review and improvement needed\n• Monitor trends closely"
	else:
		priority = "🟢 **LOW PRIORITY**"
		priority_desc = "• Low negative feedback\n• Continue current practices\n• Minor optimizations only"
	
	# Analyze key themes
	all_feedback = " ".join(feedback_texts).lower()
	
	# Service-related issues
	service_issues = []
	if any(word in all_feedback for word in ['slow', 'time', 'long', 'wait']):
		service_issues.append("Service speed and efficiency")
	if any(word in all_feedback for word in ['attitude', 'rude', 'unprofessional', 'impolite']):
		service_issues.append("Staff attitude and professionalism")
	if any(word in all_feedback for word in ['confusing', 'difficult', 'complicated', 'unclear']):
		service_issues.append("Process complexity and clarity")
	if any(word in all_feedback for word in ['error', 'mistake', 'wrong', 'incorrect']):
		service_issues.append("Accuracy and error handling")
	
	# Business impact
	business_impact = []
	if negative_percentage >= 50:
		business_impact.append("High customer dissatisfaction risk")
		business_impact.append("Potential reputation damage")
		business_impact.append("Increased support workload")
	if negative_percentage >= 30:
		business_impact.append("Moderate customer experience impact")
		business_impact.append("Need for process improvements")
	
	# Recommendations
	recommendations = []
	if negative_percentage >= 70:
		recommendations.extend([
			"Conduct immediate staff training sessions",
			"Implement process redesign with stakeholder input",
			"Set up real-time monitoring and feedback loops",
			"Establish emergency response protocols"
		])
	elif negative_percentage >= 50:
		recommendations.extend([
			"Review and optimize current processes",
			"Provide targeted staff training",
			"Implement customer feedback collection system",
			"Establish regular quality audits"
		])
	elif negative_percentage >= 30:
		recommendations.extend([
			"Identify specific pain points through user interviews",
			"Implement targeted improvements",
			"Enhance staff communication protocols",
			"Monitor improvement metrics"
		])
	else:
		recommendations.extend([
			"Continue current best practices",
			"Monitor for any emerging issues",
			"Consider minor process optimizations",
			"Maintain quality standards"
		])
	
	# Root cause analysis
	root_causes = []
	if any(word in all_feedback for word in ['time', 'slow', 'long']):
		root_causes.append("Insufficient staffing or resource allocation")
	if any(word in all_feedback for word in ['attitude', 'rude', 'unprofessional']):
		root_causes.append("Staff training gaps or cultural issues")
	if any(word in all_feedback for word in ['confusing', 'difficult', 'complicated']):
		root_causes.append("Process design complexity or poor documentation")
	if any(word in all_feedback for word in ['error', 'mistake', 'wrong']):
		root_causes.append("Lack of quality control or training")
	
	analysis = f"""📊 **{feedback_type} Feedback Analysis**

{priority}
{priority_desc}

🎯 **Key Issues Identified:**
{chr(10).join([f"• {issue}" for issue in service_issues[:4]])}

⚠️ **Business Impact:**
{chr(10).join([f"• {impact}" for impact in business_impact])}

💡 **Immediate Actions Required:**
{chr(10).join([f"• {rec}" for rec in recommendations[:4]])}

🔍 **Root Cause Analysis:**
{chr(10).join([f"• {cause}" for cause in root_causes[:3]])}

📈 **Metrics Summary:**
• {negative_percentage}% negative feedback rate
• {len(feedback_texts)} total feedback entries
• Priority level: {'Critical' if negative_percentage >= 70 else 'High' if negative_percentage >= 50 else 'Moderate' if negative_percentage >= 30 else 'Low'}"""
	
	return analysis 