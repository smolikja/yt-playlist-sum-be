from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    MODEL = "model"
