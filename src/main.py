from flask import Flask, jsonify, request, Response, stream_with_context
import openai
from openai import OpenAI
import json
from dotenv import load_dotenv
import os

app = Flask(__name__)

load_dotenv()

# prevent caching
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

if os.getenv("AI_instructions") is None:
    print("No AI instructions found in .env file. Please add AI_instructions if you want to edit AI instructions.")

@app.route("/")
def home():
    return "AI backend is running"

@app.route("/chat", methods=["POST"])
def chat():

    data = request.get_json()

    if "api_key" not in data or "message" not in data or "history" not in data:
        return jsonify({"error": "Invalid request data"}), 400

    api_key = data.get('api_key', "")

    if not isinstance(api_key, str):
        return jsonify({"error": "API key must be a string"}), 400
    
    if not isinstance(data["message"], str):
        return jsonify({"error": "Invalid request data"}), 400
    
    if not isinstance(data["history"], list):
        return jsonify({"error": "Invalid request data"}), 400
    # history must be formatted [{"role":"users/system", "message":"message"}]
    for item in data["history"]:
        if not isinstance(item, dict):
            return jsonify({"error": "Invalid request data"}), 400
        if "role" not in item or "message" not in item:
            return jsonify({"error": "Invalid request data"}), 400
        if not isinstance(item["role"], str) or not isinstance(item["message"], str):
            return jsonify({"error": "Invalid request data"}), 400
        if(item["role"] != "user" and item["role"] != "system"):
            return jsonify({"error": "Invalid request data"}), 400
    
    client = OpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )


    def generate():
        data = request.json
        msg = data.get('message', '')
        chat_history = data.get('history', [])

        # Prepare message format
        messages = [{"role": "system", "content": os.getenv("AI_instructions") or "You are a helpful assistant."}]
        for item in chat_history:
            messages.append({"role": item["role"], "content": item["message"]})

        messages.append({"role": "user", "content": msg})

        try:
            response = client.chat.completions.create(
                model="gemini-2.0-flash-exp",
                messages=messages,
                stream=True
            )
            for chunk in response:
                if(chunk.choices[0].delta.content != None): #OpenAI returns None for last chunk for some reason
                    yield chunk.choices[0].delta.content
        except openai.APIConnectionError as e:
            yield "The server could not be reached"
        except openai.RateLimitError as e:
            yield "A 429 status code was received; we should back off a bit."
        except openai.BadRequestError as e:
            error = str(e)
            #take error and split it from " - "
            error = error.split(" - ")
            error = error[1]
            error = error.replace("'", "\"")
            try:
                error = json.loads(error)
                try:
                    if "details" in error[0]["error"] and len(error[0]["error"]["details"]) > 1:
                        yield error[0]["error"]["details"][1]["message"]
                    elif "message" in error[0]["error"]:
                        yield error[0]["error"]["message"]
                    else:
                        yield "An unknown error occurred"
                except Exception as e:
                    yield "An unknown error occurred"
            except Exception as e:
                yield "An unknown error occurred"
        except Exception as e:  # Catches any other general errors
            print(f"Exception: {e.error}")
            yield f"AN UNKNOWN ERROR OCCURRED"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")

@app.route("/chat", methods=["GET"])
def chat_fail():
    return jsonify({"error": "Incorrect request method"}), 405

if __name__ == "__main__":
    app.run(debug=True)
