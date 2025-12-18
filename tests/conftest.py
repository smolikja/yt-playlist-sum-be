"""
Shared pytest fixtures and configuration.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
import uuid
from datetime import datetime

from app.main import app
from app.api.dependencies import get_chat_service
from app.api.auth import current_active_user, current_optional_user
from app.models.sql import User


@pytest.fixture
def mock_user_id():
    """Generate a mock user UUID."""
    return uuid.uuid4()


@pytest.fixture
def mock_user(mock_user_id):
    """Create a mock User object."""
    user = MagicMock(spec=User)
    user.id = mock_user_id
    user.email = "test@example.com"
    user.is_active = True
    user.is_verified = True
    user.is_superuser = False
    return user


@pytest.fixture
def mock_chat_service():
    """Create a mock ChatService."""
    return AsyncMock()


@pytest.fixture
def override_dependencies(mock_user, mock_chat_service):
    """Override FastAPI dependencies for testing."""
    async def override_current_active_user():
        return mock_user
    
    async def override_current_optional_user():
        return mock_user
    
    def override_get_chat_service():
        return mock_chat_service
    
    app.dependency_overrides[current_active_user] = override_current_active_user
    app.dependency_overrides[current_optional_user] = override_current_optional_user
    app.dependency_overrides[get_chat_service] = override_get_chat_service
    
    yield
    
    # Clean up
    app.dependency_overrides.clear()
