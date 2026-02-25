from pydantic import BaseModel
from typing import Optional


class GenerateAnswerRequest(BaseModel):
    chat_id: str
    user_text: str = ""
    voice_url: Optional[str] = None


class GenerateAnswerResponse(BaseModel):
    reply: str
