import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.summarization import SummarizationService
from app.models import Playlist, Video, LLMRole
from app.core.providers.llm_provider import LLMProvider, LLMMessage
from app.core.prompts import SummarizationPrompts

# Mock response object from LLM
class MockLLMResponse:
    def __init__(self, content):
        self.content = content

@pytest.fixture
def mock_llm_provider():
    provider = AsyncMock(spec=LLMProvider)
    # Default behavior: return a simple string
    provider.generate_text.return_value = MockLLMResponse("Mocked Summary Content")
    return provider

@pytest.fixture
def summarization_service(mock_llm_provider):
    return SummarizationService(llm_provider=mock_llm_provider)

@pytest.fixture
def sample_video():
    return Video(
        id="v1",
        title="Video 1",
        url="http://youtube.com/v1",
        transcript=[{"text": "Hello world", "start": 0, "duration": 1}]
    )

@pytest.fixture
def sample_playlist(sample_video):
    return Playlist(
        id="pl1",
        title="My Playlist",
        url="http://youtube.com/playlist",
        videos=[sample_video]
    )

@pytest.mark.asyncio
async def test_summarize_empty_playlist(summarization_service):
    """Test handling of playlist with no transcripts."""
    playlist = Playlist(id="p1", title="Empty", url="http://x", videos=[])
    
    result = await summarization_service.summarize_playlist(playlist)
    assert "No transcripts available" in result
    summarization_service.llm_provider.generate_text.assert_not_called()

@pytest.mark.asyncio
async def test_summarize_single_video(summarization_service, sample_playlist):
    """Test Strategy 1: Single Video."""
    # Ensure setup has 1 video
    assert len(sample_playlist.videos) == 1
    
    await summarization_service.summarize_playlist(sample_playlist)
    
    # Verify LLM was called with SINGLE_VIDEO prompt
    args, kwargs = summarization_service.llm_provider.generate_text.call_args
    messages = kwargs['messages']
    
    assert len(messages) == 2
    assert messages[0].role == LLMRole.SYSTEM
    assert messages[0].content == SummarizationPrompts.SINGLE_VIDEO
    assert "Video 1" in messages[1].content

@pytest.mark.asyncio
async def test_summarize_direct_batch(summarization_service):
    """Test Strategy 2: Direct Batch (Context Stuffing)."""
    # Create 3 small videos
    videos = [
        Video(id=f"v{i}", title=f"Vid {i}", url="http://dummy.url", transcript=[{"text": "content", "start": 0, "duration": 1}])
        for i in range(3)
    ]
    playlist = Playlist(id="p1", title="Batch PL", url="http://dummy.url", videos=videos)
    
    # Default limits are high (millions), so this should definitely fit in Direct Batch
    await summarization_service.summarize_playlist(playlist)
    
    # Verify LLM called once with DIRECT_BATCH prompt
    assert summarization_service.llm_provider.generate_text.call_count == 1
    
    args, kwargs = summarization_service.llm_provider.generate_text.call_args
    messages = kwargs['messages']
    
    assert messages[0].content == SummarizationPrompts.DIRECT_BATCH
    # Check if all video titles are in the user prompt
    assert "Vid 0" in messages[1].content
    assert "Vid 1" in messages[1].content
    assert "Vid 2" in messages[1].content

