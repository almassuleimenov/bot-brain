# Используем легкий официальный образ Python
FROM python:3.11-slim

# Устанавливаем системные зависимости (нужны для сборки некоторых пакетов)
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Устанавливаем Poetry
RUN pip install poetry

# Задаем рабочую папку внутри контейнера
WORKDIR /app

# Копируем файлы зависимостей
COPY pyproject.toml poetry.lock ./

# Настраиваем Poetry
RUN poetry config virtualenvs.create false

# Устанавливаем библиотеки
RUN poetry install --no-interaction --no-ansi --no-root

# Копируем весь остальной код проекта
COPY . .

# Открываем порт 8000
EXPOSE 8000

# Команда для запуска нашего FastAPI сервера
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]