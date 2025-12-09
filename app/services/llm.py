import google.generativeai as genai
from app.core.config import settings
from loguru import logger

# Initialize the library with the API Key
genai.configure(api_key=settings.GEMINI_API_KEY)

async def generate_playlist_summary(context_text: str) -> str:
    """
    Generates a summary for the provided playlist transcript context using the Gemini 2.0 Flash model.
    """
    model = genai.GenerativeModel('gemini-2.0-flash')

    system_instruction = (
        "You are an expert content summarizer. You will receive transcripts from a Youtube Playlist. "
        "Your goal is to provide a comprehensive summary of the entire playlist, highlighting the main topics, "
        "key takeaways, and the logical flow between videos. Output in Markdown."
    )
    
    # Combine system instruction with the user context for the prompt
    # Note: gemini-1.5-flash supports system instructions via the `system_instruction` parameter in recent SDKs,
    # but constructing a single prompt is also a robust and standard way to ensure context.
    # We will use the standard generate_content method.
    
    prompt = f"{system_instruction}\n\n{context_text}"

    # Generate the content asynchronously
    logger.info("Sending prompt to Gemini...")
    response = await model.generate_content_async(prompt)
    logger.info("Received response from Gemini.")
    
    return response.text
