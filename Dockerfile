FROM python:3.10-slim

WORKDIR /app
COPY . /app

RUN pip uninstall -y aiogram && \
    pip install aiogram==2.25.1 && \
    pip install --no-cache-dir -r requirements.txt

CMD ["python", "bot.py"]

