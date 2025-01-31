from flask import Flask, jsonify, request

import os
import google.generativeai as genai
import json
from dotenv import load_dotenv

app = Flask(__name__)

load_dotenv()

if(os.getenv("AI_instructions") == None):
    print("No AI instructions found in .env file. Please add AI_instructions variable with the instructions provided by the AI team.")
    exit()

generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 40,
  "max_output_tokens": 8192,
  "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
  model_name="gemini-2.0-flash-exp",
  generation_config=generation_config,
  system_instruction=os.getenv("AI_instructions") or None,
)

@app.route("/")
def home():
    return "AI backend is running"

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    # expects keys: api_key, message, history
    if "api_key" not in data or "message" not in data or "history" not in data:
        return jsonify({"error": "Invalid request data"}), 400
    # api_key must be string
    if not isinstance(data["api_key"], str):
        return jsonify({"error": "Invalid request data"}), 400
    # message must be string
    if not isinstance(data["message"], str):
        return jsonify({"error": "Invalid request data"}), 400
    # history must be JSON object formatted like:
    #    [{
    #      "role": "user",
    #      "parts": [
    #        "",
    #      ],
    # }
    # ]
    if not isinstance(data["history"], list):
        return jsonify({"error": "Invalid request data"}), 400
    for item in data["history"]:
        if "role" not in item or "parts" not in item:
            return jsonify({"error": "Invalid request data"}), 400
        if not isinstance(item["role"], str) or not isinstance(item["parts"], list):
            return jsonify({"error": "Invalid request data"}), 400
        for part in item["parts"]:
            if not isinstance(part, str):
                return jsonify({"error": "Invalid request data"}), 400
    genai.configure(api_key=data["api_key"])
    chat_session = model.start_chat(history=data["history"])
    try:
        response = chat_session.send_message(data["message"])
        dict = json.dumps(response.to_dict()['candidates'][0]["content"])

        return dict
    except Exception as e:
        # Capture the exception and check if it is an API Key error
        if "API_KEY_INVALID" in str(e):
            return jsonify({"error": "Invalid API key"}), 403
        else:
            return jsonify({"error":"unknown","error_log": str(e)}), 500

@app.route("/chat", methods=["GET"])
def chat_fail():
    return jsonify({"error": "Incorrect request method"}), 405

if __name__ == "__main__":
    app.run(debug=True)
