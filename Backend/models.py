from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str


class AskRequest(BaseModel):
    query: str


class QuestionDocument(BaseModel):
    subject: str
    question: str
    embedding: list
