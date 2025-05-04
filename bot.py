import logging
import os
import zipfile
import pytesseract
import pandas as pd
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import BotCommand
from aiogram.utils import executor
from PIL import Image
from pdf2image import convert_from_path

API_TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
user_sessions = {}

# Меню Telegram
async def set_menu():
    await bot.set_my_commands([
        BotCommand("start", "Перезапустить бота"),
    ])

# Справочник ТН ВЭД
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

def parse_ocr_lines(text):
    lines = text.split("\n")
    data = []
    seen = set()

    for line in lines:
        line = line.strip().lower()
        if not line or not any(k in line for k in catalog):
            continue

        name = next((k for k in catalog if k in line), None)
        if name in seen:
            continue
        seen.add(name)

        tnved, trts, st1 = catalog[name]

        # вес
        netto = brutto = 0
        if "/" in line and "кг" in line:
            try:
                weight_part = line.split("кг")[0]
                netto, brutto = weight_part.split("/")
                netto = float(netto.strip().replace(",", "."))
                brutto = float(brutto.strip().replace(",", "."))
            except:
                pass
        else:
            try:
                netto = float([w.replace(",", ".").replace("кг", "") for w in line.split() if "кг" in w][0])
                brutto = netto
            except:
                pass

        # цена
        price = 0
        for w in line.split():
            try:
                w_clean = w.replace("$", "").replace("usd", "").replace(",", ".")
                if w_clean.replace(".", "").isdigit():
                    price = float(w_clean)
                    break
            except:
                continue

        total = round(netto * price, 2)

        if netto == 0 and price == 0:
            continue

        data.append({
            "Наименование товара": name,
            "Код ТН ВЭД": tnved,
            "Кол-во мест": 0,
            "Вес нетто (кг)": netto,
            "Вес брутто (кг)": brutto,
            "Цена за кг ($)": price,
            "Сумма ($)": total,
            "ТР ТС": trts,
            "СТ-1": st1
        })

    return data

def parse_excel_structured_table(filepath):
    df = pd.read_excel(filepath, header=None)
    data = []
    header_index = None

    for i, row in df.iterrows():
        row_text = " ".join([str(cell).lower() for cell in row if pd.notnull(cell)])
        if "наименование" in row_text and "вес" in row_text:
            header_index = i
            break

    if header_index is None:
        return data

    df = df.iloc[header_index+1:]

    seen = set()
    for _, row in df.iterrows():
        cells = [str(c).strip().lower() if pd.notnull(c) else "" for c in row]
        line = " ".join(cells)

        if not any(k in line for k in catalog):
            continue

        name = next((k for k in catalog if k in line), None)
        if name in seen:
            continue  # убираем повторы
        seen.add(name)

        tnved, trts, st1 = catalog[name]

        # места
        places = 0
        try:
            places = int([c for c in cells if c.isdigit()][-1])
        except:
            pass

        # вес
        netto = brutto = 0
        for c in cells:
            if "/" in c and "кг" in c:
                try:
                    netto, brutto = c.replace("кг", "").split("/")
                    netto = float(netto.strip().replace(",", "."))
                    brutto = float(brutto.strip().replace(",", "."))
                    break
                except:
                    continue

        # цена
        price = 0
        for c in cells:
            try:
                if any(x in c for x in ["$", "usd"]) or c.replace(",", ".").replace(".", "").isdigit():
                    price = float(c.replace("$", "").replace("usd", "").replace(",", "."))
                    break
            except:
                continue

        total = round(netto * price, 2)

        if netto == 0 and price == 0:
            continue  # пропускаем пустые строки

        data.append({
            "Наименование товара": name,
            "Код ТН ВЭД": tnved,
            "Кол-во мест": places,
            "Вес нетто (кг)": netto,
            "Вес брутто (кг)": brutto,
            "Цена за кг ($)": price,
            "Сумма ($)": total,
            "ТР ТС": trts,
            "СТ-1": st1
        })

    return data

def extract_text_from_file(file_path):
    text = ""
    if file_path.endswith(".pdf"):
        images = convert_from_path(file_path)
        for image in images:
            text += pytesseract.image_to_string(image, lang='rus+eng') + "\n"
    elif file_path.lower().endswith((".jpg", ".jpeg", ".png")):
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image, lang='rus+eng')
    return text

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await set_menu()
    user_sessions[message.from_user.id] = []
    await message.answer("Привет! Отправь ZIP-архив с инвойсом (Excel, PDF или JPG/PNG)")

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
            parsed = parse_excel_structured_table(full_path)
            result_data.extend(parsed)
        elif f.lower().endswith((".pdf", ".jpg", ".jpeg", ".png")):
            text = extract_text_from_file(full_path)
            parsed = parse_ocr_lines(text)
            result_data.extend(parsed)
    if not result_data:
        await message.answer("❌ Не удалось распознать ни одного товара.")
        return
    user_sessions[uid] = result_data
    preview = "\n".join([
        f"{x['Наименование товара']} | {x['Код ТН ВЭД']} | {x['Вес нетто (кг)']} кг | ${x['Сумма ($)']}" 
        for x in result_data
    ])
    await message.answer(f"✅ Найдено {len(result_data)} позиций:\n\n{preview}\n\nНапиши 'готово' для генерации Excel.")

@dp.message_handler(lambda msg: msg.from_user.id in user_sessions and msg.text.lower() == "готово")
async def export_excel(message: types.Message):
    uid = message.from_user.id
    items = user_sessions.get(uid, [])
    df = pd.DataFrame(items)
    out_path = f"/mnt/data/declaration_{uid}.xlsx"
    df.to_excel(out_path, index=False)
    await message.answer_document(types.InputFile(out_path), caption="✅ Готово! Декларация в Excel.")
    user_sessions.pop(uid)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(set_menu())
    executor.start_polling(dp, skip_updates=True)
