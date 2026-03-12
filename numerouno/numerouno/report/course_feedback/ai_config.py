# AI Configuration for Course Feedback Analysis
# Free API Options for AI Analysis

# Option 1: Google Gemini (Recommended - Free tier available)
GEMINI_CONFIG = {
    "enabled": True,
    "api_url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
    "api_key": "AIzaSyDjZyKktyYjSuqmgI3NNyNKfM-GRlfwWDA",
    "model": "gemini-2.0-flash",
    "max_tokens": 500,
    "temperature": 0.7
}

# Option 2: Hugging Face (Free tier available)
HUGGING_FACE_CONFIG = {
    "enabled": False,
    "api_url": "https://api-inference.huggingface.co/models/gpt2",  # Simple, reliable model
    "api_key": "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",  # Your API key
    "max_length": 200,
    "temperature": 0.7
}

# Option 3: OpenAI (Free tier available - $5 credit)
OPENAI_CONFIG = {
    "enabled": False,
    "api_url": "https://api.openai.com/v1/chat/completions",
    "api_key": "sk-xxx",  # Get from https://platform.openai.com/api-keys
    "model": "gpt-3.5-turbo",
    "max_tokens": 200
}

# Option 4: Local AI Model (if you have one running)
LOCAL_AI_CONFIG = {
    "enabled": False,
    "api_url": "http://localhost:8000/analyze",
    "timeout": 10
}

# Fallback Analysis Settings
FALLBACK_CONFIG = {
    "enabled": True,
    "use_keyword_analysis": True,
    "use_sentiment_analysis": True
}

# Rate Limiting (to avoid API costs)
RATE_LIMIT_CONFIG = {
    "max_requests_per_minute": 10,
    "max_requests_per_day": 100,
    "cache_duration_hours": 24
}

def get_ai_config():
    """Get the active AI configuration"""
    # You can modify this to choose which AI service to use
    if GEMINI_CONFIG["enabled"]:
        return GEMINI_CONFIG
    elif HUGGING_FACE_CONFIG["enabled"]:
        return HUGGING_FACE_CONFIG
    elif OPENAI_CONFIG["enabled"]:
        return OPENAI_CONFIG
    elif LOCAL_AI_CONFIG["enabled"]:
        return LOCAL_AI_CONFIG
    else:
        return None

def is_ai_available():
    """Check if any AI service is available"""
    config = get_ai_config()
    return config is not None and config.get("enabled", False) 