from fastapi import FastAPI
from app.models.schemas import GenerateAnswerRequest, GenerateAnswerResponse
from app.services.ai import generate_reply_with_ai
from app.services.sanity import fetch_projects_from_sanity

app = FastAPI(title="Bot Brain (AI Microservice)")


@app.post("/generate-answer", response_model=GenerateAnswerResponse)
async def generate_answer(request: GenerateAnswerRequest):
    print(f"📩 Получен запрос: ChatID={request.chat_id}, Text='{request.user_text}'")

    projects = await fetch_projects_from_sanity()

    print("ИИ думает.....")

    ai_reply = await generate_reply_with_ai(request.user_text, projects)

    print("Ответ ИИ готов для дурова!!")

    return GenerateAnswerResponse(reply=ai_reply)
