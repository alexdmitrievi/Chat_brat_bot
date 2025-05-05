
import os
import logging
import asyncio
import pandas as pd
from aiogram import Bot, Dispatcher, types
from aiogram.types import BotCommand
from aiogram.utils import executor

API_TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

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

user_states = {}

async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)
    await bot.set_my_commands([
        BotCommand("start", "Перезапустить бота"),
        BotCommand("help", "Как работает бот"),
        BotCommand("cancel", "Сбросить сессию")
    ])

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_states[message.from_user.id] = {
        "step": "product",
        "current": {},
        "positions": [],
        "invoice_number": "",
        "invoice_date": "",
        "cmr_number": "",
        "cmr_date": ""
    }
    await set_menu()
    await message.answer("Привет! Давай соберём декларацию. Напиши наименование товара (например, 'томаты'):")

@dp.message_handler(lambda msg: msg.from_user.id in user_states)
async def handle_input(message: types.Message):
    state = user_states[message.from_user.id]
    step = state["step"]
    text = message.text.strip().lower()

    if step == "product":
        if text not in catalog:
            await message.answer("❌ Товар не найден в справочнике. Попробуй ещё раз.")
            return
        tnved, trts, st1 = catalog[text]
        state["current"] = {
            "Наименование товара": text,
            "Код ТН ВЭД": tnved,
            "ТР ТС": trts,
            "СТ-1": st1,
            "Страна происхождения": "Узбекистан",
            "Страна отправления": "Узбекистан",
            "Преференция": "Да",
            "Ставка НДС (%)": 10
        }
        state["step"] = "netto"
        await message.answer("Введи вес нетто (в кг):")

    elif step == "netto":
        try:
            state["current"]["Вес нетто (кг)"] = float(text.replace(",", "."))
            state["step"] = "brutto"
            await message.answer("Введи вес брутто (в кг):")
        except:
            await message.answer("❌ Введи число, например: 350.5")

    elif step == "brutto":
        try:
            state["current"]["Вес брутто (кг)"] = float(text.replace(",", "."))
            state["step"] = "places"
            await message.answer("Введи количество мест:")
        except:
            await message.answer("❌ Введи число, например: 360")

    elif step == "places":
        try:
            state["current"]["Кол-во мест"] = int(text)
            state["step"] = "price"
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
            await message.answer("✅ Позиция добавлена. Добавить ещё товар? (да/нет)")
        except:
            await message.answer("❌ Введи корректную цену, например: 1.25")

    elif step == "add_more":
        if text in ["да", "yes", "д"]:
            state["step"] = "product"
            await message.answer("Напиши наименование следующего товара:")
        elif text in ["нет", "no", "н"]:
            state["step"] = "invoice_number"
            await message.answer("Введи номер инвойса:")
        else:
            await message.answer("Пожалуйста, ответь 'да' или 'нет'.")

    elif step == "invoice_number":
        state["invoice_number"] = text
        state["step"] = "invoice_date"
        await message.answer("Введи дату инвойса (например: 01.05.2025):")

    elif step == "invoice_date":
        state["invoice_date"] = text
        state["step"] = "cmr_number"
        await message.answer("Введи номер CMR:")

    elif step == "cmr_number":
        state["cmr_number"] = text
        state["step"] = "cmr_date"
        await message.answer("Введи дату CMR (например: 02.05.2025):")

    elif step == "cmr_date":
        state["cmr_date"] = text
        df = pd.DataFrame(state["positions"])
        df["Номер инвойса"] = state["invoice_number"]
        df["Дата инвойса"] = state["invoice_date"]
        df["Номер CMR"] = state["cmr_number"]
        df["Дата CMR"] = state["cmr_date"]
        file_path = f"declaration_{message.from_user.id}.xlsx"
        df.to_excel(file_path, index=False)
        await message.answer_document(types.InputFile(file_path), caption="📄 Декларация готова!")
        del user_states[message.from_user.id]

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(set_menu())
    executor.start_polling(dp, skip_updates=True)

