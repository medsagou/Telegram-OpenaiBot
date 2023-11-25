
import asyncio
import time

from dotenv import load_dotenv
import os

from pydub import AudioSegment
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackContext
import speech_recognition as sr

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
dataDirPath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")



logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print('here2')
    await context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)

async def audio(update: Update, context: CallbackContext) -> None:
    file = await context.bot.get_file(update.message.voice)
    await file.download_to_drive(os.path.join(dataDirPath,"user_audio.ogg"))
    ogg_audio = AudioSegment.from_file(os.path.join(dataDirPath,"user_audio.ogg"), format="ogg")
    ogg_audio.export(os.path.join(dataDirPath,"user_audio.wav"), format='wav')
    r = sr.Recognizer()
    with sr.AudioFile(os.path.join(dataDirPath,"user_audio.wav")) as source:
        audio_data = r.record(source)
        text = r.recognize_google(audio_data,language="ar-AR")
    await update.message.reply_text(text)


if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()

    start_handler = CommandHandler('start', start)
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)
    audio_handler = MessageHandler(filters.VOICE & ~filters.COMMAND, audio)

    application.add_handler(start_handler)
    application.add_handler(echo_handler)
    application.add_handler(audio_handler)

    application.run_polling()