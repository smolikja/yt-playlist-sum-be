import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
import uuid
from datetime import datetime

from app.main import app
from app.api.dependencies import get_chat_service
from app.api.auth import current_active_user
from app.models.sql import User, ConversationModel

client = TestClient(app)

# Mock User
mock_user_id = uuid.uuid4()
mock_user = User(id=mock_user_id, email="test@example.com")

async def override_current_active_user():
    return mock_user

# Mock ChatService
mock_chat_service = AsyncMock()

def override_get_chat_service():
    return mock_chat_service

app.dependency_overrides[current_active_user] = override_current_active_user
app.dependency_overrides[get_chat_service] = override_get_chat_service

def test_delete_conversation():
    conversation_id = str(uuid.uuid4())
    mock_chat_service.delete_conversation.return_value = None

    response = client.delete(f"/api/v1/conversations/{conversation_id}")
    
    assert response.status_code == 204
    mock_chat_service.delete_conversation.assert_called_with(conversation_id, mock_user_id)

def test_get_conversations():
    # Setup mock return
    c1 = ConversationModel(
        id=str(uuid.uuid4()),
        title="Title 1",
        summary="Summary 1",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    mock_chat_service.get_history.return_value = [c1]

    response = client.get("/api/v1/conversations")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == c1.id
    assert "updated_at" in data[0]
    
    # Check that service was called with correct user_id
    # Note: get_history is called with (user_id, limit, offset)
    mock_chat_service.get_history.assert_called()
    args, _ = mock_chat_service.get_history.call_args
    assert args[0] == mock_user_id
