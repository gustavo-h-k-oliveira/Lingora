import logging
from typing import Any, Dict, cast

from storage.tz import now_brasilia

from .db import get_session, init_db
from .models import Conversation, Message

logger = logging.getLogger(__name__)

__all__ = ["save_conversation"]

# Ensure tables exist
init_db()

# Only these keys are allowed to be stored in the `meta` column
ALLOWED_META_KEYS = {"state", "language", "recurring_errors"}


def save_conversation(conversation: Dict[str, Any]) -> int:
    """Persist a conversation and its messages to the database.

    Conversation dict may include optional `meta` key (JSON).
    Only keys in `ALLOWED_META_KEYS` will be persisted in `meta`.
    Returns the created Conversation id.
    """
    session = get_session()
    try:
        raw_meta = conversation.get("meta") or {}
        sanitized_meta = {
            k: v
            for k, v in (raw_meta.items() if isinstance(raw_meta, dict) else [])
            if k in ALLOWED_META_KEYS
        }
        conv = Conversation(
            model=conversation.get("model", "unknown"), meta=sanitized_meta
        )
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
        conv = (
            session.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .one_or_none()
        )
        if conv is None:
            raise ValueError(f"Conversation with id={conversation_id} not found")
        # find current max position
        last_msg = (
            session.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.position.desc())
            .first()
        )
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


def update_conversation_meta(conversation_id: int, updates: dict) -> dict:
    """Merge `updates` into the conversation.meta field and return the new meta.

    Only keys in `ALLOWED_META_KEYS` will be persisted; other keys are ignored. This
    also prunes any existing disallowed keys from the stored meta.
    """
    session = get_session()
    try:
        conv = (
            session.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .one_or_none()
        )
        if conv is None:
            raise ValueError(f"Conversation with id={conversation_id} not found")

        current_meta = conv.meta if isinstance(conv.meta, dict) else {}
        # start with only allowed keys from the current meta
        new_meta = {
            k: current_meta.get(k) for k in ALLOWED_META_KEYS if k in current_meta
        }

        # merge allowed updates only
        for k, v in (updates.items() if isinstance(updates, dict) else []):
            if k not in ALLOWED_META_KEYS:
                continue
            if k == "recurring_errors":
                existing = set(new_meta.get("recurring_errors") or [])
                to_add = v if isinstance(v, (list, tuple, set)) else [v]
                existing.update(x for x in to_add if x)
                new_meta["recurring_errors"] = list(existing)
            else:
                new_meta[k] = v

        # Debug log before commit
        try:
            import json
            import os

            os.makedirs("logs", exist_ok=True)
            ts = now_brasilia().isoformat()
            with open("logs/meta_updates.log", "a", encoding="utf-8") as fh:
                fh.write(
                    json.dumps(
                        {
                            "ts": ts,
                            "conversation_id": conversation_id,
                            "new_meta_before_commit": new_meta,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        except Exception:
            logger.exception("Failed to write meta_updates.log before commit")

        # Use a direct UPDATE to avoid ORM JSON/serialization quirks and ensure DB stores the JSON
        try:
            import json as _json

            from sqlalchemy import text

            from .db import engine

            with engine.connect() as conn:
                conn.execute(
                    text("UPDATE conversations SET meta = :meta WHERE id = :id"),
                    {"meta": _json.dumps(new_meta), "id": conversation_id},
                )
                conn.commit()
        except Exception:
            # fallback to ORM commit if direct update fails
            logger.exception("Direct UPDATE failed, falling back to ORM commit")
            conv.meta = new_meta
            session.commit()

        # Debug log after commit
        try:
            import json
            import os

            os.makedirs("logs", exist_ok=True)
            ts2 = now_brasilia().isoformat()
            with open("logs/meta_updates.log", "a", encoding="utf-8") as fh:
                fh.write(
                    json.dumps(
                        {
                            "ts": ts2,
                            "conversation_id": conversation_id,
                            "committed_meta": new_meta,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            # double-check by re-querying via raw SQL
            from sqlalchemy import text

            from .db import engine as _engine

            with _engine.connect() as conn:
                row = conn.execute(
                    text("SELECT meta FROM conversations WHERE id = :id"),
                    {"id": conversation_id},
                ).fetchone()
                if row is not None:
                    with open("logs/meta_updates.log", "a", encoding="utf-8") as fh:
                        fh.write(
                            json.dumps(
                                {
                                    "ts": ts2,
                                    "conversation_id": conversation_id,
                                    "db_meta_raw": row[0],
                                },
                                ensure_ascii=False,
                            )
                            + "\n"
                        )
        except Exception:
            logger.exception("Failed to write meta updates or verify DB meta")

        return new_meta
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_conversation(conversation_id: int):
    session = get_session()
    try:
        conv = (
            session.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .one_or_none()
        )
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
        return {
            "id": conv.id,
            "model": conv.model,
            "created_at": conv.created_at.isoformat(),
            "meta": conv.meta or {},
            "messages": msgs,
        }
    finally:
        session.close()
