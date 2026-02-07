import requests
import json
from datetime import datetime, timezone

from dotenv import load_dotenv
import os
from typing import Optional, Dict, Any

from storage.conversations import save_conversation

load_dotenv()

MODEL_NAME = "arcee-ai/trinity-large-preview:free"
API_URL = "https://openrouter.ai/api/v1/chat/completions"


def run_conversation(question: Optional[str] = None) -> Dict[str, Any]:
    """Run the two-step reasoning conversation and save it to disk.

    Returns a dict with the saved conversation and the final assistant message.
    """
    if question is None:
        question = "How many r's are in the word 'strawberry'?"

    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json",
    }

    # First API call with reasoning
    resp1 = requests.post(
        url=API_URL,
        headers=headers,
        data=json.dumps({
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": question}],
            "reasoning": {"enabled": True},
        }),
    )

    resp1.raise_for_status()
    resp1_json = resp1.json()
    assistant_msg = resp1_json["choices"][0]["message"]

    # Use the assistant's first reply directly (no second request)
    messages = [
        {"role": "user", "content": question},
        {
            "role": "assistant",
            "content": assistant_msg.get("content"),
            "reasoning_details": assistant_msg.get("reasoning_details"),
        },
    ]

    final_message = assistant_msg.get("content")

    # Save conversation (uses storage module)
    conversation = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": MODEL_NAME,
        "messages": messages,
    }

    conv_id = save_conversation(conversation)

    return {"conversation": conversation, "final_message": final_message, "conversation_id": conv_id}


if __name__ == "__main__":
    import sys

    # By default, start the web server so `python app.py` runs the app.
    # Pass `--run-once` (or `run`) to execute a single conversation instead.
    if "--run-once" in sys.argv or "run" in sys.argv:
        try:
            result = run_conversation()
            print(result["final_message"])
            conv_id = result.get("conversation_id")
            print(f"✅ Conversation saved (id: {conv_id})")
        except Exception as e:
            print(f"⚠️ Failed to run conversation: {e}")
    else:
        # Start Flask server (uses create_app from web.py)
        from web import create_app

        app = create_app(run_conversation)
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port, debug=True)
