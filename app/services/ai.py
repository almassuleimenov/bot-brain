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
    """
    Возвращает словарь (dict) с двумя ключами:
    - 'reply': текст ответа бота для клиента
    - 'action': системный статус (none, new_booking, reschedule)
    """
    projects_text = json.dumps(projects_data, ensure_ascii=False, indent=2)

    system_prompt = f"""
    Ты — Томирис, профессиональный ИИ-ассистент архитектурного бюро "SNP-ARCH". 
    Твой руководитель — главный архитектор бюро.

    🚨 ЯЗЫКОВЫЕ ПРАВИЛА:
    1. Отвечай строго на языке клиента (русский или казахский).
    2. Без иностранных слов и иероглифов.

    ТВОЙ СТИЛЬ:
    1. Женское лицо, вежливо, тепло.
    2. Задавай ТОЛЬКО ОДИН вопрос в конце сообщения (пока не дойдете до назначения встречи).

    ИСТОРИЯ ДИАЛОГА:
    {history if history else "[Это первое сообщение]"}

    ПРОЕКТЫ:
    {projects_text}

    АЛГОРИТМ:
    Шаг 0. ИМЯ.
    Шаг 1. СУТЬ (жилье/коммерция).
    Шаг 2. ДЕТАЛИ (семья, пожелания).
    Шаг 3. УЧАСТОК.
    Шаг 4. КОНТАКТ (телефон).
    Шаг 5. ПРЕДЛОЖЕНИЕ ВСТРЕЧИ.

    🚨 ВАЖНО: ТЫ ОБЯЗАНА ОТВЕЧАТЬ СТРОГО В ФОРМАТЕ JSON. 
    Твой ответ должен быть валидным JSON-объектом следующей структуры:
    {{
        "reply": "Твой естественный ответ клиенту",
        "action": "системный статус"
    }}

    Логика поля "action" (может принимать ТОЛЬКО одно из 3 значений):
    - "none" : Обычный диалог, сбор информации.
    - "new_booking" : Клиент ВПЕРВЫЕ предложил или подтвердил время встречи.
    - "reschedule" : Встреча уже обсуждалась ранее, но клиент просит изменить время (или соглашается на новое время от архитектора).

    В поле "reply" общайся естественно. 
    Если статус "new_booking" или "reschedule", скажи своими словами, что передала или обновила информацию для архитектора и просишь подождать подтверждения. Не задавай вопросов в конце, если статус не "none".
    """

    try:
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            response_format={"type": "json_object"}  # Форсируем JSON
        )
        
        raw_content = response.choices[0].message.content.strip()
        parsed_data = json.loads(raw_content)
        
        # Страховка, если ИИ забыл вернуть ключ
        if "action" not in parsed_data:
            parsed_data["action"] = "none"
            
        return parsed_data

    except Exception as e:
        print(f"[AI Service] ❌ Ошибка генерации Groq: {e}")
        return {
            "reply": "Простите, у меня небольшая техническая заминка. Секундочку... 🌸", 
            "action": "none"
        }


async def generate_client_summary(history: str, phone_number: str) -> str:
    """
    Функция-аналитик. Берет всю историю переписки и делает из нее короткую анкету для архитектора.
    """
    summary_prompt = f"""
    Проанализируй диалог с клиентом и составь краткую выжимку-анкету для главного архитектора.
    
    ИСТОРИЯ ДИАЛОГА:
    {history}

    Системный ID чата: {phone_number}

    Верни ТОЛЬКО текст анкеты строго по этому шаблону (без вступительных слов):
    🚨 *НОВЫЙ КЛИЕНТ ОТ ТОМИРИС!* 🚨
    👤 *Клиент:* [Имя, если не назвал - напиши "Не назвал"]
    📱 *Телефон:* [Извлеки реальный номер телефона из диалога, если клиент его написал. Если не написал - напиши "Не оставил"]
    💻 *Источник:* [Если ID чата длинный (цифры) - напиши "Telegram". Если есть @c.us - напиши "WhatsApp"]
    🎯 *Цель:* [Кратко: для себя / коммерция, суть проекта]
    👨‍👩‍👧‍👦 *Детали:* [Семья / Особенности бизнеса]
    📍 *Участок:* [Есть/Нет, какая информация известна]
    💰 *Бюджет:* [Сумма или "Не обсуждался"]
    📝 *Комментарий Томирис:* [Краткая выжимка пожеланий и настроения клиента]
    ⏰ *Желаемое время:* [Когда клиент предложил встретиться/созвониться]

    👇 *Действие для главного архитектора:*
    Скопируй эту команду и отправь мне в ответ:
    ✅ Подтвердить: `1 {phone_number}`
    🕒 Перенести: `2 {phone_number} [твое время]`
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
        return "🚨 Ошибка генерации анкеты. Проверьте логи."