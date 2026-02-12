import logging
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from lingora.engine import LingoraEngine
from storage.db import init_db

# Configure logging after imports
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
# Ensure the database schema exists at startup (creates tables if needed)
init_db()

MODEL_NAME = "arcee-ai/trinity-large-preview:free"
API_URL = "https://openrouter.ai/api/v1/chat/completions"


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = LingoraEngine()
    return _engine


def run_conversation(
    question: Optional[str] = None,
    messages: Optional[list] = None,
    conversation_id: Optional[int] = None,
) -> Dict[str, Any]:
    engine = get_engine()
    return engine.run_turn(
        question=question, messages=messages, conversation_id=conversation_id
    )


if __name__ == "__main__":
    import sys

    # By default, start the web server so `python app.py` runs the app.
    # Pass `--run-once` (or `run`) to execute a single conversation instead.
    if "--run-once" in sys.argv or "run" in sys.argv:
        try:
            result = run_conversation()
            logger.info("%s", result["final_message"])
            conv_id = result.get("conversation_id")
            logger.info("✅ Conversation saved (id: %s)", conv_id)
        except Exception:
            logger.exception("Failed to run conversation")
    else:
        # Start Flask server (uses create_app from web.py)
        from web import create_app

        app = create_app(run_conversation)
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port, debug=True)
