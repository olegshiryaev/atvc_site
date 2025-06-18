FROM python:3.10-alpine

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Установка зависимостей и библиотек
RUN apk update && apk add --no-cache \
    libpq \
    poppler-utils \
    cairo-dev \
    pango-dev \
    gdk-pixbuf-dev \
    jpeg-dev \
    zlib-dev \
    libffi-dev \
    postgresql-dev \
    gcc \
    musl-dev \
    curl \
    && python3 -m ensurepip && pip3 install --no-cache --upgrade pip setuptools wheel poetry

# Отключаем venv внутри Poetry
ENV POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем pyproject.toml и poetry.lock до кода
COPY pyproject.toml poetry.lock ./

# Устанавливаем зависимости
RUN poetry install --no-root

# Копируем проект
COPY . .

# Открываем доступ на запись (если нужно)
RUN chmod -R 777 /app
