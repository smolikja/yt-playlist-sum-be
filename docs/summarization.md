# Summarization Service

The **Summarization Service** (`app/services/summarization.py`) is a core component of the backend responsible for transforming raw video transcripts into coherent, structured summaries. 

It implements an **Adaptive Strategy** that dynamically selects the most efficient processing method based on the volume of text (transcript length) and the capabilities of the underlying LLM (context window).

## Adaptive Strategy Overview

The service analyzes the input playlist and selects one of three execution paths to optimize for **quality**, **speed**, and **cost**.

```mermaid
flowchart TD
    Start([Playlist Request]) --> Count{Video Count}
    
    Count -- "Single Video" --> Single[Strategy: Single Video]
    Count -- "Multiple Videos" --> CalcSize[Calculate Total Characters]
    
    CalcSize --> CheckLimit{Fits in Context?}
    
    CheckLimit -- "Yes (< 3M chars)" --> Direct[Strategy: Direct Batch]
    CheckLimit -- "No (> 3M chars)" --> MapReduce[Strategy: Chunked Map-Reduce]
    
    Single --> Prompt1[Detailed Prompt]
    Direct --> Prompt2[Global Context Prompt]
    
    subgraph CMR [Chunked Map-Reduce]
        Chunking[Group Videos into Batches]
        Map[Map Phase: Summarize Batches]
        Reduce[Reduce Phase: Combine Summaries]
        Chunking --> Map --> Reduce
    end
    
    MapReduce --> CMR
    
    Prompt1 --> Output([Final Summary])
    Prompt2 --> Output
    Reduce --> Output
```

## Strategies

### 1. Single Video Strategy
**Trigger:** Playlist contains exactly one video.

*   **Logic:** The system bypasses all batching logic and treats the content as a standalone entity.
*   **Prompting:** Uses a highly detailed prompt specifically designed to extract deep insights, timestamps (implicitly), and key takeaways from a single source.
*   **Truncation:** Safety limit of ~2M characters (approx. 500k tokens).

### 2. Direct Batch Strategy (Preferred)
**Trigger:** Multiple videos, total length < `MAX_BATCH_CONTEXT_CHARS` (approx. 750k tokens / 3M chars).

This is the **most efficient method** for modern large-context models (like Gemini 1.5 Pro).

*   **Logic (Context Stuffing):** Concatenates transcripts from *all* videos into a single, massive context window.
*   **Benefits:**
    *   **Cross-Pollination:** The LLM "sees" the entire series at once, allowing it to identify connections, recurring themes, and contradictions between different videos.
    *   **Efficiency:** Only **1 API Request** is made. This reduces network latency and eliminates the repetitive "preamble" cost of multiple system prompts.
*   **Format:** Transcripts are separated by clear headers (`### Video: [Title]`).

### 3. Chunked Map-Reduce Strategy (Fallback)
**Trigger:** Total length > `MAX_BATCH_CONTEXT_CHARS`.

Used for massive datasets (e.g., playlists with hundreds of hours of content) that physically cannot fit into a single context window.

*   **Logic:**
    1.  **Chunking:** Videos are grouped into "batches" (chunks). A chunk is filled until it reaches `MAP_CHUNK_SIZE_CHARS` (~2M chars).
    2.  **Map Phase (Batch Summarization):** Each chunk is sent to the LLM as a "segment" of the playlist.
        *   *Optimization:* Instead of summarizing 1 video per request (standard Map-Reduce), we might summarize 10 short videos in 1 request. This significantly reduces the total number of API calls.
    3.  **Reduce Phase:** The summaries of these chunks are collected and sent to the LLM to generate the final global summary.

## Configuration & Limits

The logic is controlled by constants in the `SummarizationConfig` class within `app/core/constants.py`:

| Constant | Value (Chars) | Approx. Tokens | Description |
| :--- | :--- | :--- | :--- |
| `SummarizationConfig.MAX_SINGLE_VIDEO_CHARS` | 2,000,000 | ~500k | Hard limit for a single video transcript to prevent crashes. |
| `SummarizationConfig.MAX_BATCH_CONTEXT_CHARS` | 3,000,000 | ~750k | Threshold to switch from Direct Batch to Map-Reduce. Leaves buffer for output. |
| `SummarizationConfig.MAP_CHUNK_SIZE_CHARS` | 2,000,000 | ~500k | Target size for a single "chunk" in the Map phase. |

*Note: Token estimates assume ~4 characters per token.*

## Prompt Engineering

All system prompts are centralized in `app/core/prompts.py` within the `SummarizationPrompts` class. This separation allows for easier versioning and iteration without modifying the core logic.

The service uses distinct system prompts for each context:

*   **Single Video (`SINGLE_VIDEO`):** Comprehensive analysis of a single transcript, extracting key topics, insights, and takeaways. Enforces English output.
*   **Direct Batch (`DIRECT_BATCH`):** Analyzes the entire playlist at once. Specifically instructed to find "Cross-Video Connections" and "Key Themes" across the collection.
*   **Map Phase (`MAP_PHASE`):** Used for chunks of videos in the Map-Reduce strategy. Focuses on consolidating key points from a segment of the playlist.
*   **Reduce Phase (`REDUCE_PHASE`):** Synthesizes multiple summaries (from the Map phase) into a cohesive global summary, identifying overarching themes.

## Future Improvements

*   **Parallel Execution:** The Map phase currently runs sequentially (or semi-sequentially via loop) to respect strict Rate Limits. With higher tier API quotas, this can be parallelized using `asyncio.gather`.
*   **Smart Chunking:** Currently chunks are based on character count. Future versions could chunk based on semantic similarity or topic clustering.
