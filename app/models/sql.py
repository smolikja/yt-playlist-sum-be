from sqlalchemy import Column, String, DateTime, func, JSON
from app.core.db import Base

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
        user_id (str): Anonymous user identifier.
        title (str): Title of the playlist or conversation.
        summary (str): The generated summary text.
        created_at (datetime): Timestamp of creation.
    """
    __tablename__ = "conversations"

    id = Column(String, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
    title = Column(String, nullable=True)
    summary = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now(), index=True)
