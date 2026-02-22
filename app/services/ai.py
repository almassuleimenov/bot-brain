import os
import json
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("❌ ВНИМАНИЕ: GROQ_API_KEY не найден в .env!")

client = AsyncGroq(api_key=api_key)


async def generate_reply_with_ai(user_text: str, projects_data: list) -> str:
    projects_text = json.dumps(projects_data, ensure_ascii=False, indent=2)

    # Системный Промпт (Инструкция)
    system_prompt = f"""
    Ты — профессиональный, вежливый и энергичный менеджер по продажам в архитектурном бюро.
    Твоя задача — консультировать клиентов по нашим проектам. 
    
    ПРАВИЛА:
    1. Опирайся ТОЛЬКО на предоставленную ниже базу проектов. Если клиент спрашивает то, чего нет в базе, честно скажи, что таких проектов пока нет.
    2. Не выдумывай цены, локации или концепции, которых нет в JSON.
    3. Отвечай коротко, емко и по делу (как в Telegram мессенджере). Без сложных markdown таблиц.
    
    НАША АКТУАЛЬНАЯ БАЗА ПРОЕКТОВ:
    {projects_text}
    """
    
    try:
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"[AI Service] ❌ Ошибка генерации Groq: {e}")
        return (
            "Простите, мой ИИ-мозг сейчас перегружен. Попробуйте написать чуть позже."
        )
    