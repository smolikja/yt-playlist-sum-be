"""
Chat service for orchestrating playlist summarization and conversation management.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from loguru import logger

from app.models import PlaylistRequest, SummaryResult, MessageRole
from app.models.sql import ConversationModel, MessageModel
from app.services.youtube import YouTubeService
from app.services.llm import LLMService
from app.repositories.chat import ChatRepository
from app.core.exceptions import NotFoundError, ForbiddenError, BadRequestError, InternalServerError
from app.core.cache import get_cached_summary, set_cached_summary, CachedSummary


class ChatService:
    """Service for managing chat sessions and conversations."""

    def __init__(
        self,
        youtube_service: YouTubeService,
        llm_service: LLMService,
        chat_repository: ChatRepository,
    ):
        """
        Initialize the ChatService.

        Args:
            youtube_service: Service for YouTube operations.
            llm_service: Service for LLM operations.
            chat_repository: Repository for chat data access.
        """
        self.youtube_service = youtube_service
        self.llm_service = llm_service
        self.chat_repository = chat_repository

    async def create_session(
        self, user_id: Optional[uuid.UUID], request: PlaylistRequest
    ) -> SummaryResult:
        """
        Orchestrate the process of summarizing a playlist.

        1. Check cache for existing summary.
        2. Extract playlist info.
        3. Fetch transcripts.
        4. Generate summary.
        5. Save the result as a conversation history.
        6. Cache the summary.

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
            # Create new conversation for this user with cached data
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

        # 1. Extract Playlist Info (now async)
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

        # 3. Generate Summary
        generated_content = await self.llm_service.generate_summary(playlist)

        # 4. Save Conversation
        try:
            conversation = ConversationModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                title=generated_content.playlist_title,
                playlist_url=url_str,
                summary=generated_content.summary_markdown,
            )
            await self.chat_repository.create_conversation(conversation)

            final_summary_result = SummaryResult(
                conversation_id=conversation.id,
                **generated_content.model_dump(),
            )
            logger.info(f"Saved conversation {conversation.id} for user {user_id}")

            # 5. Cache the summary
            set_cached_summary(
                url_str,
                {
                    "playlist_title": generated_content.playlist_title,
                    "video_count": generated_content.video_count,
                    "summary_markdown": generated_content.summary_markdown,
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
        use_transcripts: bool = False,
    ) -> str:
        """
        Process a user message in a conversation.

        Args:
            conversation_id: The conversation ID.
            user_message: The user's message.
            user_id: The user ID.
            use_transcripts: Whether to include full transcripts in context.

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

        # 2. Fetch transcripts (using cache) if requested
        context_text = ""
        if use_transcripts:
            logger.debug(f"Fetching context for playlist {conversation.playlist_url}")
            playlist = await self.youtube_service.extract_playlist_info(
                conversation.playlist_url
            )
            transcripts = await self.youtube_service.fetch_transcripts(playlist)
            context_text = self.llm_service.prepare_context(transcripts)
        else:
            logger.debug("Skipping transcript fetch (use_transcripts=False)")

        # 3. Fetch history
        history = await self.chat_repository.get_messages(conversation_id)

        # 4. Call LLM
        logger.debug(f"Calling LLM for conversation {conversation_id}")
        response_text = await self.llm_service.chat_completion(
            context_text, conversation.summary, history, user_message
        )

        # 5. Save messages
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

        # Update conversation timestamp
        conversation.updated_at = datetime.now(timezone.utc)
        await self.chat_repository.update_conversation(conversation)

        logger.debug(f"Message processed and saved for conversation {conversation_id}")

        return response_text

    async def delete_conversation(
        self, conversation_id: str, user_id: uuid.UUID
    ) -> None:
        """
        Delete a conversation if it exists and belongs to the user.

        Args:
            conversation_id: The conversation ID.
            user_id: The user ID.

        Raises:
            NotFoundError: If conversation not found.
            ForbiddenError: If user doesn't own the conversation.
        """
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

        await self.chat_repository.delete_conversation(conversation)
        logger.info(f"Conversation {conversation_id} deleted by user {user_id}")

    async def claim_conversation(
        self, conversation_id: str, user_id: uuid.UUID
    ) -> None:
        """
        Claim an anonymous conversation for a user.

        Args:
            conversation_id: The conversation ID.
            user_id: The user ID.

        Raises:
            NotFoundError: If conversation not found.
            ForbiddenError: If conversation is already claimed.
        """
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
        """
        Retrieve the conversation history for a user.

        Args:
            user_id: The user ID.
            limit: Maximum number of results.
            offset: Pagination offset.

        Returns:
            List of ConversationModel objects.
        """
        return await self.chat_repository.get_user_conversations(user_id, limit, offset)

    async def get_conversation_detail(
        self, conversation_id: str, user_id: uuid.UUID
    ) -> ConversationModel:
        """
        Retrieve full details of a conversation, including messages.

        Enforces ownership validation.

        Args:
            conversation_id: The conversation ID.
            user_id: The user ID.

        Returns:
            ConversationModel with messages.

        Raises:
            NotFoundError: If conversation not found or user doesn't own it.
        """
        conversation = await self.chat_repository.get_conversation_with_messages(
            conversation_id, user_id
        )

        if not conversation:
            logger.warning(
                f"Conversation {conversation_id} not found for user {user_id}"
            )
            raise NotFoundError("Conversation", conversation_id)

        return conversation
