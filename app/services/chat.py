import uuid
from typing import List
from loguru import logger
from fastapi import HTTPException, status
from app.models import PlaylistRequest, SummaryResult, MessageRole
from app.models.sql import ConversationModel, MessageModel
from app.services.youtube import YouTubeService
from app.services.llm import LLMService
from app.repositories.chat import ChatRepository

class ChatService:
    def __init__(
        self, 
        youtube_service: YouTubeService, 
        llm_service: LLMService, 
        chat_repository: ChatRepository
    ):
        self.youtube_service = youtube_service
        self.llm_service = llm_service
        self.chat_repository = chat_repository

    async def create_session(self, user_id: str, request: PlaylistRequest) -> SummaryResult:
        """
        Orchestrates the process of:
        1. Extracting playlist info.
        2. Fetching transcripts.
        3. generating summary.
        4. Saving the result as a conversation history.
        """
        logger.info(f"Starting chat session for user {user_id} with URL: {request.url}")

        # 1. Extract Playlist Info
        # Note: extract_playlist_info is synchronous in YouTubeService
        playlist = self.youtube_service.extract_playlist_info(str(request.url))
        
        if not playlist.videos:
            logger.warning(f"No videos found for URL: {request.url}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="No videos found in the provided playlist URL."
            )

        # 2. Fetch Transcripts
        playlist = await self.youtube_service.fetch_transcripts(playlist)

        valid_videos = [v for v in playlist.videos if v.transcript]
        if not valid_videos:
             logger.warning("No valid transcripts found.")
             raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Could not retrieve transcripts for any videos in the playlist."
            )

        # 3. Generate Summary
        generated_content = await self.llm_service.generate_summary(playlist)

        # 4. Save Conversation
        try:
            conversation = ConversationModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                title=generated_content.playlist_title,
                playlist_url=str(request.url),
                summary=generated_content.summary_markdown
            )
            await self.chat_repository.create_conversation(conversation)
            
            # Construct final result with the mandatory conversation_id
            final_summary_result = SummaryResult(
                conversation_id=conversation.id,
                **generated_content.model_dump()
            )
            logger.info(f"Saved conversation {conversation.id} for user {user_id}")
        except Exception as e:
            # We don't want to fail the request if saving history fails, but we should log it
            logger.error(f"Failed to save conversation history: {e}")
            # In case of DB failure, we might want to return the summary anyway, 
            # but we can't provide a valid conversation_id. 
            # Given strict API contract, we should probably raise error or handle gracefully.
            # For now, we'll re-raise as we promised a conversation_id.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save conversation."
            )

        return final_summary_result

    async def process_message(self, conversation_id: str, user_message: str, use_transcripts: bool = False) -> str:
        """
        Processes a user message in a conversation.
        """
        logger.debug(f"Processing message for conversation {conversation_id}")
        
        # 1. Fetch conversation
        conversation = await self.chat_repository.get_conversation(conversation_id)
        if not conversation:
            logger.warning(f"Conversation {conversation_id} not found")
            raise HTTPException(status_code=404, detail="Conversation not found")

        # 2. Fetch transcripts (using cache) if requested
        context_text = ""
        if use_transcripts:
            logger.debug(f"Fetching context for playlist {conversation.playlist_url}")
            playlist = self.youtube_service.extract_playlist_info(conversation.playlist_url)
            transcripts = await self.youtube_service.fetch_transcripts(playlist)
            context_text = self.llm_service.prepare_context(transcripts)
        else:
            logger.debug("Skipping transcript fetch (use_transcripts=False)")

        # 3. Fetch history
        history = await self.chat_repository.get_messages(conversation_id)

        # 4. Call LLM
        logger.debug(f"Calling LLM for conversation {conversation_id}")
        response_text = await self.llm_service.chat_completion(context_text, history, user_message)

        # 5. Save messages
        user_msg = MessageModel(
            conversation_id=conversation_id, 
            role=MessageRole.USER.value, 
            content=user_message
        )
        await self.chat_repository.add_message(user_msg)

        model_msg = MessageModel(
            conversation_id=conversation_id, 
            role=MessageRole.MODEL.value, 
            content=response_text
        )
        await self.chat_repository.add_message(model_msg)
        
        logger.debug(f"Message processed and saved for conversation {conversation_id}")

        return response_text

    async def get_history(self, user_id: str, limit: int = 20, offset: int = 0) -> List[ConversationModel]:
        """
        Retrieves the conversation history for a user.
        """
        return await self.chat_repository.get_user_conversations(user_id, limit, offset)

    async def get_conversation_detail(self, conversation_id: str, user_id: str) -> ConversationModel:
        """
        Retrieves full details of a conversation, including messages.
        Enforces ownership validation.
        """
        conversation = await self.chat_repository.get_conversation_with_messages(conversation_id, user_id)
        
        if not conversation:
            # We return 404 both if it doesn't exist OR if user_id doesn't match
            # (since our repo query filters by both)
            logger.warning(f"Conversation {conversation_id} not found for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
            
        return conversation
