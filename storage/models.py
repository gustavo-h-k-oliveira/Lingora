import datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from storage.tz import now_brasilia

from .db import Base


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model: Mapped[str] = mapped_column(String, nullable=False)
    # default timestamp in America/Sao_Paulo timezone (best-effort, falls back to UTC-3 fixed offset)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=now_brasilia
    )
    meta: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True, default=dict
    )
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )

    def __init__(self, model: str = "unknown", meta: Optional[Dict[str, Any]] = None):
        self.model = model
        if meta is not None:
            self.meta = meta


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conversations.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reasoning_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    conversation = relationship("Conversation", back_populates="messages")

    def __init__(
        self,
        conversation_id: int,
        role: str,
        content: Optional[str],
        reasoning_details: Optional[Any],
        position: int,
    ):
        self.conversation_id = conversation_id
        self.role = role
        self.content = content
        self.reasoning_details = reasoning_details
        self.position = position
