"""
API endpoints for playlist summarization, chat, and conversation management.
"""
from fastapi import APIRouter, Request, Depends, Query
from typing import List, Optional
from loguru import logger
import time

from app.models.api import (
    PlaylistRequest,
    SummaryResult,
    ConversationResponse,
    ChatRequest,
    ChatResponse,
    ConversationDetailResponse,
)
from app.services.chat import ChatService
from app.api.dependencies import get_chat_service
from app.api.auth import current_active_user, current_optional_user
from app.models.sql import User
from app.core.limiter import limiter
from app.core.exceptions import InternalServerError, AppException
from app.core.constants import (
    CONVERSATIONS_DEFAULT_LIMIT,
    CONVERSATIONS_MAX_LIMIT,
    RATE_LIMIT_SUMMARIZE,
    RATE_LIMIT_CHAT,
)


router = APIRouter()


@router.post("/summarize", response_model=SummaryResult)
@limiter.limit(RATE_LIMIT_SUMMARIZE)
async def summarize_playlist(
    request: Request,
    payload: PlaylistRequest,
    chat_service: ChatService = Depends(get_chat_service),
    user: Optional[User] = Depends(current_optional_user),
):
    """
    Summarizes a YouTube playlist by extracting video transcripts and processing them with AI.
    Saves the result as a conversation history for the user.

    Rate limit: 10 requests per minute.

    Args:
        request: FastAPI request object (required for rate limiting).
        payload: The request body containing the playlist URL.
        chat_service: The service handling the business logic.
        user: The authenticated user (optional).

    Returns:
        SummaryResult: A JSON object containing the generated summary text.
    """
    user_id = user.id if user else None
    logger.info(f"Incoming request for URL: {payload.url} from user {user_id}")
    
    start_time = time.perf_counter()
    result = await chat_service.create_session(user_id, payload)
    duration = time.perf_counter() - start_time
    logger.info(f"Summarization completed in {duration:.2f}s")
    return result


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(RATE_LIMIT_CHAT)
async def chat_with_playlist(
    request: Request,
    payload: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
    user: User = Depends(current_active_user),
):
    """
    Sends a message to the LLM within the context of a specific conversation/playlist.

    Rate limit: 30 requests per minute.

    Args:
        request: FastAPI request object (required for rate limiting).
        payload: The chat request containing conversation_id and message.
        chat_service: The service handling the business logic.
        user: The authenticated user.

    Returns:
        ChatResponse: The AI-generated response.
    """
    logger.info(f"Incoming chat message for conversation {payload.conversation_id} from user {user.id}")
    
    start_time = time.perf_counter()
    response_text = await chat_service.process_message(
        payload.conversation_id,
        payload.message,
        user.id,
        payload.use_rag,
    )
    duration = time.perf_counter() - start_time
    logger.info(f"Chat message processed in {duration:.2f}s")
    return ChatResponse(response=response_text)


@router.post("/conversations/{conversation_id}/claim")
async def claim_conversation(
    conversation_id: str,
    chat_service: ChatService = Depends(get_chat_service),
    user: User = Depends(current_active_user),
):
    """
    Claims an anonymous conversation for the authenticated user.

    Args:
        conversation_id: The ID of the conversation to claim.
        chat_service: The service handling the business logic.
        user: The authenticated user.

    Returns:
        Success message.
    """
    logger.info(f"User {user.id} claiming conversation {conversation_id}")
    await chat_service.claim_conversation(conversation_id, user.id)
    return {"status": "success", "message": "Conversation claimed successfully."}


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    chat_service: ChatService = Depends(get_chat_service),
    user: User = Depends(current_active_user),
):
    """
    Deletes a specific conversation.

    Args:
        conversation_id: The ID of the conversation to delete.
        chat_service: The service handling the business logic.
        user: The authenticated user.
    """
    logger.info(f"User {user.id} deleting conversation {conversation_id}")
    await chat_service.delete_conversation(conversation_id, user.id)
    return


@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    limit: int = Query(
        default=CONVERSATIONS_DEFAULT_LIMIT,
        ge=1,
        le=CONVERSATIONS_MAX_LIMIT,
        description=f"Max results (1-{CONVERSATIONS_MAX_LIMIT})",
    ),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    chat_service: ChatService = Depends(get_chat_service),
    user: User = Depends(current_active_user),
):
    """
    Retrieves the history of conversations for the authenticated user.

    Args:
        limit: Max number of results.
        offset: Pagination offset.
        chat_service: The service to fetch history.
        user: The authenticated user.

    Returns:
        List[ConversationResponse]: List of past conversations with snippets.
    """
    logger.info(f"Fetching conversations for user {user.id} (limit={limit}, offset={offset})")
    conversations = await chat_service.get_history(user.id, limit, offset)

    # Map to response model with summary truncation
    response = []
    for c in conversations:
        snippet = c.summary
        if snippet and len(snippet) > 200:
            snippet = snippet[:200] + "..."

        response.append(
            ConversationResponse(
                id=c.id,
                title=c.title,
                summary_snippet=snippet,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
        )

    return response


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation_detail(
    conversation_id: str,
    chat_service: ChatService = Depends(get_chat_service),
    user: User = Depends(current_active_user),
):
    """
    Retrieves full details of a specific conversation, including all messages.
    Performs security check to ensure the user owns the conversation.

    Args:
        conversation_id: The ID of the conversation.
        chat_service: The service handling the business logic.
        user: The authenticated user.

    Returns:
        ConversationDetailResponse: Full conversation details with messages.
    """
    logger.info(f"Fetching conversation details {conversation_id} for user {user.id}")
    return await chat_service.get_conversation_detail(conversation_id, user.id)
