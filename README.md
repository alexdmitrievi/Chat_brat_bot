# Telegram Decl Bot v3

Этот бот принимает ZIP-архив с Excel-инвойсом и JPG-документами, проверяет комплектность, извлекает товарные позиции и формирует Excel-декларацию, готовую к импорту в Альта-ГТД.

## 🚀 Как запустить на Fly.io

1. Установи Fly.io CLI: https://fly.io/docs/hands-on/install-flyctl/
2. Открой терминал в этой папке:

```bash
fly launch --name capitalpay-decl-bot
fly secrets set BOT_TOKEN=твой_токен_бота
fly deploy
```

## 📁 Что внутри:
- `bot.py` — логика Telegram-бота
- `Dockerfile` — инструкция для сборки контейнера
- `requirements.txt` — зависимости Python
