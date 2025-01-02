from flask import Flask, request, jsonify
import g4f
import re
import time
import os
import asyncio
from functools import wraps
from dotenv import load_dotenv
from flask_cors import CORS  # Import CORS for handling cross-origin requests

# Fix for Windows ProactorEventLoop warning
if os.name == 'nt':  # For Windows
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "https://627b0e63.bolt-diy-eiq.pages.dev"}})  # Allow specific origin

# Get API key from environment variable
API_KEY = os.getenv('API_KEY')
if not API_KEY:
    raise ValueError("API_KEY environment variable is not set!")

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key and api_key == API_KEY:
            return f(*args, **kwargs)
        return jsonify({"error": "Invalid or missing API key"}), 401
    return decorated_function

def is_code(content):
    """
    Check if the content contains code-like patterns.
    """
    # Look for common code patterns (e.g., function definitions, braces, semicolons)
    code_patterns = [r"def ", r"\{", r"\}", r";", r"class ", r"import ", r"function "]
    return any(re.search(pattern, content) for pattern in code_patterns)

def format_bolt_response(content, status="success"):
    """
    Format the response according to Bolt.DIY specifications
    """
    return {
        "status": status,
        "data": {
            "messages": [
                {
                    "role": "assistant",
                    "content": content
                }
            ]
        }
    }

@app.route('/api/chat', methods=['POST'])
@require_api_key
def chat():
    try:
        data = request.json
        if not data:
            return jsonify(format_bolt_response("Invalid request payload", status="error")), 400

        user_input = data.get("input", "")
        if not user_input:
            return jsonify(format_bolt_response("No input provided", status="error")), 400

        max_retries = 10
        retry_delay = 3
        attempt = 0

        while attempt < max_retries:
            attempt += 1
            try:
                # Call the g4f API
                response = g4f.ChatCompletion.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": user_input}],
                )

                # Parse the response
                if isinstance(response, str):
                    generated_content = response
                else:
                    generated_content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

                # Check for known error messages
                if "Model not found" in generated_content or "too long input" in generated_content:
                    raise ValueError("Invalid response from the model.")

                # Check if the response contains code
                if is_code(generated_content):
                    return jsonify(format_bolt_response(generated_content))

                # If no code found and not last attempt, retry
                if attempt < max_retries:
                    time.sleep(retry_delay)
                    continue

                # If all retries exhausted and no code found
                return jsonify(format_bolt_response("Failed to generate a code response after multiple attempts.", status="error")), 500

            except Exception as e:
                print(f"Attempt {attempt} failed: {e}")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                else:
                    return jsonify(format_bolt_response(f"Error: {str(e)}", status="error")), 500

    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify(format_bolt_response(f"An unexpected error occurred: {str(e)}", status="error")), 500

@app.route('/api/chat/models', methods=['GET'])
@require_api_key
def get_models():
    # Example list of models; replace with your actual model retrieval logic
    models = [
        {"name": "gpt-4o", "description": "GPT-4 Optimized"},
        {"name": "gpt-4", "description": "GPT-4"},
        # Add more models as needed
    ]
    return jsonify(models), 200

@app.route('/api/chat/api/tags', methods=['GET'])
@require_api_key
def get_tags():
    # Example list of tags; replace with your actual logic to retrieve tags
    tags = [
        {"tag": "example1"},
        {"tag": "example2"},
        {"tag": "example3"},
        # Add more tags as needed
    ]
    return jsonify(tags), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)