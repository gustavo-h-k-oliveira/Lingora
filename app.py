import requests
import json
from datetime import datetime, timezone

from dotenv import load_dotenv
import os
from typing import Optional, Dict, Any

from storage.conversations import save_conversation, append_messages, get_conversation

load_dotenv()

MODEL_NAME = "arcee-ai/trinity-large-preview:free"
API_URL = "https://openrouter.ai/api/v1/chat/completions"


def run_conversation(question: Optional[str] = None, messages: Optional[list] = None, conversation_id: Optional[int] = None) -> Dict[str, Any]:
    """Run a conversation turn with optional history and persistence.

    - If `messages` is provided, it will be used as the context (list of {role, content}).
    - If `conversation_id` is provided, new messages will be appended to the existing conversation.
    - If neither `messages` nor `question` is provided, a default question is used.

    Returns dict with final message and conversation_id.
    """
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json",
    }

    if messages is None:
        if question is None:
            question = "How many r's are in the word 'strawberry'?"
        messages = [{"role": "user", "content": question}]

    # Call the model with full message history
    resp = requests.post(
        url=API_URL,
        headers=headers,
        json={
            "model": MODEL_NAME,
            "messages": messages,
            "reasoning": {"enabled": True},
        },
    )

    resp.raise_for_status()
    resp_json = resp.json()
    assistant_msg = resp_json["choices"][0]["message"]
    assistant_content = assistant_msg.get("content")

    # Persist: if conversation_id provided, append only the new user + assistant messages;
    # otherwise create a new conversation record containing the full history + assistant reply.
    if conversation_id:
        # the frontend should have included the user's new message as the last entry in `messages`.
        user_msg = messages[-1]
        append_messages(conversation_id, [user_msg, {"role": "assistant", "content": assistant_content, "reasoning_details": assistant_msg.get("reasoning_details")}])
        conv_id = conversation_id
    else:
        convo_to_save = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": MODEL_NAME,
            "messages": messages + [{"role": "assistant", "content": assistant_content, "reasoning_details": assistant_msg.get("reasoning_details")}],
        }
        conv_id = save_conversation(convo_to_save)

    return {"conversation": {"id": conv_id}, "final_message": assistant_content, "conversation_id": conv_id}


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
