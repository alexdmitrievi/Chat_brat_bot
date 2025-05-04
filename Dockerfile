FROM python:3.10-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем всё содержимое проекта
COPY . /app

# Устанавливаем зависимости
RUN pip uninstall -y aiogram && \
    pip install aiogram==2.25.1 && \
    pip install --no-cache-dir -r requirements.txt

# Запускаем бота напрямую (без оболочки sh)
CMD ["python", "bot.py"]
