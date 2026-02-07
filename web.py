from flask import Flask, render_template, jsonify, request
import os


def create_app(run_conversation_func):
    """Create Flask app, injecting the `run_conversation` callable to avoid circular imports."""
    app = Flask(__name__)

    @app.route("/", methods=["GET"])
    def index():
        return render_template("index.html")

    @app.route("/run", methods=["POST"])
    def run():
        data = request.get_json(silent=True) or {}
        question = data.get("question")
        try:
            result = run_conversation_func(question)
            return jsonify({
                "ok": True,
                "final_message": result["final_message"],
                "conversation": result["conversation"],
                "conversation_id": result.get("conversation_id"),
            })
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    return app


if __name__ == "__main__":
    # When executed directly, import the run_conversation implementation and start the server.
    from app import run_conversation

    app = create_app(run_conversation)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
