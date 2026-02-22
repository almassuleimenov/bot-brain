# 🧠 Architecture AI Bot: Brain (Python)

[![Python Version](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Framework-FastAPI-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![AI Model](https://img.shields.io/badge/LLM-Llama_3.3_70B-blueviolet?style=flat)](https://groq.com/)
[![Database](https://img.shields.io/badge/CMS-Sanity.io-F03E2F?style=flat&logo=sanity)](https://www.sanity.io/)

> **The "Brain" of our AI ecosystem.**
> Этот микросервис отвечает за "мышление", извлечение данных из базы проектов и генерацию человекоподобных ответов.

---

## 🛠 Технология RAG (Retrieval-Augmented Generation)

В отличие от обычных чат-ботов, этот сервис не галлюцинирует. Он использует архитектуру **RAG**:
1. **Retrieval**: Извлекает актуальные данные о проектах из **Sanity CMS**.
2. **Augmentation**: Обогащает системный промпт полученными знаниями.
3. **Generation**: Генерирует точный ответ через **Groq LPU** (Llama 3.3 70B).

---

## 🔥 Ключевые особенности
- **Extreme Speed:** Ответы генерируются практически мгновенно благодаря инфраструктуре Groq.
- **Dynamic Knowledge:** ИИ всегда знает о новых проектах, как только они добавляются в Sanity.
- **Structured IO:** Полная валидация данных через Pydantic-схемы.
- **Async Engine:** Полностью асинхронная работа на базе `FastAPI` и `httpx`.

---

## 🏗 Технологический стек
* **Backend:** FastAPI (Python)
* **AI Provider:** Groq Cloud API
* **LLM:** Llama-3.3-70b-versatile
* **Headless CMS:** Sanity.io
* **Dependency Manager:** Poetry

---
