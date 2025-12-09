import sys
import os

# Add project root to python path
sys.path.insert(0, os.getcwd())

from app.models import TranscriptSegment, Video, Playlist

def test_video_full_text():
    segments = [
        TranscriptSegment(text="Hello", start=0.0, duration=1.0),
        TranscriptSegment(text="World", start=1.0, duration=1.0)
    ]
    video = Video(id="123", transcript=segments)
    assert video.full_text == "Hello World"
    print("test_video_full_text passed")

def test_playlist_structure():
    video = Video(id="123", title="Test Video")
    playlist = Playlist(url="https://youtube.com/playlist?list=123", videos=[video])
    assert playlist.videos[0].id == "123"
    assert playlist.videos[0].title == "Test Video"
    print("test_playlist_structure passed")

if __name__ == "__main__":
    test_video_full_text()
    test_playlist_structure()