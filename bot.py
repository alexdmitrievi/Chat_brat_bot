import os
import logging
import json
import asyncio
import pandas as pd
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import BotCommand, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.executor import start_webhook

# Webhook config for Render
API_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL", "https://your-service.onrender.com")
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.environ.get("PORT", 8080))

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

logging.basicConfig(level=logging.INFO)

STATE_FILE = "user_states.json"

def load_states():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_states(states):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(states, f, ensure_ascii=False, indent=2)

user_states = load_states()

catalog = {
    "томаты": ("0702 00 000 0", "Нужна", "Да"),
    "огурцы": ("0707 00 190 0", "Нужна", "Да"),
    "картофель": ("0701 90 500 0", "Нужна", "Да"),
    "лук": ("0703 10 190 0", "Нужна", "Да"),
    "чеснок": ("0703 20 000 0", "Нужна", "Да"),
    "капуста": ("0704 90 100 0", "Нужна", "Да"),
    "брокколи": ("0704 10 000 0", "Нужна", "Да"),
    "морковь": ("0706 10 000 0", "Нужна", "Да"),
    "свекла": ("0706 20 000 0", "Нужна", "Да"),
    "редис": ("0706 90 900 2", "Нужна", "Да"),
    "петрушка": ("0706 90 900 1", "Нужна", "Да"),
    "укроп": ("0706 90 900 3", "Нужна", "Да"),
    "шпинат": ("0710 30 000 0", "Нужна", "Да"),
    "кабачки": ("0709 90 900 1", "Нужна", "Да"),
    "баклажаны": ("0709 30 000 0", "Нужна", "Да"),
    "перец": ("0709 60 100 0", "Нужна", "Да"),
    "яблоки": ("0808 10 800 0", "Нужна", "Да"),
    "груши": ("0808 30 900 0", "Нужна", "Да"),
    "абрикосы": ("0809 10 000 0", "Нужна", "Да"),
    "черешня": ("0809 29 000 0", "Нужна", "Да"),
    "персики": ("0809 30 000 0", "Нужна", "Да"),
    "сливы": ("0809 40 000 0", "Нужна", "Да"),
    "нектарины": ("0809 30 100 0", "Нужна", "Да"),
    "гранаты": ("0810 90 500 0", "Нужна", "Да"),
    "хурма": ("0810 70 000 0", "Нужна", "Да"),
    "виноград": ("0806 10 100 0", "Нужна", "Да"),
    "мандарины": ("0805 20 100 0", "Нужна", "Да"),
    "апельсины": ("0805 10 200 0", "Нужна", "Да"),
    "лимоны": ("0805 50 100 0", "Нужна", "Да"),
    "бананы": ("0803 90 100 0", "Нужна", "Нет"),
    "киви": ("0810 50 000 0", "Нужна", "Нет"),
    "финики": ("0804 10 000 0", "Нужна", "Нет"),
    "инжир": ("0804 20 100 0", "Нужна", "Нет"),
    "арбузы": ("0807 11 000 0", "Нужна", "Да"),
    "дыни": ("0807 19 000 0", "Нужна", "Да")
}

def is_valid_date(date_str):
    try:
        datetime.strptime(date_str, "%d.%m.%Y")
        return True
    except ValueError:
        return False

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    uid = str(message.from_user.id)
    user_states[uid] = {
        "step": "product",
        "current": {},
        "positions": []
    }
    save_states(user_states)
    await message.answer("Привет! Напиши название или часть названия товара (например, 'том').")

@dp.message_handler(commands=["help"])
async def cmd_help(message: types.Message):
    await message.answer(
        "Этот бот помогает подготовить Excel-декларацию для Альта-ГТД.\n"
        "/start — начать\n"
        "/cancel — сбросить сессию."
    )

@dp.message_handler(commands=["cancel"])
async def cmd_cancel(message: types.Message):
    user_states.pop(str(message.from_user.id), None)
    save_states(user_states)
    await message.answer("❌ Сессия сброшена. Введите /start, чтобы начать заново.")

@dp.message_handler(lambda msg: msg.text and msg.text.lower() in ["да", "нет"])
async def yes_no_handler(message: types.Message):
    uid = str(message.from_user.id)
    state = user_states.get(uid, {})
    if state.get("step") == "add_more":
        if message.text.lower() == "да":
            state["step"] = "product"
            save_states(user_states)
            await message.answer("Введите наименование следующего товара:")
        else:
            state["step"] = "invoice_number"
            save_states(user_states)
            await message.answer("Введи номер инвойса:")

