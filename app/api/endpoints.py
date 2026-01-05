"""
API endpoints for playlist summarization, chat, conversation management, and background jobs.
"""
import asyncio
from fastapi import APIRouter, Request, Depends, Query
from typing import List, Optional
import uuid
from loguru import logger
import time

from app.models.api import (
    PlaylistRequest,
    SummaryResult,
    ConversationResponse,
    ChatRequest,
    ChatResponse,
    ConversationDetailResponse,
    JobResponse,
    JobClaimResponse,
    SummarizeResponse,
)
from app.services.chat import ChatService
from app.services.job_service import JobService
from app.api.dependencies import get_chat_service, get_job_service
from app.api.auth import current_active_user, current_optional_user
from app.models.sql import User
from app.core.limiter import limiter
from app.core.exceptions import PublicTimeoutError
from app.core.constants import PaginationConfig, RateLimitConfig
from app.core.config import settings


router = APIRouter()


# =============================================================================
# SUMMARIZATION ENDPOINT (DUAL-MODE)
# =============================================================================

@router.post("/summarize", response_model=SummarizeResponse)
@limiter.limit(RateLimitConfig.SUMMARIZE)
async def summarize_playlist(
    request: Request,
    payload: PlaylistRequest,
    chat_service: ChatService = Depends(get_chat_service),
    job_service: JobService = Depends(get_job_service),
    user: Optional[User] = Depends(current_optional_user),
):
    """
    Summarizes a YouTube playlist by extracting video transcripts and processing them with AI.

    **Dual-mode operation:**
    - **Public users**: Synchronous with timeout. Returns error if exceeded.
    - **Authenticated users**: Creates async job. Poll `/jobs/{id}` for status.

    Rate limit: 10 requests per minute.

    Args:
        request: FastAPI request object (required for rate limiting).
        payload: The request body containing the playlist URL.
        chat_service: The service handling the business logic.
        job_service: The service for job management.
        user: The authenticated user (optional).

    Returns:
        SummarizeResponse: Contains either summary (sync) or job reference (async).
    """
    if user is None:
        # Public user: synchronous with timeout
        logger.info(f"Public user summarization request for URL: {payload.url}")
        
        start_time = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                chat_service.create_session(None, payload),
                timeout=settings.PUBLIC_SUMMARIZATION_TIMEOUT_SECONDS,
            )
            duration = time.perf_counter() - start_time
            logger.info(f"Public summarization completed in {duration:.2f}s")
            return SummarizeResponse(mode="sync", summary=result)
            
        except asyncio.TimeoutError:
            logger.warning(
                f"Public summarization timeout ({settings.PUBLIC_SUMMARIZATION_TIMEOUT_SECONDS}s) "
                f"for URL: {payload.url}"
            )
            raise PublicTimeoutError(
                "Playlist je příliš komplexní pro nepřihlášené uživatele. "
                "Zaregistrujte se pro neomezený přístup k sumarizaci."
            )
    else:
        # Authenticated user: create async job
        logger.info(f"Creating job for user {user.id}, URL: {payload.url}")
        
        job = await job_service.create_job(user.id, str(payload.url))
        return SummarizeResponse(mode="async", job=JobResponse.model_validate(job))


# =============================================================================
# JOB ENDPOINTS
# =============================================================================

@router.get("/jobs", response_model=List[JobResponse])
async def get_user_jobs(
    job_service: JobService = Depends(get_job_service),
    user: User = Depends(current_active_user),
):
    """
    Get all background jobs for the authenticated user.

    Args:
        job_service: The service handling job management.
        user: The authenticated user.

    Returns:
        List[JobResponse]: List of user's jobs.
    """
    jobs = await job_service.get_user_jobs(user.id)
    return [JobResponse.model_validate(job) for job in jobs]


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: uuid.UUID,
    job_service: JobService = Depends(get_job_service),
    user: User = Depends(current_active_user),
):
    """
    Get status of a specific background job.

    Args:
        job_id: The UUID of the job.
        job_service: The service handling job management.
        user: The authenticated user.

    Returns:
        JobResponse: The job status.
    """
    job = await job_service.get_job_status(job_id, user.id)
    return JobResponse.model_validate(job)


@router.post("/jobs/{job_id}/claim", response_model=JobClaimResponse)
async def claim_job(
    job_id: uuid.UUID,
    job_service: JobService = Depends(get_job_service),
    user: User = Depends(current_active_user),
):
    """
    Claim a completed job and transform it into a conversation.

    The job is deleted after claiming. The conversation becomes visible
    in the user's conversation list.

    Args:
        job_id: The UUID of the job to claim.
        job_service: The service handling job management.
        user: The authenticated user.

    Returns:
        JobClaimResponse: The created conversation details.
    """
    logger.info(f"User {user.id} claiming job {job_id}")
    conversation = await job_service.claim_job(job_id, user.id)
    return JobClaimResponse(conversation=conversation)


@router.post("/jobs/{job_id}/retry", response_model=JobResponse)
async def retry_job(
    job_id: uuid.UUID,
    job_service: JobService = Depends(get_job_service),
    user: User = Depends(current_active_user),
):
    """
    Retry a failed job.

    Resets the job status to pending for reprocessing.

    Args:
        job_id: The UUID of the job to retry.
        job_service: The service handling job management.
        user: The authenticated user.

    Returns:
        JobResponse: The updated job status.
    """
    logger.info(f"User {user.id} retrying job {job_id}")
    job = await job_service.retry_job(job_id, user.id)
    return JobResponse.model_validate(job)


@router.delete("/jobs/{job_id}", status_code=204)
async def cancel_job(
    job_id: uuid.UUID,
    job_service: JobService = Depends(get_job_service),
    user: User = Depends(current_active_user),
):
    """
    Cancel/delete a pending or failed job.

    Running jobs cannot be cancelled. Completed jobs should be claimed instead.

    Args:
        job_id: The UUID of the job to cancel.
        job_service: The service handling job management.
        user: The authenticated user.
    """
    logger.info(f"User {user.id} cancelling job {job_id}")
    await job_service.cancel_job(job_id, user.id)
    return


# =============================================================================
# CHAT ENDPOINTS
# =============================================================================

@router.post("/chat", response_model=ChatResponse)
@limiter.limit(RateLimitConfig.CHAT)
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


# =============================================================================
# CONVERSATION ENDPOINTS
# =============================================================================

@router.post("/conversations/{conversation_id}/claim")
async def claim_conversation(
    conversation_id: str,
    chat_service: ChatService = Depends(get_chat_service),
    user: User = Depends(current_active_user),
):
    """
    Claims an anonymous conversation for the authenticated user.

    This is for public users who created a conversation without login
    and later want to associate it with their account.

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
        default=PaginationConfig.DEFAULT_LIMIT,
        ge=1,
        le=PaginationConfig.MAX_LIMIT,
        description=f"Max results (1-{PaginationConfig.MAX_LIMIT})",
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