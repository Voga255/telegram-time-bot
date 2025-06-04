import logging
import json
import os
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

import gspread
from oauth2client.service_account import ServiceAccountCredentials

USERS_FILE = "users.json"
SPREADSHEET_NAME = "Відмітки часу"
keyboard = [
    [InlineKeyboardButton("Прийшов", callback_data='arrived')],
    [InlineKeyboardButton("Пішов", callback_data='left')]
]

logging.basicConfig(level=logging.INFO)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
spreadsheet = client.open(SPREADSHEET_NAME)

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

user_names = load_users()

def get_or_create_sheet(full_name, user_id):
    sheet_title = f"{full_name} ({user_id})"
    try:
        worksheet = spreadsheet.worksheet(sheet_title)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_title, rows="1000", cols="3")
        worksheet.append_row(["Дія", "Час"])
    return worksheet

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id in user_names:
        await update.message.reply_text("Оберіть дію:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("Введіть, будь ласка, ваше ім’я та прізвище:")

async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in user_names:
        full_name = update.message.text.strip()
        user_names[user_id] = full_name
        save_users(user_names)
        get_or_create_sheet(full_name, user_id)
        await update.message.reply_text(
            f"Дякую, {full_name}! Тепер ви можете фіксувати час:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text("Ви вже зареєстровані. Оберіть дію:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    full_name = user_names.get(user_id)

    if not full_name:
        await query.edit_message_text("Спочатку введіть ім’я та прізвище через /start.")
        return

    action = "Прийшов" if query.data == "arrived" else "Пішов"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    worksheet = get_or_create_sheet(full_name, user_id)
    worksheet.append_row([action, timestamp])

    await query.edit_message_text(f"{action} о {timestamp}")

if __name__ == '__main__':
    app = ApplicationBuilder().token("8013981496:AAEezFWSIxiFSNQTzTsKidkC2iOjaXzyyCk").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name))
    app.run_polling()
