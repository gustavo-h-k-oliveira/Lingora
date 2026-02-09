import os

from flask import Flask, jsonify, request
from flask_cors import CORS


def create_app(run_conversation_func):
    """Create Flask app, injecting the `run_conversation` callable to avoid circular imports."""
    app = Flask(__name__)

    # Allow local frontend dev server to call the API during development
    CORS(
        app,
        resources={r"/run": {"origins": "http://localhost:5173"}},
        supports_credentials=True,
    )

    @app.route("/", methods=["GET"])
    def index():
        return jsonify(
            {
                "ok": True,
                "message": "Frontend is a separate React app. Run 'npm run dev' in ./frontend for development or serve built assets from frontend/dist in production.",
            }
        )

    @app.route("/run", methods=["POST"])
    def run():
        data = request.get_json(silent=True) or {}
        question = data.get("question")
        messages = data.get("messages")
        conversation_id = data.get("conversation_id")
        try:
            result = run_conversation_func(
                question=question, messages=messages, conversation_id=conversation_id
            )
            return jsonify(
                {
                    "ok": True,
                    "final_message": result["final_message"],
                    "conversation": result.get("conversation"),
                    "conversation_id": result.get("conversation_id"),
                }
            )
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    return app


if __name__ == "__main__":
    # When executed directly, import the run_conversation implementation and start the server.
    from app import run_conversation

    app = create_app(run_conversation)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
