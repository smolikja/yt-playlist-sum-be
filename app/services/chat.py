"""
Chat service for orchestrating playlist summarization and conversation management.

This module integrates the RAG (Retrieval-Augmented Generation) pipeline:
- SummarizationService for Map-Reduce summarization
- IngestionService for vector indexing
- RetrievalService for context retrieval during chat
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from loguru import logger

from app.models import PlaylistRequest, SummaryResult, MessageRole, Playlist, LLMRole
from app.models.sql import ConversationModel, MessageModel
from app.models.api import SummaryContent
from app.services.youtube import YouTubeService
from app.services.ingestion import IngestionService
from app.services.summarization import SummarizationService
from app.services.retrieval import RetrievalService
from app.repositories.chat import ChatRepository
from app.core.exceptions import NotFoundError, ForbiddenError, BadRequestError, InternalServerError
from app.core.cache import get_cached_summary, set_cached_summary
from app.core.providers.llm_provider import LLMProvider, LLMMessage


from app.core.prompts import ChatPrompts

class ChatService:
    # ... (existing code) ...

    def _build_system_prompt(self, context: str, summary: Optional[str]) -> str:
        """
        Build the system prompt with dynamic context using the centralized template.

        Args:
            context: Retrieved context from RAG (if available).
            summary: Pre-computed playlist summary.

        Returns:
            Formatted system prompt.
        """
        return ChatPrompts.SYSTEM_INSTRUCTIONS.format(
            summary=summary or 'No summary available.',
            context=context or 'No specific context retrieved. Rely on the summary and chat history.'
        )

    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds to MM:SS or HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    # =========================================================================
    # CONVERSATION MANAGEMENT (unchanged from original)
    # =========================================================================

    async def delete_conversation(
        self, conversation_id: str, user_id: uuid.UUID
    ) -> None:
        """Delete a conversation if it exists and belongs to the user."""
        conversation = await self.chat_repository.get_conversation(conversation_id)
        if not conversation:
            logger.warning(f"Conversation {conversation_id} not found for deletion")
            raise NotFoundError("Conversation", conversation_id)

        if conversation.user_id != user_id:
            logger.warning(
                f"User {user_id} attempted to delete conversation {conversation_id} "
                f"owned by {conversation.user_id}"
            )
            raise ForbiddenError("You do not have permission to delete this conversation.")

        # Also delete indexed chunks
        if conversation.playlist_url:
            try:
                await self.ingestion_service.delete_playlist(conversation.playlist_url)
            except Exception as e:
                logger.warning(f"Failed to delete indexed chunks: {e}")

        await self.chat_repository.delete_conversation(conversation)
        logger.info(f"Conversation {conversation_id} deleted by user {user_id}")

    async def claim_conversation(
        self, conversation_id: str, user_id: uuid.UUID
    ) -> None:
        """Claim an anonymous conversation for a user."""
        conversation = await self.chat_repository.get_conversation(conversation_id)
        if not conversation:
            raise NotFoundError("Conversation", conversation_id)

        if conversation.user_id is not None:
            raise ForbiddenError(
                "Conversation is already claimed or owned by another user."
            )

        conversation.user_id = user_id
        await self.chat_repository.update_conversation(conversation)
        logger.info(f"Conversation {conversation_id} claimed by user {user_id}")

    async def get_history(
        self, user_id: uuid.UUID, limit: int = 20, offset: int = 0
    ) -> List[ConversationModel]:
        """Retrieve the conversation history for a user."""
        return await self.chat_repository.get_user_conversations(user_id, limit, offset)

    async def get_conversation_detail(
        self, conversation_id: str, user_id: uuid.UUID
    ) -> ConversationModel:
        """Retrieve full details of a conversation, including messages."""
        conversation = await self.chat_repository.get_conversation_with_messages(
            conversation_id, user_id
        )

        if not conversation:
            logger.warning(
                f"Conversation {conversation_id} not found for user {user_id}"
            )
            raise NotFoundError("Conversation", conversation_id)

        return conversation
