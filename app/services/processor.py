from typing import List, Dict, Any

def prepare_transcript_context(transcripts_data: List[Dict[str, Any]]) -> str:
    """
    Formats a list of transcript data dictionaries into a single string optimized 
    for an LLM context window. Removes timestamps and concatenates text.
    
    Args:
        transcripts_data: List of dicts, each containing 'video_id' and 'transcript'
                          (which is a list of dicts with 'text', 'start', 'duration').

    Returns:
        A formatted string containing the concatenated text of all videos.
    """
    formatted_parts = []
    
    for index, item in enumerate(transcripts_data, start=1):
        video_id = item.get("video_id", "Unknown")
        raw_transcript = item.get("transcript", [])
        
        # Concatenate text parts, ignoring 'start' and 'duration'
        # Filter out empty or None text entries just in case
        full_text = " ".join(
            entry.text.strip() 
            for entry in raw_transcript 
            if hasattr(entry, 'text') and entry.text
        )
        
        # Clean up extra whitespace that might result from joining
        full_text = " ".join(full_text.split())
        
        video_section = (
            f"--- VIDEO {index} ---\n"
            f"Video ID: {video_id}\n"
            f"Content: {full_text}\n"
            f"---------------------"
        )
        formatted_parts.append(video_section)
        
    return "\n\n".join(formatted_parts)
