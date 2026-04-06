from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    message: str


class AskRequest(BaseModel):
    query: str
    subject: Optional[str] = None  # Optional subject filter


class QuestionDocument(BaseModel):
    subject: str
    question: str
    embedding: list
