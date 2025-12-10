import google.generativeai as genai
from app.models import Playlist, SummaryResult, MessageRole
from app.models.api import SummaryContent
from loguru import logger

class LLMService:
    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name
        # Initialize the library with the API Key
        genai.configure(api_key=self.api_key)

    def prepare_context(self, playlist: Playlist) -> str:
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

    async def generate_summary(self, playlist: Playlist) -> SummaryContent:
        """
        Generates a summary for the provided playlist using the Gemini 2.0 Flash model.
        """
        model = genai.GenerativeModel(self.model_name)

        system_instruction = (
            "You are an expert content summarizer. You will receive transcripts from a Youtube Playlist. "
            "Your goal is to provide a comprehensive summary of the entire playlist, highlighting the main topics, "
            "key takeaways, and the logical flow between videos. Output in Markdown."
        )
        
        logger.info("Processing transcript context...")
        context_text = self.prepare_context(playlist)
        logger.info(f"Context size: {len(context_text)} characters")

        prompt = f"{system_instruction}\n\n{context_text}"

        # Generate the content asynchronously
        logger.info("Sending prompt to Gemini...")
        response = await model.generate_content_async(prompt)
        logger.info("Received response from Gemini.")
        
        if response.usage_metadata:
            logger.info(f"Token usage: {response.usage_metadata}")
        
        return SummaryContent(
            playlist_title=playlist.title,
            video_count=len(playlist.videos),
            summary_markdown=response.text
        )

    async def chat_completion(self, context_text: str, history: list, user_question: str) -> str:
        """
        Generates a response to a user question based on the playlist context and chat history.
        """
        model = genai.GenerativeModel(self.model_name)
        
        system_instruction = (
            "You are a helpful assistant discussing a YouTube Playlist. "
            "Answer the user's questions based strictly on the provided transcripts. "
            "If the answer is not in the context, say so."
        )

        if not context_text:
            system_instruction = (
                "You are a helpful assistant discussing a YouTube Playlist. "
                "Answer based on the conversation history and the summary provided above. "
                "Do not hallucinate details not present in the history."
            )

        history_text = ""
        for msg in history:
            role_label = "User" if msg.role == MessageRole.USER else "Model"
            history_text += f"{role_label}: {msg.content}\n"

        prompt = (
            f"{system_instruction}\n\n"
            f"--- CONTEXT (TRANSCRIPTS) ---\n{context_text if context_text else 'No transcripts provided.'}\n-----------------------------\n\n"
            f"--- CHAT HISTORY ---\n{history_text}\n"
            f"User: {user_question}\n"
            f"Model:"
        )

        logger.info("Sending chat completion prompt to Gemini...")
        response = await model.generate_content_async(prompt)
        logger.info("Received chat response from Gemini.")

        if response.usage_metadata:
            logger.info(f"Chat token usage: {response.usage_metadata}")

        return response.text