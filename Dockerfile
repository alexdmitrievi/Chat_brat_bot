FROM python:3.10-slim

WORKDIR /app

# Установка Tesseract и зависимостей для OCR и PDF
RUN apt-get update && \
    apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-rus \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    poppler-utils && \
    apt-get clean

# Копируем проект
COPY . /app

# Установка Python-зависимостей
RUN pip uninstall -y aiogram && \
    pip install aiogram==2.25.1 && \
    pip install --no-cache-dir -r requirements.txt

# Запуск бота
CMD ["python", "bot.py"]

