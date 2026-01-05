# API Reference

Base URL: `http://localhost:8000/api/v1`

## Authentication

All endpoints except `/summarize` (public mode) require JWT authentication.

```http
Authorization: Bearer <jwt_token>
```

See [Authentication](./authentication.md) for details on obtaining tokens.

---

## API Limits

| Limit | Value | Description |
|-------|-------|-------------|
| `PaginationConfig.MAX_LIMIT` | 100 | Max conversations per request |
| `MessageConfig.MAX_LENGTH` | 10,000 | Max characters per message |
| `RateLimitConfig.SUMMARIZE` | 10/minute | Rate limit for `/summarize` |
| `RateLimitConfig.CHAT` | 30/minute | Rate limit for `/chat` |
| `JOB_MAX_CONCURRENT_PER_USER` | 3 | Max active jobs per user |
| `PUBLIC_SUMMARIZATION_TIMEOUT` | 100s | Timeout for public users |

Constants are defined in `app/core/constants.py` and `app/core/config.py`.

---

## Endpoints

### POST /summarize

Summarize a YouTube playlist or single video. **Dual-mode operation:**

- **Public users**: Synchronous with timeout (default: 100s)
- **Authenticated users**: Creates async background job

**Rate Limit:** 10 requests/minute

**Request:**
```json
{
  "url": "https://youtube.com/playlist?list=PLxxx"
}
```

**Response (Public - Sync):**
```json
{
  "mode": "sync",
  "summary": {
    "conversation_id": "uuid",
    "playlist_title": "My Playlist",
    "video_count": 14,
    "summary_markdown": "# Summary\n\n...\n\n## ⚠️ Vyloučená videa\n...",
    "exclusion_report": {
      "total_videos": 14,
      "included_count": 11,
      "excluded_count": 3,
      "excluded_videos": [
        {
          "id": "abc123",
          "title": "Video Title",
          "reason": "Video je soukromé",
          "status": "private"
        }
      ]
    }
  }
}
```

**Response (Authenticated - Async):**
```json
{
  "mode": "async",
  "job": {
    "id": "uuid",
    "status": "pending",
    "playlist_url": "https://...",
    "created_at": "2026-01-05T10:00:00Z"
  }
}
```

**Error (Public Timeout - 408):**
```json
{
  "type": "https://problems.example.com/public-timeout",
  "title": "Request Timeout",
  "status": 408,
  "detail": "Playlist je příliš komplexní pro nepřihlášené uživatele..."
}
```

---

## Job Endpoints

### GET /jobs

List all background jobs for the authenticated user.

**Authentication:** Required

**Response:**
```json
[
  {
    "id": "uuid",
    "status": "completed",
    "playlist_url": "https://...",
    "error_message": null,
    "created_at": "2026-01-05T10:00:00Z",
    "started_at": "2026-01-05T10:00:01Z",
    "completed_at": "2026-01-05T10:02:30Z"
  }
]
```

**Job Status Values:**
| Status | Description |
|--------|-------------|
| `pending` | Waiting to be processed |
| `running` | Currently being processed |
| `completed` | Success - ready to claim |
| `failed` | Error occurred - can retry |

---

### GET /jobs/{id}

Get status of a specific job (polling endpoint).

**Authentication:** Required

**Response:** Same as individual job object above.

---

### POST /jobs/{id}/claim

Claim a completed job, transforming it into a conversation.

**Authentication:** Required

**Response:**
```json
{
  "conversation": {
    "id": "uuid",
    "title": "Playlist Title",
    "playlist_url": "https://...",
    "summary": "Full markdown summary",
    "created_at": "2026-01-05T10:00:00Z",
    "updated_at": "2026-01-05T10:02:30Z",
    "messages": []
  }
}
```

> **Note:** The job is deleted after claiming. The conversation becomes visible in the user's conversation list.

---

### POST /jobs/{id}/retry

Retry a failed job by resetting it to pending status.

**Authentication:** Required

**Response:** Updated job object with `status: "pending"`.

---

### DELETE /jobs/{id}

Cancel and delete a pending or failed job.

**Authentication:** Required

**Response:** `204 No Content`

> **Note:** Running and completed jobs cannot be cancelled.

---

## Chat Endpoints

### POST /chat

Send a message within a conversation context.

**Rate Limit:** 30 requests/minute

**Authentication:** Required

**Request:**
```json
{
  "conversation_id": "uuid",
  "message": "What topics are covered?",
  "use_rag": true
}
```

| Parameter | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `conversation_id` | string | required | Conversation UUID |
| `message` | string | 1-10,000 chars | User message |
| `use_rag` | boolean | default: `true` | Enable RAG context retrieval |

**Response:**
```json
{
  "response": "The playlist covers..."
}
```

---

## Conversation Endpoints

### GET /conversations

List user's conversations.

**Authentication:** Required

**Query Parameters:**
| Parameter | Type | Constraints | Default | Description |
|-----------|------|-------------|---------|-------------|
| `limit` | int | 1-100 | 20 | Max results |
| `offset` | int | >= 0 | 0 | Pagination offset |

**Response:**
```json
[
  {
    "id": "uuid",
    "title": "Playlist Title",
    "summary_snippet": "First 200 chars...",
    "created_at": "2025-12-23T12:00:00Z",
    "updated_at": "2025-12-23T12:30:00Z"
  }
]
```

---

### GET /conversations/{id}

Get full conversation details including messages.

**Authentication:** Required

**Response:**
```json
{
  "id": "uuid",
  "title": "Playlist Title",
  "playlist_url": "https://youtube.com/...",
  "summary": "Full markdown summary",
  "created_at": "2025-12-23T12:00:00Z",
  "updated_at": "2025-12-23T12:30:00Z",
  "messages": [
    {
      "id": 1,
      "role": "user",
      "content": "What topics?",
      "created_at": "2025-12-23T12:30:00Z"
    },
    {
      "id": 2,
      "role": "model",
      "content": "The playlist covers...",
      "created_at": "2025-12-23T12:30:01Z"
    }
  ]
}
```

---

### POST /conversations/{id}/claim

Claim an anonymous conversation for the authenticated user.

**Authentication:** Required

**Response:**
```json
{
  "status": "success",
  "message": "Conversation claimed successfully."
}
```

---

### DELETE /conversations/{id}

Delete a conversation and all its messages.

**Authentication:** Required

**Response:** `204 No Content`

---

## Error Responses

All errors follow RFC 7807 format:

```json
{
  "type": "https://problems.example.com/not-found",
  "title": "Resource not found",
  "status": 404,
  "detail": "Conversation xyz not found"
}
```

| Status | Description |
|--------|-------------|
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Missing/invalid token |
| 403 | Forbidden - Access denied |
| 404 | Not Found - Resource doesn't exist |
| 408 | Request Timeout - Public user timeout exceeded |
| 422 | Validation Error - Schema mismatch |
| 429 | Rate Limited / Too Many Jobs |
| 500 | Internal Error - Server failure |
