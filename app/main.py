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
# 🟩 БЛОК 1: ВАТСАП 
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
            return GenerateAnswerResponse(reply="Извините, я не смогла разобрать ваше голосовое сообщение. Можете написать текстом? 🌸")

    if not final_user_text:
        return GenerateAnswerResponse(reply="Пожалуйста, отправьте текст или голосовое сообщение.")

    result = await db.execute(select(Client).where(Client.chat_id == request.chat_id))
    client = result.scalars().first()

    if not client:
        client = Client(chat_id=request.chat_id)
        db.add(client)
        await db.commit()
        await db.refresh(client)
        print(f"🆕 В базу добавлен НОВЫЙ клиент (WhatsApp): {request.chat_id}")

    projects = await fetch_projects_from_sanity()
    
    ai_response_data = await generate_reply_with_ai(final_user_text, projects, client.context)
    ai_reply_text = ai_response_data.get("reply", "Простите, техническая заминка.")
    ai_action = ai_response_data.get("action", "none")

    new_context = f"{client.context}\nКлиент: {final_user_text}\nТомирис: {ai_reply_text}"
    if len(new_context) > 2000:
        lines = new_context.split('\n')
        new_context = "...\n" + "\n".join(lines[-20:]) 
    client.context = new_context
    await db.commit()

    architect_tg_id = os.getenv("ARCHITECT_TG_ID")
    clean_phone = request.chat_id.replace("@c.us", "") if "@c.us" in str(request.chat_id) else request.chat_id

    if ai_action == "new_booking":
        from app.services.ai import generate_client_summary
        # Передаем жестко "WhatsApp" и чистый номер
        summary = await generate_client_summary(new_context, clean_phone, "WhatsApp")
        if architect_tg_id:
            await send_telegram_message(architect_tg_id, f"🟢 [НОВЫЙ ЛИД ИЗ WHATSAPP]\n{summary}")
            
    elif ai_action == "reschedule":
        if architect_tg_id:
            update_msg = (
                f"🟡 <b>ОБНОВЛЕНИЕ ПО КЛИЕНТУ: {clean_phone}</b>\n\n"
                f"<b>Ответ клиента:</b> <i>{final_user_text}</i>\n\n"
                f"👇 <i>Для подтверждения отправьте:</i>\n<code>1 {clean_phone}</code>"
            )
            await send_telegram_message(architect_tg_id, update_msg)

    return GenerateAnswerResponse(reply=ai_reply_text)

