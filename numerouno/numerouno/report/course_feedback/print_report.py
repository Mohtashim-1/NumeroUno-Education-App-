#!/usr/bin/env python3
"""
Print Course Feedback Report to Console
Run this with: bench --site all execute numerouno.numerouno.report.course_feedback.course_feedback.print_report
"""

import frappe
from frappe import _

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

if __name__ == "__main__":
    print_report() 