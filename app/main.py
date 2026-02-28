from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from app.models.schemas import GenerateAnswerRequest, GenerateAnswerResponse
from app.services.ai import generate_reply_with_ai
from app.services.sanity import fetch_projects_from_sanity
from app.core.database import engine, Base, get_db
from app.models.client import Client
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.services.audio import transcribe_audio_from_url


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Запуск Мозга: подключаемся к PostgreSQL...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ База данных готова!")
    yield
    await engine.dispose()


app = FastAPI(title="Bot Brain (AI Microservice)", lifespan=lifespan)


@app.post("/generate-answer", response_model=GenerateAnswerResponse)
async def generate_answer(
    request: GenerateAnswerRequest, db: AsyncSession = Depends(get_db)
):
    final_user_text = request.user_text

    if request.voice_url:
        print(f"🎤 Получена ссылка на голосовое: {request.voice_url[:30]}...")

        transcribed_text = await transcribe_audio_from_url(request.voice_url)

        if transcribed_text:
            final_user_text = transcribed_text
        else:
            return GenerateAnswerResponse(
                reply="Извините, я не смог разобрать ваше голосовое сообщение. Можете написать текстом?"
            )

    if not final_user_text:
        return GenerateAnswerResponse(
            reply="Пожалуйста, отправьте текст или голосовое сообщение."
        )

    result = await db.execute(select(Client).where(Client.chat_id == request.chat_id))
    client = result.scalars().first()

    if not client:
        client = Client(chat_id=request.chat_id)
        db.add(client)
        await db.commit()
        await db.refresh(client)
        print(f"🆕 В базу добавлен НОВЫЙ клиент: {request.chat_id}")
    else:
        print(
            f"👤 Клиент вернулся: {request.chat_id} | VIP: {client.is_vip} | Память: {client.context}"
        )

    print(f"📩 Получен запрос: ChatID={request.chat_id}, Text='{request.user_text}'")

    projects = await fetch_projects_from_sanity()

    print("ИИ думает.....")

    ai_reply = await generate_reply_with_ai(final_user_text, projects, client.context)

    print("Ответ ИИ готов для дурова!!")

    new_context = f"{client.context}\nКлиент: {final_user_text}\nТомирис: {ai_reply}"
    
    if len(new_context) > 2000:
        new_context = "..." + new_context[-2000:] 

    client.context = new_context
    await db.commit()

    return GenerateAnswerResponse(reply=ai_reply)
