import logging
import os
import zipfile
import pytesseract
import pandas as pd
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils.executor import start_polling
from datetime import datetime
from PIL import Image
from pdf2image import convert_from_path

API_TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(level=logging.INFO)

if not API_TOKEN:
    raise ValueError("❌ Переменная BOT_TOKEN не установлена! Проверь Render Secrets.")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
user_sessions = {}

async def on_startup(_):
    await bot.set_my_commands([
        types.BotCommand(command="/start", description="🔁 Перезапуск бота")
    ])

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

def extract_text_from_file(file_path):
    text = ""
    if file_path.endswith('.pdf'):
        images = convert_from_path(file_path)
        for i, image in enumerate(images):
            ocr = pytesseract.image_to_string(image, lang='rus+eng')
            print(f"\n[OCR PDF page {i+1}]\n{ocr}")
            text += ocr + "\n"
    elif file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
        image = Image.open(file_path)
        ocr = pytesseract.image_to_string(image, lang='rus+eng')
        print(f"\n[OCR Image]\n{ocr}")
        text += ocr
    return text

def parse_ocr_lines(text):
    lines = text.split("\n")
    data = []
    for line in lines:
        line = line.strip().lower()
        if not line:
            continue
        if any(key in line for key in catalog):
            print(f"[OCR строка] {line}")
            name = next((k for k in catalog if k in line), None)
            tnved, trts, st1 = catalog[name]

            # Масса
            try:
                weight = float([w.replace(",", ".").replace("кг", "") for w in line.split() if "кг" in w][0])
            except:
                weight = 0

            # Цена
            try:
                price = float([p.replace(",", ".").replace("$", "") for p in line.split() if "$" in p or "usd" in p][0])
            except:
                price = 0

            # Кол-во мест
            try:
                digits = [int(p) for p in line.split() if p.isdigit()]
                places = digits[-1] if digits else 0
            except:
                places = 0

            total = round(weight * price, 2)
            data.append({
                "Наименование товара": name,
                "Код ТН ВЭД": tnved,
                "Кол-во мест": places,
                "Вес нетто (кг)": weight,
                "Вес брутто (кг)": weight,
                "Цена за кг ($)": price,
                "Сумма ($)": total,
                "ТР ТС": trts,
                "СТ-1": st1
            })
    return data

def parse_excel_file(filepath):
    data = []
    try:
        df = pd.read_excel(filepath, header=None)
    except Exception as e:
        print(f"[Excel] Ошибка чтения: {e}")
        return data

    for i, row in df.iterrows():
        row_text = " ".join([str(cell).lower() for cell in row if pd.notnull(cell)])
        if not row_text.strip():
            continue
        if any(key in row_text for key in catalog):
            print(f"[Excel строка] {row_text}")
            name = next((key for key in catalog if key in row_text), None)
            tnved, trts, st1 = catalog[name]

            # Масса
            try:
                weight = float([w.replace(",", ".").replace("кг", "") for w in row_text.split() if "кг" in w][0])
            except:
                weight = 0

            # Цена
            try:
                price = float([p.replace(",", ".").replace("$", "") for p in row_text.split() if "$" in p or "usd" in p][0])
            except:
                price = 0

            # Кол-во мест
            try:
                digits = [int(p) for p in row_text.split() if p.isdigit()]
                places = digits[-1] if digits else 0
            except:
                places = 0

            total = round(weight * price, 2)
            data.append({
                "Наименование товара": name,
                "Код ТН ВЭД": tnved,
                "Кол-во мест": places,
                "Вес нетто (кг)": weight,
                "Вес брутто (кг)": weight,
                "Цена за кг ($)": price,
                "Сумма ($)": total,
                "ТР ТС": trts,
                "СТ-1": st1
            })
    return data

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_sessions[message.from_user.id] = []
    await message.answer("📦 Отправь ZIP-архив с инвойсом (Excel, PDF или JPG/PNG). Я распознаю товары и подготовлю Excel-декларацию для Альта-ГТД.")

@dp.message_handler(content_types=types.ContentType.DOCUMENT)
async def handle_zip(message: types.Message):
    uid = message.from_user.id
    file_path = f"/mnt/data/{message.document.file_name}"
    await message.document.download(destination_file=file_path)
    extract_dir = f"/mnt/data/extracted_{uid}"
    os.makedirs(extract_dir, exist_ok=True)

    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)

    files = os.listdir(extract_dir)
    result_data = []

    for f in files:
        full_path = os.path.join(extract_dir, f)
        if f.endswith(".xlsx"):
            result_data.extend(parse_excel_file(full_path))
        elif f.lower().endswith((".pdf", ".jpg", ".jpeg", ".png")):
            text = extract_text_from_file(full_path)
            parsed = parse_ocr_lines(text)
            result_data.extend(parsed)

    if not result_data:
        await message.answer("❌ Не удалось распознать ни одного товара.")
        return

    user_sessions[uid] = result_data
    preview = "\n".join([
        f"{i+1}. {x['Наименование товара']} | {x['Код ТН ВЭД']} | {x['Вес нетто (кг)']} кг | ${x['Сумма ($)']}"
        for i, x in enumerate(result_data)
    ])
    await message.answer(
        f"✅ Найдено {len(result_data)} позиций:\n{preview}\n\nНапиши 'готово' для генерации Excel."
    )

@dp.message_handler(lambda msg: msg.from_user.id in user_sessions and msg.text.lower() == "готово")
async def export_excel(message: types.Message):
    uid = message.from_user.id
    items = user_sessions.get(uid, [])
    for i, item in enumerate(items):
        item["№"] = i + 1
    df = pd.DataFrame(items)[[
        "№", "Наименование товара", "Код ТН ВЭД", "Кол-во мест",
        "Вес нетто (кг)", "Вес брутто (кг)", "Цена за кг ($)",
        "Сумма ($)", "ТР ТС", "СТ-1"
    ]]
    out_path = f"/mnt/data/declaration_altagt_{uid}.xlsx"
    df.to_excel(out_path, index=False)
    await message.answer_document(types.InputFile(out_path), caption="✅ Готово! Excel-декларация для Альта-ГТД.")
    user_sessions.pop(uid)

if __name__ == '__main__':
    start_polling(dp, skip_updates=True, on_startup=on_startup)