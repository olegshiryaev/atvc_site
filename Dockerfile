FROM python:alpine

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Устанавливаем зависимости
RUN apk update && apk add --no-cache --virtual .build-deps \
    libpq \
    gcc \
    python3-dev \
    musl-dev \
    postgresql-dev \
    nodejs \
    npm

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Копируем package.json и ставим node-модули (для Tailwind)
COPY package.json package-lock.json* ./
RUN npm install

# Копируем всё остальное
COPY . .

# Собираем Tailwind
RUN npm run build

# Удаляем ненужные пакеты для билда (если хочешь — оставь)
RUN apk del .build-deps

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
