from flask import Flask, jsonify, request, Response, stream_with_context
import openai
from openai import OpenAI
import json
from dotenv import load_dotenv
import os
# import CORS
from flask_cors import CORS

# allow requests from any origin


app = Flask(__name__)

load_dotenv()

if os.environ.get("production") == "false":
    CORS(app) # allow requests from any origin

# prevent caching
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# load instructions.txt 
AI_instructions = ""
instructions_path = "instructions.txt"

if os.path.exists(instructions_path):
    with open(instructions_path, "r") as file:
        AI_instructions = file.read()
    print(AI_instructions)
else:
    print("No AI instructions file. found Please add create a instructions.txt if you want to edit AI instructions.")

@app.route("/")
def home():
    return "AI backend is running"

@app.route("/chat", methods=["POST"])
def chat():

    data = request.get_json()

    if "api_key" not in data or "message" not in data or "history" not in data:
        return jsonify({"error": "Invalid request data (ID: 1)"}), 400

    api_key = data.get('api_key', "")

    if not isinstance(api_key, str):
        return jsonify({"error": "API key must be a string"}), 400
    
    if not isinstance(data["message"], str):
        return jsonify({"error": "Invalid request data (ID: 2)"}), 400
    
    if not isinstance(data["history"], list):
        return jsonify({"error": "Invalid request data (ID: 3)"}), 400
    # history must be formatted [{"role":"users/system", "message":"message"}]
    for item in data["history"]:
        if not isinstance(item, dict):
            return jsonify({"error": "Invalid request data (ID: 4)"}), 400
        if "role" not in item or "message" not in item:
            return jsonify({"error": "Invalid request data (ID: 5)"}), 400
        if not isinstance(item["role"], str) or not isinstance(item["message"], str):
            return jsonify({"error": "Invalid request data (ID: 6)"}), 400
        if(item["role"] != "user" and item["role"] != "assistant"):
            return jsonify({"error": "Invalid request data (ID: 7)"}), 400
    
    client = OpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )


    def generate():
        data = request.json
        msg = data.get('message', '')
        chat_history = data.get('history', [])

        # Prepare message format
        messages = [{"role": "system", "content": AI_instructions or "You are a helpful assistant."}]
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
                        yield "An unknown error occurred (ID: 1)"
                    print(f"Error: {e}")
                except Exception as e:
                    yield "An unknown error occurred (ID: 2)"
                    print(f"Exception: {e}")
            except Exception as e:
                yield "An unknown error occurred (ID: 3)"
                print(f"Exception: {e}")
        except Exception as e:  # Catches any other general errors
            yield f"AN UNKNOWN ERROR OCCURRED (ID: 4)"
            print(f"Exception: {e}")

    return Response(stream_with_context(generate()), mimetype="text/event-stream")

@app.route("/chat", methods=["GET"])
def chat_fail():
    return jsonify({"error": "Incorrect request method"}), 405

if __name__ == "__main__":
    app.run(debug=True)
