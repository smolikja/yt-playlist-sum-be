import google.generativeai as genai
from app.core.config import settings
from app.models import Playlist, SummaryResult
from loguru import logger

# Initialize the library with the API Key
genai.configure(api_key=settings.GEMINI_API_KEY)

def _prepare_context(playlist: Playlist) -> str:
    """
    Formats the playlist transcripts into a single string optimized for the LLM.
    """
    formatted_parts = []
    
    # Filter videos that have transcripts
    valid_videos = [v for v in playlist.videos if v.transcript]
    
    for index, video in enumerate(valid_videos, start=1):
        # Use the helper property from the Video model
        full_text = video.full_text
        
        # Clean up extra whitespace
        full_text = " ".join(full_text.split())
        
        video_section = (
            f"--- VIDEO {index} ---\n"
            f"Video ID: {video.id}\n"
            f"Title: {video.title or 'Unknown'}\n"
            f"Content: {full_text}\n"
            f"---------------------"
        )
        formatted_parts.append(video_section)
        
    return "\n\n".join(formatted_parts)

async def generate_playlist_summary(playlist: Playlist) -> SummaryResult:
    """
    Generates a summary for the provided playlist using the Gemini 2.0 Flash model.
    """
    model = genai.GenerativeModel('gemini-2.5-flash')

    system_instruction = (
        "You are an expert content summarizer. You will receive transcripts from a Youtube Playlist. "
        "Your goal is to provide a comprehensive summary of the entire playlist, highlighting the main topics, "
        "key takeaways, and the logical flow between videos. Output in Markdown."
    )
    
    logger.info("Processing transcript context...")
    context_text = _prepare_context(playlist)
    logger.info(f"Context size: {len(context_text)} characters")

    prompt = f"{system_instruction}\n\n{context_text}"

    # Generate the content asynchronously
    logger.info("Sending prompt to Gemini...")
    response = await model.generate_content_async(prompt)
    logger.info("Received response from Gemini.")
    
    if response.usage_metadata:
        logger.info(f"Token usage: {response.usage_metadata}")
    
    return SummaryResult(
        playlist_title=playlist.title or "Summarized Playlist",
        video_count=len(playlist.videos),
        summary_markdown=response.text
    )
