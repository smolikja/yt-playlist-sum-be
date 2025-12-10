import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.services.chat import ChatService
from app.models.sql import ConversationModel

async def test_chat_logic():
    # Mock dependencies
    mock_youtube_service = MagicMock()
    mock_youtube_service.extract_playlist_info = MagicMock(return_value=MagicMock())
    mock_youtube_service.fetch_transcripts = AsyncMock(return_value=MagicMock())
    
    mock_llm_service = MagicMock()
    mock_llm_service.prepare_context = MagicMock(return_value="Context")
    mock_llm_service.chat_completion = AsyncMock(return_value="Response")
    
    mock_chat_repository = MagicMock()
    mock_chat_repository.get_conversation = AsyncMock(return_value=ConversationModel(
        id="123", playlist_url="http://url", user_id="user", title="Title", summary="Summary"
    ))
    mock_chat_repository.get_messages = AsyncMock(return_value=[])
    mock_chat_repository.add_message = AsyncMock()

    # Instantiate service
    service = ChatService(mock_youtube_service, mock_llm_service, mock_chat_repository)

    # Test Case 1: use_transcripts = True
    print("Testing use_transcripts=True...")
    await service.process_message("123", "Hello", use_transcripts=True)
    
    # Verify fetch_transcripts was called
    if mock_youtube_service.fetch_transcripts.called:
        print("PASS: fetch_transcripts called when use_transcripts=True")
    else:
        print("FAIL: fetch_transcripts NOT called when use_transcripts=True")

    # Reset mocks
    mock_youtube_service.fetch_transcripts.reset_mock()

    # Test Case 2: use_transcripts = False
    print("\nTesting use_transcripts=False...")
    await service.process_message("123", "Hello", use_transcripts=False)
    
    # Verify fetch_transcripts was NOT called
    if not mock_youtube_service.fetch_transcripts.called:
        print("PASS: fetch_transcripts NOT called when use_transcripts=False")
    else:
        print("FAIL: fetch_transcripts called when use_transcripts=False")

if __name__ == "__main__":
    asyncio.run(test_chat_logic())
