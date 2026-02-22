from pydantic import BaseModel


class GenerateAnswerRequest(BaseModel):
    chat_id: int
    user_text: str


class GenerateAnswerResponse(BaseModel):
    reply: str
