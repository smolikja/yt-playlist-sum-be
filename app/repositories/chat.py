from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.sql import ConversationModel, MessageModel
import uuid

class ChatRepository:
    """
    Repository layer for managing ConversationModel data.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_conversation(self, conversation: ConversationModel) -> ConversationModel:
        """
        Saves a new conversation to the database.

        Args:
            conversation (ConversationModel): The conversation object to save.

        Returns:
            ConversationModel: The saved conversation object with updated state.
        """
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        return conversation

    async def update_conversation(self, conversation: ConversationModel) -> ConversationModel:
        """
        Updates an existing conversation in the database.
        """
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        return conversation

    async def get_conversation(self, conversation_id: str) -> Optional[ConversationModel]:
        """
        Retrieves a specific conversation by ID.
        """
        query = select(ConversationModel).where(ConversationModel.id == conversation_id)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_conversation_with_messages(self, conversation_id: str, user_id: uuid.UUID) -> Optional[ConversationModel]:
        """
        Retrieves a conversation by ID and user_id, including all messages eagerly loaded.
        """
        query = (
            select(ConversationModel)
            .where(
                ConversationModel.id == conversation_id,
                ConversationModel.user_id == user_id
            )
            .options(selectinload(ConversationModel.messages))
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def add_message(self, message: MessageModel) -> MessageModel:
        """
        Adds a message to a conversation.
        """
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def get_messages(self, conversation_id: str) -> List[MessageModel]:
        """
        Retrieves all messages for a conversation, ordered by creation time.
        """
        query = (
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            .order_by(MessageModel.created_at.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_user_conversations(self, user_id: uuid.UUID, limit: int = 20, offset: int = 0) -> List[ConversationModel]:
        """
        Retrieves a list of conversations for a specific user, ordered by last update.

        Args:
            user_id (uuid.UUID): The user ID to filter by.
            limit (int): Maximum number of records to return.
            offset (int): Number of records to skip.

        Returns:
            List[ConversationModel]: A list of ConversationModel objects.
        """
        query = (
            select(ConversationModel)
            .where(ConversationModel.user_id == user_id)
            .order_by(ConversationModel.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def delete_conversation(self, conversation: ConversationModel) -> None:
        """
        Deletes a conversation from the database.
        """
        await self.db.delete(conversation)
        await self.db.commit()
