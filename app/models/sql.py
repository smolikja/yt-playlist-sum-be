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


class DocumentEmbedding(Base):
    """
    SQLAlchemy ORM model for document embeddings in the vector store.
    
    Uses pgvector extension for vector operations and HNSW indexing.
    The migration c9d0e1f2a3b4 converts this to native vector(384) type.
    
    Attributes:
        id (str): Unique identifier ({video_id}_{chunk_index}).
        content (str): The text content of the chunk.
        embedding: The embedding vector (384 dimensions for all-MiniLM-L6-v2).
        chunk_metadata (dict): Additional metadata (video_id, timestamps, etc.).
        namespace (str): Grouping key (typically playlist URL).
        created_at (datetime): Timestamp of creation.
    """
    __tablename__ = "document_embeddings"

    id = Column(String, primary_key=True)
    content = Column(Text, nullable=False)
    # Stored as Text in base migration, converted to vector(384) by c9d0e1f2a3b4
    embedding = Column(Text, nullable=False)
    # Note: Cannot use 'metadata' as it's reserved by SQLAlchemy
    chunk_metadata = Column(JSON, default={})
    namespace = Column(String, index=True, nullable=True)
    created_at = Column(DateTime, default=func.now())


class JobModel(Base):
    """
    SQLAlchemy ORM model representing a background summarization job.
    
    Jobs are created for authenticated users when summarizing large playlists.
    Once completed, a job can be "claimed" which transforms it into a conversation.
    
    Attributes:
        id (UUID): Unique identifier for the job.
        user_id (UUID): Foreign key to the user who created the job.
        playlist_url (str): The YouTube playlist URL to summarize.
        status (str): Current job status (pending, running, completed, failed).
        error_message (str): Error details if job failed.
        result_conversation_id (str): FK to created conversation when completed.
        created_at (datetime): When the job was created.
        started_at (datetime): When processing started.
        completed_at (datetime): When processing finished.
        expires_at (datetime): When the job will be auto-deleted.
    """
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    playlist_url = Column(String, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    error_message = Column(Text, nullable=True)
    result_conversation_id = Column(String, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User", backref="jobs")
    result_conversation = relationship("ConversationModel", foreign_keys=[result_conversation_id])


