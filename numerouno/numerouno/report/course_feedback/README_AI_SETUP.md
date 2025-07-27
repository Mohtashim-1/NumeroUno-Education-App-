# AI Integration Setup Guide for Course Feedback Report

## 🚀 Overview

This report now includes AI-powered analysis of course feedback using free APIs. The AI will read and analyze feedback content to provide deeper insights into student complaints and suggestions.

## 📋 Features Added

- **AI Analysis Column**: New column showing AI-generated insights
- **Multiple AI Providers**: Support for Hugging Face, OpenAI, and custom APIs
- **Fallback Analysis**: Works even without AI API (basic analysis)
- **Configurable**: Easy to switch between different AI services

## 🔧 Setup Instructions

### Option 1: Hugging Face (Recommended - Free)

1. **Get Free API Token**:
   - Go to https://huggingface.co/
   - Create a free account
   - Go to Settings → Access Tokens
   - Create a new token (free tier available)

2. **Configure the Report**:
   - Edit `ai_config.py`
   - Set `HUGGING_FACE_CONFIG["api_key"] = "your_token_here"`
   - Ensure `HUGGING_FACE_CONFIG["enabled"] = True`

### Option 2: OpenAI (Free $5 Credit)

1. **Get API Key**:
   - Go to https://platform.openai.com/
   - Create account (get $5 free credit)
   - Go to API Keys → Create new key

2. **Configure the Report**:
   - Edit `ai_config.py`
   - Set `OPENAI_CONFIG["api_key"] = "your_key_here"`
   - Set `OPENAI_CONFIG["enabled"] = True`
   - Set `HUGGING_FACE_CONFIG["enabled"] = False`

### Option 3: Custom AI Service

1. **Set up your own AI endpoint**:
   - Create an API endpoint that accepts POST requests
   - Expected format: `{"text": "feedback content"}`
   - Response format: `{"analysis": "AI analysis result"}`

2. **Configure the Report**:
   - Edit `ai_config.py`
   - Set `LOCAL_AI_CONFIG["api_url"] = "your_api_url"`
   - Set `LOCAL_AI_CONFIG["enabled"] = True`

## 📊 What the AI Analysis Provides

The AI will analyze feedback and provide:

1. **Main Themes**: Common patterns in feedback
2. **Specific Issues**: Detailed complaints and problems
3. **Improvement Suggestions**: Actionable recommendations
4. **Sentiment Assessment**: Overall tone and mood analysis

## 🔄 How It Works

1. **Data Collection**: Combines all feedback for each feedback type
2. **AI Processing**: Sends combined feedback to AI API
3. **Analysis**: AI returns structured insights
4. **Display**: Shows AI analysis in the report
5. **Fallback**: If AI fails, shows basic keyword analysis

## 💰 Cost Management

### Free Options:
- **Hugging Face**: Free tier with rate limits
- **OpenAI**: $5 free credit (enough for thousands of analyses)
- **Custom**: Your own AI service

### Rate Limiting:
The system includes built-in rate limiting to control costs:
- Max 10 requests per minute
- Max 100 requests per day
- 24-hour caching

## 🛠️ Configuration File

Edit `ai_config.py` to customize:

```python
# Choose your AI provider
HUGGING_FACE_CONFIG = {
    "enabled": True,
    "api_key": "your_token_here",
    # ... other settings
}

# Rate limiting
RATE_LIMIT_CONFIG = {
    "max_requests_per_minute": 10,
    "max_requests_per_day": 100,
    "cache_duration_hours": 24
}
```

## 🚨 Troubleshooting

### AI Not Working?
1. Check API key is correct
2. Verify internet connection
3. Check rate limits
4. Review API service status

### Fallback Analysis
If AI fails, the system automatically shows:
- Basic sentiment analysis
- Keyword detection
- Priority assessment
- Action recommendations

## 📈 Benefits

1. **Deeper Insights**: AI reads and understands feedback content
2. **Actionable Analysis**: Specific recommendations for improvement
3. **Cost Effective**: Free options available
4. **Reliable**: Fallback analysis ensures report always works
5. **Scalable**: Handles large volumes of feedback

## 🔮 Future Enhancements

- Sentiment trend analysis
- Predictive analytics
- Automated action recommendations
- Integration with other AI services

## 📞 Support

If you need help setting up the AI integration:
1. Check the configuration file
2. Verify API credentials
3. Test with a small dataset first
4. Monitor API usage and costs

---

**Note**: The AI analysis is optional. The report works perfectly without AI, providing basic sentiment and keyword analysis. 