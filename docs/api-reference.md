# API Reference

Base URL: `http://localhost:8000/api/v1`

## Authentication

All endpoints except `/summarize` require JWT authentication.

```http
Authorization: Bearer <jwt_token>
```

See [Authentication](./authentication.md) for details on obtaining tokens.

---

## Endpoints

### POST /summarize

Summarize a YouTube playlist and create a conversation.

**Rate Limit:** 10 requests/minute

**Request:**
```json
{
  "url": "https://youtube.com/playlist?list=PLxxx"
}
```

**Response:**
```json
{
  "conversation_id": "uuid",
  "playlist_title": "My Playlist",
  "video_count": 5,
  "summary_markdown": "# Summary\n\n..."
}
```

**Notes:**
- Anonymous users can summarize but cannot access conversation history
- Transcripts are cached for future requests
- RAG indexing happens automatically

---

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

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `conversation_id` | string | required | Conversation UUID |
| `message` | string | required | User message |
| `use_rag` | boolean | `true` | Enable RAG context retrieval |

**Response:**
```json
{
  "response": "The playlist covers..."
}
```

---

### GET /conversations

List user's conversations.

**Authentication:** Required

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 20 | Max results |
| `offset` | int | 0 | Pagination offset |

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

All errors follow this format:

```json
{
  "detail": "Error message"
}
```

| Status | Description |
|--------|-------------|
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Missing/invalid token |
| 403 | Forbidden - Access denied |
| 404 | Not Found - Resource doesn't exist |
| 422 | Validation Error - Schema mismatch |
| 429 | Rate Limited - Too many requests |
| 500 | Internal Error - Server failure |
