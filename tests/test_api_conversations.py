"""
Integration tests for conversation API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
import uuid
from datetime import datetime

from app.main import app
from app.models.sql import ConversationModel


client = TestClient(app)


def test_delete_conversation(override_dependencies, mock_chat_service, mock_user_id):
    """Test DELETE /api/v1/conversations/{id} endpoint."""
    conversation_id = str(uuid.uuid4())
    mock_chat_service.delete_conversation.return_value = None

    response = client.delete(f"/api/v1/conversations/{conversation_id}")

    assert response.status_code == 204
    mock_chat_service.delete_conversation.assert_called_with(
        conversation_id, mock_user_id
    )


def test_get_conversations(override_dependencies, mock_chat_service, mock_user_id):
    """Test GET /api/v1/conversations endpoint."""
    c1 = ConversationModel(
        id=str(uuid.uuid4()),
        title="Title 1",
        summary="Summary 1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    mock_chat_service.get_history.return_value = [c1]

    response = client.get("/api/v1/conversations")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == c1.id
    assert "updated_at" in data[0]

    # Check that service was called with correct user_id
    mock_chat_service.get_history.assert_called()
    args, _ = mock_chat_service.get_history.call_args
    assert args[0] == mock_user_id


def test_get_conversations_empty(override_dependencies, mock_chat_service):
    """Test GET /api/v1/conversations with no conversations."""
    mock_chat_service.get_history.return_value = []

    response = client.get("/api/v1/conversations")

    assert response.status_code == 200
    assert response.json() == []


def test_health_check():
    """Test GET /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "project" in data
