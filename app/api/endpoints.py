from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from app.models.api import PlaylistRequest, SummaryResult, ConversationResponse, ChatRequest, ChatResponse
from app.services.chat import ChatService
from app.api.dependencies import get_chat_service, get_user_identifier
from loguru import logger
import time

router = APIRouter()

@router.post("/summarize", response_model=SummaryResult)
async def summarize_playlist(
    request: PlaylistRequest,
    chat_service: ChatService = Depends(get_chat_service),
    user_id: str = Depends(get_user_identifier)
):
    """
    Summarizes a YouTube playlist by extracting video transcripts and processing them with Gemini.
    Saves the result as a conversation history for the user.
    
    Args:
        request (PlaylistRequest): The request body containing the playlist URL.
        chat_service (ChatService): The service handling the business logic.
        user_id (str): The anonymous user identifier from the header.

    Returns:
        SummaryResult: A JSON object containing the generated summary text.
    """
    logger.info(f"Incoming request for URL: {request.url} from user {user_id}")
    try:
        start_time = time.perf_counter()
        result = await chat_service.create_session(user_id, request)
        duration = time.perf_counter() - start_time
        logger.info(f"Summarization completed in {duration:.2f}s")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing playlist summarization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="An error occurred while processing the playlist."
        )

@router.post("/chat", response_model=ChatResponse)
async def chat_with_playlist(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
    user_id: str = Depends(get_user_identifier)
):
    """
    Sends a message to the LLM within the context of a specific conversation/playlist.
    """
    logger.info(f"Incoming chat message for conversation {request.conversation_id} from user {user_id}")
    try:
        start_time = time.perf_counter()
        response_text = await chat_service.process_message(request.conversation_id, request.message)
        duration = time.perf_counter() - start_time
        logger.info(f"Chat message processed in {duration:.2f}s")
        return ChatResponse(response=response_text)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="An error occurred while processing the chat message."
        )

@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    limit: int = 20,
    offset: int = 0,
    chat_service: ChatService = Depends(get_chat_service),
    user_id: str = Depends(get_user_identifier)
):
    """
    Retrieves the history of conversations for the authenticated (anonymous) user.
    
    Args:
        limit (int): Max number of results.
        offset (int): Pagination offset.
        chat_service (ChatService): The service to fetch history.
        user_id (str): The anonymous user identifier.
        
    Returns:
        List[ConversationResponse]: List of past conversations with snippets.
    """
    logger.info(f"Fetching conversations for user {user_id} (limit={limit}, offset={offset})")
    conversations = await chat_service.get_history(user_id, limit, offset)
    
    # Map to response model (ConversationResponse handles formatting, but we need to create the snippet here if not in model)
    # The Pydantic model doesn't automatically truncate 'summary' to 'summary_snippet' unless we added a validator or computed field.
    # So we do it manually here.
    
    response = []
    for c in conversations:
        snippet = c.summary
        if snippet and len(snippet) > 200:
            snippet = snippet[:200] + "..."
            
        response.append(ConversationResponse(
            id=c.id,
            title=c.title,
            summary_snippet=snippet,
            created_at=c.created_at
        ))
        
    return response
