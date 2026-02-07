from typing import Any, Dict, cast
from datetime import datetime

from .db import get_session, init_db
from .models import Conversation, Message

__all__ = ["save_conversation"]

# Ensure tables exist
init_db()


def save_conversation(conversation: Dict[str, Any]) -> int:
    """Persist a conversation and its messages to the SQLite database.

    Returns the created Conversation id.
    """
    session = get_session()
    try:
        conv = Conversation(model=conversation.get("model", "unknown"))
        session.add(conv)
        session.flush()  # populate conv.id

        for idx, msg in enumerate(conversation.get("messages", [])):
            message = Message(
                conversation_id=conv.id,
                role=msg.get("role"),
                content=msg.get("content"),
                reasoning_details=msg.get("reasoning_details"),
                position=idx,
            )
            session.add(message)

        session.commit()
        return cast(int, conv.id)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
