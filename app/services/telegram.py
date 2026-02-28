import os
import httpx
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def send_telegram_message(chat_id: str, text: str):
   
    if not TELEGRAM_BOT_TOKEN:
        print("❌ Ошибка: Нет TELEGRAM_BOT_TOKEN в .env")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML" 
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            print(f"✅ Успешно отправлено в Telegram на ID: {chat_id}")
            return True
        except Exception as e:
            print(f"❌ Ошибка отправки в Telegram: {e}")
            return False