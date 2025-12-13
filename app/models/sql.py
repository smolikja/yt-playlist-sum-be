from sqlalchemy import Column, String, DateTime, func, JSON, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from app.core.db import Base
import uuid

class User(SQLAlchemyBaseUserTableUUID, Base):
    """
    SQLAlchemy ORM model representing an authenticated user.
    """
    __tablename__ = "users"

class VideoModel(Base):
    """
    SQLAlchemy ORM model representing a cached YouTube video transcript.

    Attributes:
        id (str): The YouTube Video ID (Primary Key).
        title (str): The title of the video.
        transcript (list): The transcript data stored as a JSON array of segment objects.
        language (str): The language code of the transcript (default: 'en').
        created_at (datetime): The timestamp when the record was created.
    """
    __tablename__ = "videos"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=True)
    transcript = Column(JSON, nullable=True)  # Stores list of transcript segments
    language = Column(String, default='en')
    created_at = Column(DateTime, default=func.now())


class ConversationModel(Base):
    """
    SQLAlchemy ORM model representing a user conversation/summary session.

    Attributes:
        id (str): Unique identifier for the conversation (UUID).
        user_id (UUID): Foreign key to the user.
        playlist_url (str): The URL of the playlist.
        title (str): Title of the playlist or conversation.
        summary (str): The generated summary text.
        created_at (datetime): Timestamp of creation.
    """
    __tablename__ = "conversations"

    id = Column(String, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=True)
    playlist_url = Column(String, nullable=True)
    title = Column(String, nullable=True)
    summary = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), server_default=func.now(), nullable=False)

    messages = relationship("MessageModel", back_populates="conversation", cascade="all, delete-orphan")
    user = relationship("User", backref="conversations")


class MessageModel(Base):
    """
    SQLAlchemy ORM model representing a message in a conversation.

    Attributes:
        id (int): Unique identifier for the message (Auto-increment).
        conversation_id (str): Foreign key to the conversation.
        role (str): The role of the message sender ('user' or 'model').
        content (str): The content of the message.
        created_at (datetime): Timestamp of creation.
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # 'user' or 'model'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())

    conversation = relationship("ConversationModel", back_populates="messages")
