from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.sql import ConversationModel, MessageModel

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

    async def get_conversation(self, conversation_id: str) -> Optional[ConversationModel]:
        """
        Retrieves a specific conversation by ID.
        """
        query = select(ConversationModel).where(ConversationModel.id == conversation_id)
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

    async def get_user_conversations(self, user_id: str, limit: int = 20, offset: int = 0) -> List[ConversationModel]:
        """
        Retrieves a list of conversations for a specific user, ordered by creation date.

        Args:
            user_id (str): The user ID to filter by.
            limit (int): Maximum number of records to return.
            offset (int): Number of records to skip.

        Returns:
            List[ConversationModel]: A list of ConversationModel objects.
        """
        query = (
            select(ConversationModel)
            .where(ConversationModel.user_id == user_id)
            .order_by(ConversationModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
