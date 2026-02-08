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


def append_messages(conversation_id: int, new_messages: list) -> int:
    """Append messages to an existing conversation. Returns the conversation id."""
    session = get_session()
    try:
        conv = session.query(Conversation).filter(Conversation.id == conversation_id).one_or_none()
        if conv is None:
            raise ValueError(f"Conversation with id={conversation_id} not found")
        # find current max position
        last_msg = session.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.position.desc()).first()
        start = last_msg.position + 1 if last_msg is not None else 0
        for idx, msg in enumerate(new_messages):
            message = Message(
                conversation_id=conversation_id,
                role=msg.get("role"),
                content=msg.get("content"),
                reasoning_details=msg.get("reasoning_details"),
                position=start + idx,
            )
            session.add(message)
        session.commit()
        return conversation_id
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_conversation(conversation_id: int):
    session = get_session()
    try:
        conv = session.query(Conversation).filter(Conversation.id == conversation_id).one_or_none()
        if conv is None:
            return None
        msgs = [
            {
                "role": m.role,
                "content": m.content,
                "reasoning_details": m.reasoning_details,
                "position": m.position,
            }
            for m in sorted(conv.messages, key=lambda x: x.position)
        ]
        return {"id": conv.id, "model": conv.model, "created_at": conv.created_at.isoformat(), "messages": msgs}
    finally:
        session.close()
