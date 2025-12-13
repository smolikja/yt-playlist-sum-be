from functools import lru_cache
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.db import get_db_session
from app.repositories.video import VideoRepository
from app.repositories.chat import ChatRepository
from app.services.proxy import ProxyService
from app.services.youtube import YouTubeService
from app.services.llm import LLMService
from app.services.chat import ChatService

@lru_cache
def get_proxy_service() -> ProxyService:
    return ProxyService(
        host=settings.DATAIMPULSE_HOST,
        port=settings.DATAIMPULSE_PORT,
        login=settings.DATAIMPULSE_LOGIN,
        password=settings.DATAIMPULSE_PASSWORD
    )

def get_video_repository(db: AsyncSession = Depends(get_db_session)) -> VideoRepository:
    return VideoRepository(db)

def get_chat_repository(db: AsyncSession = Depends(get_db_session)) -> ChatRepository:
    return ChatRepository(db)

def get_youtube_service(
    proxy_service: ProxyService = Depends(get_proxy_service),
    video_repository: VideoRepository = Depends(get_video_repository)
) -> YouTubeService:
    return YouTubeService(proxy_service=proxy_service, video_repository=video_repository)

@lru_cache
def get_llm_service() -> LLMService:
    return LLMService(
        gemini_api_key=settings.GEMINI_API_KEY,
        gemini_model_name=settings.GEMINI_MODEL_NAME,
        groq_api_key=settings.GROQ_API_KEY,
        groq_model_name=settings.GROQ_MODEL_NAME
    )

def get_chat_service(
    youtube_service: YouTubeService = Depends(get_youtube_service),
    llm_service: LLMService = Depends(get_llm_service),
    chat_repository: ChatRepository = Depends(get_chat_repository)
) -> ChatService:
    return ChatService(youtube_service, llm_service, chat_repository)