@pytest.mark.asyncio
async def test_summarize_map_reduce_flow(summarization_service):
    """Test Strategy 3: Map-Reduce triggering and flow."""
    # Mock the constants to force Map-Reduce with small amount of data
    # MAX_BATCH_CONTEXT_CHARS = 50 -> Total 60 chars will trigger Map-Reduce
    # MAP_CHUNK_SIZE_CHARS = 40 -> Will force chunks
    
    with patch('app.services.summarization.settings') as mock_settings:
        mock_settings.SUMMARIZATION_BATCH_THRESHOLD = 50
        mock_settings.SUMMARIZATION_CHUNK_SIZE = 40
        mock_settings.SUMMARIZATION_MAX_INPUT_CHARS = 2_000_000
        
        # Create videos with defined length
        # "Ten chars." = 10 chars.
        videos = [
            Video(id="v1", title="V1", url="http://dummy.url", transcript=[{"text": "Ten chars." * 3, "start": 0, "duration": 1}]), # 30 chars
            Video(id="v2", title="V2", url="http://dummy.url", transcript=[{"text": "Ten chars." * 3, "start": 0, "duration": 1}]), # 30 chars
        ]
        # Total = 60 chars > MAX_BATCH_CONTEXT_CHARS (50) -> Should trigger Map-Reduce
        
        playlist = Playlist(id="p1", title="MR Playlist", url="http://dummy.url", videos=videos)
        
        await summarization_service.summarize_playlist(playlist)
        
        # Verify calls:
        # We expect multiple calls.
        # Call 1: Map Phase (Chunk 1 - V1) -> 30 chars < 40 chunk limit
        # Call 2: Map Phase (Chunk 2 - V2) -> V1+V2 = 60 > 40, so V2 goes to new chunk
        # Call 3: Reduce Phase
        
        assert summarization_service.llm_provider.generate_text.call_count >= 2
        
        calls = summarization_service.llm_provider.generate_text.call_args_list
        
        # Inspect the last call (Reduce Phase)
        last_call_args = calls[-1][1]['messages']
        assert last_call_args[0].content == SummarizationPrompts.REDUCE_PHASE

@pytest.mark.asyncio
async def test_chunking_logic(summarization_service):
    """Unit test for the _chunk_videos logic specifically."""
    
    # Setup: 4 videos, each 10 chars long
    videos = [
        Video(id=f"v{i}", title=f"V{i}", url="http://dummy.url", transcript=[{"text": "0123456789", "start": 0, "duration": 1}])
        for i in range(4)
    ]
    
    # Configure chunk size to 25 chars
    # Expected:
    # Chunk 1: V0 (10) + V1 (10) = 20. Adding V2 would be 30 > 25. So Chunk 1 = [V0, V1]
    # Chunk 2: V2 (10) + V3 (10) = 20. Chunk 2 = [V2, V3]
    
    with patch('app.services.summarization.settings') as mock_settings:
        mock_settings.SUMMARIZATION_CHUNK_SIZE = 25
        mock_settings.SUMMARIZATION_MAX_INPUT_CHARS = 2_000_000
        chunks = summarization_service._chunk_videos(videos)
        
        assert len(chunks) == 2
        assert len(chunks[0]) == 2 # V0, V1
        assert len(chunks[1]) == 2 # V2, V3
        assert chunks[0][0].id == "v0"
        assert chunks[0][1].id == "v1"
        assert chunks[1][0].id == "v2"

@pytest.mark.asyncio
async def test_truncation_logic(summarization_service):
    """Test that individual videos are truncated if they exceed hard limit."""
    
    # Mock hard limit to 10 chars
    with patch('app.services.summarization.settings') as mock_settings:
        mock_settings.SUMMARIZATION_MAX_INPUT_CHARS = 10
        mock_settings.SUMMARIZATION_BATCH_THRESHOLD = 3_000_000
        mock_settings.SUMMARIZATION_CHUNK_SIZE = 2_000_000
        video = Video(
            id="v1", 
            title="Long", 
            url="http://dummy.url", 
            transcript=[{"text": "This is a very long text exceeding ten chars", "start": 0, "duration": 1}]
        )
        
        # Test private method _summarize_single_video logic directly or via public method
        # Let's use public method but expect truncation in the prompt
        playlist = Playlist(id="p1", title="T", url="http://dummy.url", videos=[video])
        
        await summarization_service.summarize_playlist(playlist)
        
        args, kwargs = summarization_service.llm_provider.generate_text.call_args
        sent_transcript = kwargs['messages'][1].content
        
        # Expect "This is a ..." or similar based on slicing logic
        # Code: text[:limit] + "..."
        assert "This is a ..." in sent_transcript
        assert "exceeding" not in sent_transcript