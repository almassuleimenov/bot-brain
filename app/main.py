from contextlib import asynccontextmanager
import os
from fastapi import Depends, FastAPI, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.services.whatsapp import send_whatsapp_message
from app.services.telegram import send_telegram_message 
from app.models.schemas import GenerateAnswerRequest, GenerateAnswerResponse
from app.services.ai import generate_reply_with_ai
from app.services.sanity import fetch_projects_from_sanity
from app.core.database import engine, Base, get_db
from app.models.client import Client
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

# ==========================================
# 🟩 БЛОК 1: ВАТСАП (И ПЕРЕХВАТЧИК БОССА)
# ==========================================
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
            return GenerateAnswerResponse(reply="Извините, я не смог разобрать ваше голосовое сообщение. Можете написать текстом?")

    if not final_user_text:
        return GenerateAnswerResponse(reply="Пожалуйста, отправьте текст или голосовое сообщение.")
        
    architect_phone = os.getenv("ARCHITECT_PHONE")

    # === ПЕРЕХВАТЧИК КОМАНД ОТ АРХИТЕКТОРА ===
    if architect_phone and request.chat_id == architect_phone:
        text_lower = final_user_text.strip().lower()

        if text_lower.startswith("1 ") or text_lower.startswith("2 "):
            parts = final_user_text.split(" ", 2)
            client_phone = parts[1].strip()
            
            # Ищем номер как есть (без @c.us). Если найдем - это Телеграм.
            check_res = await db.execute(select(Client).where(Client.chat_id == client_phone))
            tg_client = check_res.scalars().first()
            
            if tg_client:
                client_chat_id = client_phone
                is_telegram = True
            else:
                client_chat_id = f"{client_phone}@c.us"
                is_telegram = False

            # --- КОМАНДА 1 (ПОДТВЕРДИТЬ) ---
            if text_lower.startswith("1 "):
                happy_msg = (
                    "🎉 Отличные новости! Главный архитектор подтвердил наше время. "
                    "Будем рады видеть вас в нашем офисе!\n\n"
                    "📍 Наш адрес: г. Алматы, мкр. Самал-3, 15 к1\n"
                    "🗺️ Построить маршрут в 2GIS: https://2gis.kz/almaty/geo/9430047375085700/76.956587,43.227737\n\n"
                    "Если планы изменятся или будут вопросы — пишите, я всегда на связи. До встречи! 🌸"
                )
                if is_telegram:
                    await send_telegram_message(client_chat_id, happy_msg)
                else:
                    await send_whatsapp_message(client_chat_id, happy_msg)

                # Запись в память
                result = await db.execute(select(Client).where(Client.chat_id == client_chat_id))
                client_in_db = result.scalars().first()
                if client_in_db:
                    client_in_db.context += f"\n[СИСТЕМНОЕ СООБЩЕНИЕ]: Главный архитектор ПОДТВЕРДИЛ встречу."
                    await db.commit()
                return GenerateAnswerResponse(reply=f"✅ Подтверждение успешно отправлено клиенту {client_phone}!")

            # --- КОМАНДА 2 (ПЕРЕНОС) ---
            elif text_lower.startswith("2 ") and len(parts) >= 3:
                new_time_text = parts[2].strip()
                reschedule_msg = (
                    "🌸 Я переговорила с главным архитектором. К сожалению, прошлое время у него уже занято.\n\n"
                    f"Но он выделил для вас **специальное личное окно: {new_time_text}**, чтобы вы могли детально обсудить проект без спешки.\n\n"
                    "Подскажите, вам будет удобно подойти в это время?"
                )
                if is_telegram:
                    await send_telegram_message(client_chat_id, reschedule_msg)
                else:
                    await send_whatsapp_message(client_chat_id, reschedule_msg)

                # Запись в память
                result = await db.execute(select(Client).where(Client.chat_id == client_chat_id))
                client_in_db = result.scalars().first()
                if client_in_db:
                    client_in_db.context += f"\n[СИСТЕМНОЕ СООБЩЕНИЕ]: Архитектор ПРЕДЛОЖИЛ ПЕРЕНОС времени на: {new_time_text}."
                    await db.commit()
                return GenerateAnswerResponse(reply=f"🕒 Предложение о 'личном окне' отправлено клиенту {client_phone}!")

    # --- СТАНДАРТНАЯ ЛОГИКА ВАТСАПА ---
    result = await db.execute(select(Client).where(Client.chat_id == request.chat_id))
    client = result.scalars().first()

    if not client:
        client = Client(chat_id=request.chat_id)
        db.add(client)
        await db.commit()
        await db.refresh(client)
        print(f"🆕 В базу добавлен НОВЫЙ клиент (WhatsApp): {request.chat_id}")

    projects = await fetch_projects_from_sanity()
    ai_reply = await generate_reply_with_ai(final_user_text, projects, client.context)

    new_context = f"{client.context}\nКлиент: {final_user_text}\nТомирис: {ai_reply}"
    if len(new_context) > 2000:
        new_context = "..." + new_context[-2000:]
    client.context = new_context
    await db.commit()

    magic_phrase = "Я передала всю информацию главному архитектору"
    if magic_phrase in ai_reply:
        from app.services.ai import generate_client_summary
        clean_phone = request.chat_id.replace("@c.us", "")
        summary = await generate_client_summary(new_context, clean_phone)
        architect_phone = os.getenv("ARCHITECT_PHONE")
        if architect_phone:
            await send_whatsapp_message(architect_phone, f"🟢 [ИЗ WHATSAPP]\n{summary}")

    return GenerateAnswerResponse(reply=ai_reply)

# ==========================================
# 🟦 БЛОК 2: ТЕЛЕГРАМ (НОВЫЙ ЭНДПОИНТ)
# ==========================================
@app.post("/telegram-webhook")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()

    if "message" not in data or "text" not in data["message"]:
        return {"status": "ok"} 

    chat_id = str(data["message"]["chat"]["id"])
    user_text = data["message"]["text"]

    # 1. Ищем клиента в базе (ID телеграма)
    result = await db.execute(select(Client).where(Client.chat_id == chat_id))
    client = result.scalars().first()

    if not client:
        client = Client(chat_id=chat_id)
        db.add(client)
        await db.commit()
        await db.refresh(client)
        print(f"🆕 В базу добавлен НОВЫЙ клиент (Telegram): {chat_id}")

    # 2. Генерируем ответ Томирис
    projects = await fetch_projects_from_sanity()
    ai_reply = await generate_reply_with_ai(user_text, projects, client.context)

    # 3. Сохраняем память
    new_context = f"{client.context}\nКлиент: {user_text}\nТомирис: {ai_reply}"
    if len(new_context) > 2000:
        new_context = "..." + new_context[-2000:]
    client.context = new_context
    await db.commit()

    # 4. Проверка на БИНГО!
    magic_phrase = "Я передала всю информацию главному архитектору"
    if magic_phrase in ai_reply:
        from app.services.ai import generate_client_summary
        summary = await generate_client_summary(new_context, chat_id)
        architect_phone = os.getenv("ARCHITECT_PHONE")
        
        if architect_phone:
            # Отправляем анкету боссу в Ватсап с пометкой Телеграма
            await send_whatsapp_message(architect_phone, f"🔵 [ИЗ TELEGRAM]\n{summary}")

    # 5. Отправляем ответ клиенту в Телеграм
    await send_telegram_message(chat_id, ai_reply)

    return {"status": "ok"}