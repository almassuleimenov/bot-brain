import os
import httpx
from dotenv import load_dotenv

load_dotenv()

GREEN_API_URL = os.getenv("GREEN_API_URL", "https://api.green-api.com")
GREEN_API_INSTANCE = os.getenv("GREEN_API_INSTANCE")
GREEN_API_TOKEN = os.getenv("GREEN_API_TOKEN")


async def send_whatsapp_message(chat_id: str, message: str):
    """
    Отправляет текстовое сообщение в WhatsApp через Green-API.
    """
    if not GREEN_API_INSTANCE or not GREEN_API_TOKEN:
        print("❌ Ошибка: Нет данных Green-API в .env")
        return False

    url = (
        f"{GREEN_API_URL}/waInstance{GREEN_API_INSTANCE}/sendMessage/{GREEN_API_TOKEN}"
    )
    payload = {"chatId": chat_id, "message": message}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            print(f"✅ Успешно отправлено уведомление на номер: {chat_id}")
            return True
        except Exception as e:
            print(f"❌ Ошибка отправки в WhatsApp: {e}")
            return False
