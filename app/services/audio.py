import httpx
import tempfile
import os
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
client = AsyncGroq(api_key=api_key)


async def transcribe_audio_from_url(audio_url: str) -> str:
    """
    Скачивает аудио по ссылке и отправляет в Groq Whisper.
    Возвращает расшифрованный текст.
    """
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(audio_url)
            response.raise_for_status()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
            temp_audio.write(response.content)
            temp_filepath = temp_audio.name

        # Отправляем в Groq Whisper
        print(
            f"🎧 Отправляем аудио ({os.path.getsize(temp_filepath)} байт) в Whisper..."
        )
        with open(temp_filepath, "rb") as file:
            transcription = await client.audio.transcriptions.create(
                file=(temp_filepath, file.read()),
                model="whisper-large-v3",
                prompt="Это голосовое сообщение от клиента архитектурного бюро. Язык может быть русский, казахский или другой.",
            )

        os.remove(temp_filepath)

        result_text = transcription.text.strip()
        print(f"📝 Расшифровано: {result_text}")
        return result_text

    except Exception as e:
        print(f"❌ Ошибка расшифровки аудио: {e}")
        return ""
