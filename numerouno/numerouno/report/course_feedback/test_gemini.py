#!/usr/bin/env python3
"""
Test Gemini API integration
"""

import requests
import json

def test_gemini_api():
    """Test the Gemini API with sample feedback"""
    
    api_key = "AIzaSyDjZyKktyYjSuqmgI3NNyNKfM-GRlfwWDA"
    api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": api_key
    }
    
    # Sample feedback data
    sample_feedback = """
    Instructor is not good
    Receptionist is not good
    Registration process is difficult
    Good experience overall
    Helpful staff
    Confusing process
    Excellent service
    Poor communication
    """
    
    prompt = f"""
    Analyze this course feedback for 'Registration' type and provide a concise business analysis:

    Feedback Content: {sample_feedback}
    
    Negative Percentage: 50.0%
    
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
            "maxOutputTokens": 500,
            "temperature": 0.7
        }
    }
    
    print("🧪 Testing Gemini API...")
    print(f"API URL: {api_url}")
    print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
    print("=" * 60)
    
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=15)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS: Gemini API is working!")
            
            # Extract the generated text
            if "candidates" in result and len(result["candidates"]) > 0:
                candidate = result["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if len(parts) > 0 and "text" in parts[0]:
                        ai_analysis = parts[0]["text"]
                        print("\n🤖 GEMINI AI ANALYSIS:")
                        print("-" * 40)
                        print(ai_analysis)
                        print("-" * 40)
                        return True
            
            print("❌ Could not extract AI response from Gemini")
            return False
        else:
            print(f"❌ ERROR: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_gemini_api()
    
    if success:
        print("\n🎉 Gemini API integration is working!")
        print("Your Course Feedback report will now use real AI analysis!")
    else:
        print("\n⚠️ Gemini API test failed. Check your API key and internet connection.") 