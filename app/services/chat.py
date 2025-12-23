"""
Chat service for orchestrating playlist summarization and conversation management.

This module integrates the RAG (Retrieval-Augmented Generation) pipeline:
- SummarizationService for Map-Reduce summarization
- IngestionService for vector indexing
- RetrievalService for context retrieval during chat
"""
import uuid
from datetime import datetime
from typing import List, Optional

from loguru import logger

from app.models import PlaylistRequest, SummaryResult, MessageRole, LLMRole
from app.models.sql import ConversationModel, MessageModel
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
    """
    Service for managing chat sessions and conversations with RAG integration.
    
    This service orchestrates:
    1. Playlist summarization using Map-Reduce approach
    2. Vector embedding and indexing of transcripts
    3. RAG-based chat with semantic retrieval
    """

    def __init__(
        self,
        youtube_service: YouTubeService,
        summarization_service: SummarizationService,
        ingestion_service: IngestionService,
        retrieval_service: RetrievalService,
        chat_llm_provider: LLMProvider,
        chat_repository: ChatRepository,
    ):
        """
        Initialize the ChatService with RAG components.

        Args:
            youtube_service: Service for YouTube operations.
            summarization_service: Service for Map-Reduce summarization.
            ingestion_service: Service for vector indexing.
            retrieval_service: Service for RAG retrieval.
            chat_llm_provider: LLM provider for chat responses.
            chat_repository: Repository for chat data access.
        """
        self.youtube_service = youtube_service
        self.summarization_service = summarization_service
        self.ingestion_service = ingestion_service
        self.retrieval_service = retrieval_service
        self.chat_llm_provider = chat_llm_provider
        self.chat_repository = chat_repository

    async def create_session(
        self, user_id: Optional[uuid.UUID], request: PlaylistRequest
    ) -> SummaryResult:
        """
        Orchestrate the process of summarizing a playlist with RAG indexing.

        Flow:
        1. Check cache for existing summary
        2. Extract playlist info
        3. Fetch transcripts
        4. Generate summary using Map-Reduce
        5. Index transcripts for RAG
        6. Save conversation
        7. Cache the summary

        Args:
            user_id: The user ID (optional for anonymous usage).
            request: The playlist request containing the URL.

        Returns:
            SummaryResult: The generated summary with conversation ID.

        Raises:
            BadRequestError: If no videos found in the playlist.
            NotFoundError: If no transcripts could be retrieved.
            InternalServerError: If saving the conversation fails.
        """
        url_str = str(request.url)
        logger.info(f"Starting chat session for user {user_id} with URL: {url_str}")

        # Check cache first
        cached = get_cached_summary(url_str)
        if cached:
            logger.info(f"Cache hit for URL: {url_str}")
            conversation = ConversationModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                title=cached["playlist_title"],
                playlist_url=url_str,
                summary=cached["summary_markdown"],
            )
            await self.chat_repository.create_conversation(conversation)
            return SummaryResult(
                conversation_id=conversation.id,
                playlist_title=cached["playlist_title"],
                video_count=cached["video_count"],
                summary_markdown=cached["summary_markdown"],
            )

        # 1. Extract Playlist Info
        playlist = await self.youtube_service.extract_playlist_info(url_str)

        if not playlist.videos:
            logger.warning(f"No videos found for URL: {url_str}")
            raise BadRequestError("No videos found in the provided playlist URL.")

        # 2. Fetch Transcripts
        playlist = await self.youtube_service.fetch_transcripts(playlist)

        valid_videos = [v for v in playlist.videos if v.transcript]
        if not valid_videos:
            logger.warning("No valid transcripts found.")
            raise NotFoundError("transcripts", url_str)

        # 3. Generate Summary (adaptive: direct for single video, Map-Reduce for playlist)
        is_single_video = len(valid_videos) == 1
        if is_single_video:
            logger.info("Generating summary for single video...")
        else:
            logger.info(f"Generating summary using Map-Reduce for {len(valid_videos)} videos...")
        summary_markdown = await self.summarization_service.summarize_playlist(playlist)

        # 4. Index Transcripts for RAG
        logger.info("Indexing transcripts for RAG...")
        try:
            chunk_count = await self.ingestion_service.ingest_playlist(
                playlist, 
                namespace=url_str,  # Use URL as namespace for retrieval
            )
            logger.info(f"Indexed {chunk_count} chunks for RAG")
        except Exception as e:
            # Log but don't fail - RAG indexing is not critical for basic functionality
            logger.error(f"Failed to index transcripts for RAG: {e}")

        # 5. Save Conversation
        try:
            conversation = ConversationModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                title=playlist.title,
                playlist_url=url_str,
                summary=summary_markdown,
            )
            await self.chat_repository.create_conversation(conversation)

            final_summary_result = SummaryResult(
                conversation_id=conversation.id,
                playlist_title=playlist.title,
                video_count=len(playlist.videos),
                summary_markdown=summary_markdown,
            )
            logger.info(f"Saved conversation {conversation.id} for user {user_id}")

            # 6. Cache the summary
            set_cached_summary(
                url_str,
                {
                    "playlist_title": playlist.title,
                    "video_count": len(playlist.videos),
                    "summary_markdown": summary_markdown,
                },
            )

        except Exception as e:
            logger.error(f"Failed to save conversation history: {e}")
            raise InternalServerError("Failed to save conversation.")

        return final_summary_result

    async def process_message(
        self,
        conversation_id: str,
        user_message: str,
        user_id: uuid.UUID,
        use_rag: bool = True,
    ) -> str:
        """
        Process a user message using RAG for context retrieval.

        Flow:
        1. Validate conversation ownership
        2. Fetch chat history
        3. Transform query to standalone (if history exists)
        4. Retrieve relevant chunks from vector store
        5. Build dynamic prompt with context
        6. Generate response
        7. Save messages

        Args:
            conversation_id: The conversation ID.
            user_message: The user's message.
            user_id: The user ID.
            use_rag: Whether to use RAG for context retrieval (default: True).

        Returns:
            str: The AI-generated response.

        Raises:
            NotFoundError: If conversation not found.
            ForbiddenError: If user doesn't own the conversation.
        """
        logger.debug(f"Processing message for conversation {conversation_id}")

        # 1. Fetch conversation
        conversation = await self.chat_repository.get_conversation(conversation_id)
        if not conversation:
            logger.warning(f"Conversation {conversation_id} not found")
            raise NotFoundError("Conversation", conversation_id)

        # Security check: Ensure user owns this conversation
        if conversation.user_id != user_id:
            logger.warning(
                f"User {user_id} attempted to access conversation {conversation_id} "
                f"owned by {conversation.user_id}"
            )
            raise ForbiddenError("You do not have permission to access this conversation.")

        # 2. Fetch history
        history = await self.chat_repository.get_messages(conversation_id)
        history_dicts = [{"role": m.role, "content": m.content} for m in history]

        # 3. Transform query and retrieve context
        context_text = ""
        if use_rag and conversation.playlist_url:
            try:
                # Transform query to standalone
                standalone_query = await self.retrieval_service.transform_query(
                    user_message, history_dicts
                )

                # Retrieve relevant chunks
                results = await self.retrieval_service.retrieve_context(
                    query=standalone_query,
                    namespace=conversation.playlist_url,
                    top_k=5,
                )

                # Format context with timestamps
                context_text = self.retrieval_service.format_context(results)
                logger.debug(f"Retrieved {len(results)} chunks for context")
            except Exception as e:
                logger.warning(f"RAG retrieval failed, falling back to summary only: {e}")

        # 4. Build dynamic prompt
        system_prompt = self._build_system_prompt(
            context=context_text,
            summary=conversation.summary,
        )

        # Build messages for LLM
        messages = [LLMMessage(role=LLMRole.SYSTEM, content=system_prompt)]

        # Add last 5 messages from history
        for msg in history[-5:]:
            role = LLMRole.USER if msg.role == MessageRole.USER.value else LLMRole.ASSISTANT
            messages.append(LLMMessage(role=role, content=msg.content))

        messages.append(LLMMessage(role=LLMRole.USER, content=user_message))

        # 5. Generate response
        logger.debug(f"Calling LLM for conversation {conversation_id}")
        response = await self.chat_llm_provider.generate_text(
            messages=messages,
            temperature=0.7,
        )
        response_text = response.content

        # 6. Save messages
        user_msg = MessageModel(
            conversation_id=conversation_id,
            role=MessageRole.USER.value,
            content=user_message,
        )
        await self.chat_repository.add_message(user_msg)

        model_msg = MessageModel(
            conversation_id=conversation_id,
            role=MessageRole.MODEL.value,
            content=response_text,
        )
        await self.chat_repository.add_message(model_msg)

        # Update conversation timestamp (use naive datetime for TIMESTAMP WITHOUT TIME ZONE)
        conversation.updated_at = datetime.utcnow()
        await self.chat_repository.update_conversation(conversation)

        logger.debug(f"Message processed and saved for conversation {conversation_id}")

        return response_text

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
    # CONVERSATION MANAGEMENT
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