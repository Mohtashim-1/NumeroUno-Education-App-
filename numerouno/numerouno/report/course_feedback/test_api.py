#!/usr/bin/env python3
"""
Test script for Hugging Face API
Run this to verify your API key and troubleshoot issues
"""

import requests
import json

def test_huggingface_api():
    """Test the Hugging Face API with different models"""
    
    api_key = "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"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Test different models
    models = [
        "https://api-inference.huggingface.co/models/facebook/bart-large-cnn",
        "https://api-inference.huggingface.co/models/cardiffnlp/twitter-roberta-base-sentiment-latest",
        "https://api-inference.huggingface.co/models/gpt2",
        "https://api-inference.huggingface.co/models/facebook/bart-base"
    ]
    
    test_text = "This course feedback is very helpful and informative. Students are satisfied with the content."
    
    print("🔍 Testing Hugging Face API...")
    print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
    print("=" * 50)
    
    for i, model_url in enumerate(models, 1):
        print(f"\n📋 Test {i}: {model_url.split('/')[-1]}")
        
        try:
            payload = {
                "inputs": test_text,
                "parameters": {
                    "max_length": 100,
                    "do_sample": True,
                    "temperature": 0.7
                }
            }
            
            response = requests.post(model_url, headers=headers, json=payload, timeout=10)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ SUCCESS: {type(result)}")
                if isinstance(result, list) and len(result) > 0:
                    print(f"Result: {result[0]}")
                else:
                    print(f"Result: {result}")
            else:
                print(f"❌ ERROR: {response.text}")
                
        except Exception as e:
            print(f"❌ EXCEPTION: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🎯 Recommendation:")
    print("If any model works, update ai_config.py with that model URL")
    print("If none work, check your API key and internet connection")

def test_simple_request():
    """Test a simple API request to verify connectivity"""
    
    api_key = "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"
    
    print("\n🔧 Testing basic connectivity...")
    
    # Test with a simple model
    url = "https://api-inference.huggingface.co/models/gpt2"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    try:
        response = requests.post(url, headers=headers, json={"inputs": "Hello"})
        print(f"Basic test status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Basic connectivity works!")
        else:
            print(f"❌ Basic test failed: {response.text}")
    except Exception as e:
        print(f"❌ Connection error: {str(e)}")

if __name__ == "__main__":
    test_simple_request()
    test_huggingface_api() 