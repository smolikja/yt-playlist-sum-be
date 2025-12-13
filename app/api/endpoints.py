from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from app.models.api import PlaylistRequest, SummaryResult, ConversationResponse, ChatRequest, ChatResponse, ConversationDetailResponse
from app.services.chat import ChatService
from app.api.dependencies import get_chat_service
from app.api.auth import current_active_user, current_optional_user
from app.models.sql import User
from loguru import logger
import time

router = APIRouter()

@router.post("/summarize", response_model=SummaryResult)
async def summarize_playlist(
    request: PlaylistRequest,
    chat_service: ChatService = Depends(get_chat_service),
    user: Optional[User] = Depends(current_optional_user)
):
    """
    Summarizes a YouTube playlist by extracting video transcripts and processing them with Gemini.
    Saves the result as a conversation history for the user.
    
    Args:
        request (PlaylistRequest): The request body containing the playlist URL.
        chat_service (ChatService): The service handling the business logic.
        user (Optional[User]): The authenticated user (optional).

    Returns:
        SummaryResult: A JSON object containing the generated summary text.
    """
    user_id = user.id if user else None
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
    user: User = Depends(current_active_user)
):
    """
    Sends a message to the LLM within the context of a specific conversation/playlist.
    """
    logger.info(f"Incoming chat message for conversation {request.conversation_id} from user {user.id}")
    try:
        start_time = time.perf_counter()
        response_text = await chat_service.process_message(request.conversation_id, request.message, user.id, request.use_transcripts)
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

@router.post("/conversations/{conversation_id}/claim", status_code=status.HTTP_200_OK)
async def claim_conversation(
    conversation_id: str,
    chat_service: ChatService = Depends(get_chat_service),
    user: User = Depends(current_active_user)
):
    """
    Claims an anonymous conversation for the authenticated user.
    """
    logger.info(f"User {user.id} claiming conversation {conversation_id}")
    try:
        await chat_service.claim_conversation(conversation_id, user.id)
        return {"status": "success", "message": "Conversation claimed successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error claiming conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while claiming the conversation."
        )

@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    chat_service: ChatService = Depends(get_chat_service),
    user: User = Depends(current_active_user)
):
    """
    Deletes a specific conversation.
    """
    logger.info(f"User {user.id} deleting conversation {conversation_id}")
    try:
        await chat_service.delete_conversation(conversation_id, user.id)
        return
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the conversation."
        )

@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    limit: int = 20,
    offset: int = 0,
    chat_service: ChatService = Depends(get_chat_service),
    user: User = Depends(current_active_user)
):
    """
    Retrieves the history of conversations for the authenticated user.
    
    Args:
        limit (int): Max number of results.
        offset (int): Pagination offset.
        chat_service (ChatService): The service to fetch history.
        user (User): The authenticated user.
        
    Returns:
        List[ConversationResponse]: List of past conversations with snippets.
    """
    logger.info(f"Fetching conversations for user {user.id} (limit={limit}, offset={offset})")
    conversations = await chat_service.get_history(user.id, limit, offset)
    
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
            created_at=c.created_at,
            updated_at=c.updated_at
        ))
        
    return response

@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation_detail(
    conversation_id: str,
    chat_service: ChatService = Depends(get_chat_service),
    user: User = Depends(current_active_user)
):
    """
    Retrieves full details of a specific conversation, including all messages.
    Performs security check to ensure the user owns the conversation.
    """
    logger.info(f"Fetching conversation details {conversation_id} for user {user.id}")
    return await chat_service.get_conversation_detail(conversation_id, user.id)
