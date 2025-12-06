import sys
import requests
import json

# Your Gemini API key
API_KEY = "AIzaSyDWmF6VtlWUlS6Bdn_lvGwebAKFpi0Gs38"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# Read the table data from stdin (piped from extract_table.py)
table_data = sys.stdin.read()

# Custom prompt - you can modify this as needed
custom_prompt = f"""
Analyze the following table data and provide a structured summary:

{table_data}

Please provide:
1. A brief description of what the table contains
2. Key insights or patterns
3. Any notable data points
"""

# Prepare the request payload
payload = {
    "contents": [
        {
            "parts": [
                {
                    "text": custom_prompt
                }
            ]
        }
    ]
}

# Set headers
headers = {
    "Content-Type": "application/json",
    "X-goog-api-key": API_KEY
}

try:
    # Send request to Gemini API
    response = requests.post(API_URL, headers=headers, json=payload)
    response.raise_for_status()
    
    # Parse the response
    result = response.json()
    
    # Extract and print the AI response
    if "candidates" in result and len(result["candidates"]) > 0:
        ai_response = result["candidates"][0]["content"]["parts"][0]["text"]
        print("\n" + "="*60)
        print("GEMINI API RESPONSE:")
        print("="*60)
        print(ai_response)
        print("="*60 + "\n")
    else:
        print("No response from API")
        
except requests.exceptions.RequestException as e:
    print(f"Error calling Gemini API: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error: {e}", file=sys.stderr)
    sys.exit(1)
    