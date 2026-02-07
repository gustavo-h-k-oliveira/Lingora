from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .db import Base
import datetime


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True)
    model = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    reasoning_details = Column(JSON, nullable=True)
    position = Column(Integer, nullable=False)
    conversation = relationship("Conversation", back_populates="messages")