# ==========================================
# 🟦 БЛОК 2: ТЕЛЕГРАМ (И ПЕРЕХВАТЧИК БОССА)
# ==========================================
@app.post("/telegram-webhook")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()

    if "message" not in data:
        return {"status": "ok"} 

    message = data["message"]
    chat_id = str(message["chat"]["id"])
    user_text = ""

    if "text" in message:
        user_text = message["text"]
    elif "voice" in message:
        file_id = message["voice"]["file_id"]
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        import httpx
        async with httpx.AsyncClient() as client_http:
            try:
                file_info_resp = await client_http.get(f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}")
                file_info = file_info_resp.json()
                if file_info.get("ok"):
                    file_path = file_info["result"]["file_path"]
                    voice_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
                    user_text = await transcribe_audio_from_url(voice_url)
                    if not user_text:
                        await send_telegram_message(chat_id, "Извините, я не смогла разобрать голосовое сообщение.")
                        return {"status": "ok"}
            except Exception as e:
                print(f"❌ Ошибка загрузки войса из Телеги: {e}")
                return {"status": "ok"}

    if not user_text:
         return {"status": "ok"}

    # === ПЕРЕХВАТЧИК БОССА (ЩИТ ОТ БАГОВ) ===
    architect_tg_id = os.getenv("ARCHITECT_TG_ID")
    if architect_tg_id and chat_id == architect_tg_id:
        text_lower = user_text.strip().lower()

        if text_lower.startswith("1 ") or text_lower.startswith("2 "):
            parts = user_text.split(" ", 2)
            if len(parts) < 2:
                await send_telegram_message(chat_id, "❌ Ошибка формата. Укажите номер клиента.")
                return {"status": "ok"}
                
            client_phone = parts[1].strip()
            
            check_res = await db.execute(select(Client).where(Client.chat_id == client_phone))
            tg_client = check_res.scalars().first()
            
            if tg_client:
                client_chat_id = client_phone
                is_telegram = True
            else:
                client_chat_id = f"{client_phone}@c.us"
                is_telegram = False

            if text_lower.startswith("1 "):
                happy_msg = "🎉 Отличные новости! Главный архитектор подтвердил наше время. Будем рады видеть вас в нашем офисе! 🌸"
                if is_telegram:
                    await send_telegram_message(client_chat_id, happy_msg)
                else:
                    await send_whatsapp_message(client_chat_id, happy_msg)

                result = await db.execute(select(Client).where(Client.chat_id == client_chat_id))
                client_in_db = result.scalars().first()
                if client_in_db:
                    client_in_db.context += f"\n[СИСТЕМНОЕ СООБЩЕНИЕ]: Главный архитектор ПОДТВЕРДИЛ встречу."
                    await db.commit()
                
                await send_telegram_message(architect_tg_id, f"✅ Подтверждение успешно отправлено клиенту {client_phone}!")
                return {"status": "ok"}

            elif text_lower.startswith("2 ") and len(parts) >= 3:
                new_time_text = parts[2].strip()
                reschedule_msg = f"🌸 Я переговорила с главным архитектором. К сожалению, прошлое время занято. Но он выделил для вас специальное окно: {new_time_text}. Вам удобно?"
                if is_telegram:
                    await send_telegram_message(client_chat_id, reschedule_msg)
                else:
                    await send_whatsapp_message(client_chat_id, reschedule_msg)

                result = await db.execute(select(Client).where(Client.chat_id == client_chat_id))
                client_in_db = result.scalars().first()
                if client_in_db:
                    client_in_db.context += f"\n[СИСТЕМНОЕ СООБЩЕНИЕ]: Архитектор ПРЕДЛОЖИЛ ПЕРЕНОС времени на: {new_time_text}."
                    await db.commit()
                
                await send_telegram_message(architect_tg_id, f"🕒 Предложение о переносе отправлено клиенту {client_phone}!")
                return {"status": "ok"}
        else:
            # ЕСЛИ БОСС ПИШЕТ ПРОСТО ТЕКСТ - БЛОКИРУЕМ!
            await send_telegram_message(chat_id, "🤖 Босс, я понимаю только команды:\n✅ `1 [номер]` - подтвердить\n🕒 `2 [номер] [твое время]` - перенести")
            return {"status": "ok"}

    # --- ЛОГИКА ДЛЯ КЛИЕНТОВ В TELEGRAM ---
    result = await db.execute(select(Client).where(Client.chat_id == chat_id))
    client = result.scalars().first()

    if not client:
        client = Client(chat_id=chat_id)
        db.add(client)
        await db.commit()
        await db.refresh(client)

    projects = await fetch_projects_from_sanity()
    
    ai_response_data = await generate_reply_with_ai(user_text, projects, client.context)
    ai_reply_text = ai_response_data.get("reply", "Простите, техническая заминка.")
    ai_action = ai_response_data.get("action", "none")

    new_context = f"{client.context}\nКлиент: {user_text}\nТомирис: {ai_reply_text}"
    if len(new_context) > 2000:
        lines = new_context.split('\n')
        new_context = "...\n" + "\n".join(lines[-20:])
    client.context = new_context
    await db.commit()

    if ai_action == "new_booking":
        from app.services.ai import generate_client_summary
        summary = await generate_client_summary(new_context, chat_id, "Telegram")
        if architect_tg_id:
            await send_telegram_message(architect_tg_id, f"🔵 [НОВЫЙ ЛИД ИЗ TELEGRAM]\n{summary}")
            
    elif ai_action == "reschedule":
        if architect_tg_id:
            update_msg = (
                f"🟡 <b>ОБНОВЛЕНИЕ ПО КЛИЕНТУ: {chat_id}</b>\n\n"
                f"<b>Ответ клиента:</b> <i>{user_text}</i>\n\n"
                f"👇 <i>Для подтверждения отправьте:</i>\n<code>1 {chat_id}</code>"
            )
            await send_telegram_message(architect_tg_id, update_msg)

    await send_telegram_message(chat_id, ai_reply_text)

    return {"status": "ok"}