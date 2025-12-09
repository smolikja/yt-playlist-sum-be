import uuid
from typing import List
from loguru import logger
from fastapi import HTTPException, status
from app.models import PlaylistRequest, SummaryResult
from app.models.sql import ConversationModel
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
        summary_result = await self.llm_service.generate_summary(playlist)

        # 4. Save Conversation
        try:
            conversation = ConversationModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                title=summary_result.playlist_title,
                summary=summary_result.summary_markdown
            )
            await self.chat_repository.create_conversation(conversation)
            logger.info(f"Saved conversation {conversation.id} for user {user_id}")
        except Exception as e:
            # We don't want to fail the request if saving history fails, but we should log it
            logger.error(f"Failed to save conversation history: {e}")

        return summary_result

    async def get_history(self, user_id: str, limit: int = 20, offset: int = 0) -> List[ConversationModel]:
        """
        Retrieves the conversation history for a user.
        """
        return await self.chat_repository.get_user_conversations(user_id, limit, offset)