@dp.message_handler(lambda msg: msg.text)
async def handle_input(message: types.Message):
    uid = str(message.from_user.id)
    state = user_states.get(uid, {})
    step = state.get("step")
    text = message.text.strip().lower()

    if step == "product":
        matches = [k for k in catalog if text in k]
        if not matches:
            await message.answer("❌ Товар не найден. Попробуйте ещё раз.")
            return
        if len(matches) == 1:
            name = matches[0]
            tnved, trts, st1 = catalog[name]
            state["current"] = {
                "Наименование товара": name,
                "Код ТН ВЭД": tnved,
                "ТР ТС": trts,
                "СТ-1": st1,
                "Страна происхождения": "Узбекистан",
                "Страна отправления": "Узбекистан",
                "Преференция": "Да",
                "Ставка НДС (%)": 10
            }
            state["step"] = "netto"
            save_states(user_states)
            await message.answer("Введи вес нетто (в кг):")
        else:
            markup = ReplyKeyboardMarkup(resize_keyboard=True)
            for name in matches:
                markup.add(KeyboardButton(name))
            await message.answer("Выберите товар:", reply_markup=markup)

    elif step == "netto":
        try:
            state["current"]["Вес нетто (кг)"] = float(text.replace(",", "."))
            state["step"] = "brutto"
            save_states(user_states)
            await message.answer("Введи вес брутто (в кг):")
        except:
            await message.answer("❌ Введи число, например: 350.5")

    elif step == "brutto":
        try:
            state["current"]["Вес брутто (кг)"] = float(text.replace(",", "."))
            state["step"] = "places"
            save_states(user_states)
            await message.answer("Введи количество мест:")
        except:
            await message.answer("❌ Введи число, например: 360")

    elif step == "places":
        try:
            state["current"]["Кол-во мест"] = int(text)
            state["step"] = "price"
            save_states(user_states)
            await message.answer("Введи цену за кг в долларах (например: 0.85):")
        except:
            await message.answer("❌ Введи целое число, например: 20")

    elif step == "price":
        try:
            price = float(text.replace(",", "."))
            current = state["current"]
            current["Цена за кг ($)"] = price
            current["Сумма ($)"] = round(current["Вес нетто (кг)"] * price, 2)
            state["positions"].append(current)
            state["current"] = {}
            state["step"] = "add_more"
            save_states(user_states)
            await message.answer("✅ Позиция добавлена. Добавить ещё товар? (да/нет)")
        except:
            await message.answer("❌ Введи корректную цену, например: 1.25")

    elif step == "invoice_number":
        state["invoice_number"] = message.text.strip()
        state["step"] = "invoice_date"
        save_states(user_states)
        await message.answer("Введи дату инвойса (например: 01.05.2025):")

    elif step == "invoice_date":
        if not is_valid_date(text):
            await message.answer("❌ Неверный формат даты. Пример: 01.05.2025")
            return
        state["invoice_date"] = text
        state["step"] = "cmr_number"
        save_states(user_states)
        await message.answer("Введи номер CMR:")

    elif step == "cmr_number":
        state["cmr_number"] = message.text.strip()
        state["step"] = "cmr_date"
        save_states(user_states)
        await message.answer("Введи дату CMR (например: 02.05.2025):")

    elif step == "cmr_date":
        if not is_valid_date(text):
            await message.answer("❌ Неверный формат даты. Пример: 02.05.2025")
            return
        state["cmr_date"] = text
        df = pd.DataFrame(state["positions"])
        df["Номер инвойса"] = state["invoice_number"]
        df["Дата инвойса"] = state["invoice_date"]
        df["Номер CMR"] = state["cmr_number"]
        df["Дата CMR"] = state["cmr_date"]
        file_path = f"declaration_{uid}.xlsx"
        df.to_excel(file_path, index=False)
        await message.answer_document(types.InputFile(file_path), caption="📄 Декларация готова!")
        user_states.pop(uid, None)
        save_states(user_states)

async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)
    await bot.set_my_commands([
        BotCommand("start", "Перезапустить бота"),
        BotCommand("help", "Как работает бот"),
        BotCommand("cancel", "Сбросить сессию")
    ])
    logging.info("Бот запущен с Webhook")

async def on_shutdown(dp):
    await bot.delete_webhook()
    logging.info("Бот выключен")

if __name__ == "__main__":
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )

