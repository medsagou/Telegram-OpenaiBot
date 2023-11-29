from telegram.ext import ContextTypes
from telegram import Update
from config import menu_message

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await context.bot.send_message(chat_id=update.effective_chat.id, text=menu_message)
