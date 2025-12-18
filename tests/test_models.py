"""
Unit tests for Pydantic models.
"""
import pytest
from app.models import TranscriptSegment, Video, Playlist


def test_video_full_text():
    """Test that Video.full_text concatenates transcript segments."""
    segments = [
        TranscriptSegment(text="Hello", start=0.0, duration=1.0),
        TranscriptSegment(text="World", start=1.0, duration=1.0),
    ]
    video = Video(id="123", transcript=segments)
    assert video.full_text == "Hello World"


def test_video_full_text_empty_transcript():
    """Test that Video.full_text falls back to description when no transcript."""
    video = Video(id="123", description="A video description")
    assert video.full_text == "A video description"


def test_video_full_text_no_content():
    """Test that Video.full_text returns empty string when no content."""
    video = Video(id="123")
    assert video.full_text == ""


def test_playlist_structure():
    """Test basic Playlist structure."""
    video = Video(id="123", title="Test Video")
    playlist = Playlist(url="https://youtube.com/playlist?list=123", videos=[video])
    assert playlist.videos[0].id == "123"
    assert playlist.videos[0].title == "Test Video"


def test_transcript_segment_immutable():
    """Test that TranscriptSegment is immutable (frozen)."""
    segment = TranscriptSegment(text="Hello", start=0.0, duration=1.0)
    with pytest.raises(Exception):  # ValidationError for frozen model
        segment.text = "Changed"


def test_playlist_empty():
    """Test Playlist with no videos."""
    playlist = Playlist(url="https://youtube.com/playlist?list=123")
    assert playlist.videos == []
    assert playlist.title is None