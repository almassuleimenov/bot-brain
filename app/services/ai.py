import os
import json
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("❌ ВНИМАНИЕ: GROQ_API_KEY не найден в .env!")

client = AsyncGroq(api_key=api_key)


async def generate_reply_with_ai(
    user_text: str, projects_data: list, history: str = ""
) -> dict:
    projects_text = json.dumps(projects_data, ensure_ascii=False, indent=2)

    system_prompt = f"""
    Ты — Томирис, профессиональный ИИ-ассистент архитектурного бюро "SNP-ARCH". 
    Твой руководитель — главный архитектор бюро.

    🚨 ЯЗЫКОВЫЕ ПРАВИЛА:
    1. Отвечай строго на языке клиента (русский или казахский).
    2. Без иностранных слов и иероглифов.

    ТВОЙ СТИЛЬ:
    1. Женское лицо, вежливо, тепло.
    2. Задавай ТОЛЬКО ОДИН вопрос в конце сообщения.
    3. 🚨 ЖЕСТКИЙ ЗАПРЕТ НА ПРИВЕТСТВИЯ: Если в "ИСТОРИИ ДИАЛОГА" уже есть текст от клиента, ТЕБЕ КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО писать "Здравствуйте", "Добрый день", "Приветствую". Начинай ответ сразу по делу!

    ИСТОРИЯ ДИАЛОГА:
    {history if history else "[Это первое сообщение. Поздоровайся и спроси, чем можешь помочь]"}

    ПРОЕКТЫ: {projects_text}

    АЛГОРИТМ:
    Шаг 0. ИМЯ.
    Шаг 1. СУТЬ (жилье/коммерция).
    Шаг 2. ДЕТАЛИ (семья, пожелания).
    Шаг 3. УЧАСТОК.
    Шаг 4. КОНТАКТ (телефон).
    Шаг 5. ПРЕДЛОЖЕНИЕ ВСТРЕЧИ.

    🚨 ВАЖНО: ТЫ ОБЯЗАНА ОТВЕЧАТЬ СТРОГО В ФОРМАТЕ JSON:
    {{
        "reply": "Твой ответ клиенту",
        "action": "системный статус"
    }}

    Логика "action":
    - "none" : Обычный диалог.
    - "new_booking" : Клиент ВПЕРВЫЕ предложил/подтвердил время встречи.
    - "reschedule" : Клиент просит изменить время или соглашается на новое.

    В поле "reply" общайся естественно. Если статус "new_booking" или "reschedule", скажи своими словами, что передала информацию архитектору и просишь подождать подтверждения (вопросов в конце не задавай).
    """

    try:
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        raw_content = response.choices[0].message.content.strip()
        parsed_data = json.loads(raw_content)
        
        if "action" not in parsed_data:
            parsed_data["action"] = "none"
            
        return parsed_data

    except Exception as e:
        print(f"[AI Service] ❌ Ошибка генерации: {e}")
        return {"reply": "Простите, техническая заминка. Секундочку... 🌸", "action": "none"}


async def generate_client_summary(history: str) -> str:
    """
    Генерирует только факты из переписки. Без шапки и кнопок.
    """
    summary_prompt = f"""
    Проанализируй диалог с клиентом и сделай выжимку.
    ИСТОРИЯ ДИАЛОГА:
    {history}

    Верни ТОЛЬКО факты строго по этому шаблону (без лишних слов):
    👤 *Имя:* [Имя или "Не назвал"]
    🎯 *Цель:* [Суть проекта]
    👨‍👩‍👧‍👦 *Детали:* [Семья / Особенности]
    📍 *Участок:* [Есть/Нет]
    💰 *Бюджет:* [Сумма или "Не обсуждался"]
    ⏰ *Желаемое время:* [Когда клиент предложил встретиться]
    """

    try:
        response = await client.chat.completions.create(
            messages=[{"role": "user", "content": summary_prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"[AI Service] ❌ Ошибка генерации анкеты: {e}")
        return "🚨 Ошибка генерации фактов."