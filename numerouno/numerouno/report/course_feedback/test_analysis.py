#!/usr/bin/env python3
"""
Test script to show what the AI analysis should look like
"""

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

# Test with sample data
sample_feedback = [
	"Instructor is not good",
	"Receptionist is not good", 
	"111",
	"Registration process is difficult",
	"Good experience overall",
	"Helpful staff",
	"Confusing process",
	"Excellent service"
]

print("=" * 80)
print("🧪 TESTING AI ANALYSIS OUTPUT")
print("=" * 80)

analysis = get_enhanced_fallback_analysis("Registration", " ".join(sample_feedback), 50.0, sample_feedback)

print("📊 EXPECTED AI ANALYSIS OUTPUT:")
print("-" * 40)
print(analysis)
print("=" * 80) 