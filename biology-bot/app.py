import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from google import genai
from google.genai import types

import chatbot_config as cfg

load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY) if API_KEY else None


@app.route("/")
def index():
    return render_template(
        "index.html",
        name=cfg.CHATBOT_NAME,
        emoji=cfg.CHATBOT_EMOJI,
        tagline=cfg.CHATBOT_TAGLINE,
        welcome=cfg.WELCOME_MESSAGE,
        suggestions=cfg.SUGGESTIONS,
        topics=cfg.TOPICS,
        theme=cfg.THEME,
        max_chars=cfg.MAX_INPUT_CHARS,
    )


@app.route("/chat", methods=["POST"])
def chat():
    if client is None:
        return jsonify(error="GEMINI_API_KEY is missing. Add it to the .env file."), 500

    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    history = data.get("history") or []

    if not message:
        return jsonify(error="Please type a question."), 400
    if len(message) > cfg.MAX_INPUT_CHARS:
        return jsonify(error=f"Question is too long (max {cfg.MAX_INPUT_CHARS} characters)."), 400

    contents = []
    for item in history[-cfg.MAX_HISTORY_MESSAGES:]:
        role = "user" if item.get("role") == "user" else "model"
        text = str(item.get("text", ""))[: cfg.MAX_INPUT_CHARS * 3]
        if text:
            contents.append(types.Content(role=role, parts=[types.Part(text=text)]))
    contents.append(types.Content(role="user", parts=[types.Part(text=message)]))

    try:
        response = client.models.generate_content(
            model=cfg.MODEL_NAME,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=cfg.SYSTEM_PROMPT,
                temperature=cfg.TEMPERATURE,
            ),
        )
        reply = (response.text or "").strip()
        if not reply:
            reply = "Sorry, I could not generate an answer. Please rephrase your question."
        return jsonify(reply=reply)
    except Exception as exc:  # keep the UI friendly, log the details
        app.logger.error("Gemini error: %s", exc)
        return jsonify(error="Something went wrong while contacting the AI. Please try again."), 502


if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", 5000)))
