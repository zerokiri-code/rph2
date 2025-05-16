from flask import Flask, render_template, request, jsonify
from flask_cors import CORS  # Add this import
import requests
import os
from dotenv import load_dotenv
import re
from collections import defaultdict

load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure OpenRouter API
OPENROUTER_API_KEY = os.getenv("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")
OPENROUTER_API_URL = "https://openrouter.ai/chat?models=meta-llama/llama-3.3-8b-instruct:free"

# Common teleserye clichés for initial filtering
CLICHES = {
    "amnesia": {
        "patterns": [r"amnesia", r"memory loss", r"forgot everything"],
        "category": "plot_device"
    },
    "long-lost twin": {
        "patterns": [r"twin", r"separated at birth", r"identical look-alike"],
        "category": "character"
    },
    # Add more clichés as needed
}

def analyze_with_openrouter(prompt, script):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "anthropic/claude-3-opus",  # You can change this to any model OpenRouter supports
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": script}
        ],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Error calling OpenRouter API: {e}")
        return None

def analyze_script(script_text):
    # First do basic pattern matching
    basic_results = defaultdict(list)
    script_lower = script_text.lower()
    
    for cliche, data in CLICHES.items():
        for pattern in data["patterns"]:
            if re.search(pattern, script_lower):
                basic_results[cliche].append({
                    "found": re.findall(pattern, script_lower),
                    "category": data["category"]
                })
                break
    
    # Then get AI analysis
    analysis_prompt = """You are a professional script analyst specializing in Filipino teleseryes. 
    Analyze the provided script for:
    1. Overused clichés and tropes
    2. Plot structure issues
    3. Character development opportunities
    4. Pacing problems
    5. Cultural relevance
    
    Provide specific recommendations for improvement while maintaining the Filipino drama essence.
    Format your response with clear sections and bullet points."""
    
    ai_analysis = analyze_with_openrouter(analysis_prompt, script_text)
    
    return {
        "basic_analysis": dict(basic_results),
        "ai_analysis": ai_analysis
    }

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    script_text = request.form.get('script', '')
    if not script_text.strip():
        return jsonify({"error": "Please enter a script to analyze"}), 400
    
    try:
        analysis = analyze_script(script_text)
        return jsonify(analysis)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ... (keep the rest of your backend code)

if __name__ == '__main__':
    app.run(debug=True, port=5001)  # Changed port to avoid conflicts