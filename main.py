from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext
from dotenv import load_dotenv
import os

load_dotenv()

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Hi! I am your ChatGPT-powered bot. Send me a message.')


def reply_message(update: Update, context: CallbackContext) -> None:
    user_input = update.message.text
    response = "this is a text response"
    update.message.reply_text(response)


def main() -> None:
    # Set up the Telegram bot
    # updater = Updater(os.getenv("TELEGRAM_TOKEN")
    dispatcher = updater.dispatcher

    # Handlers for commands and messages
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, reply_message))

    # Start the bot
    updater.start_polling()
    updater.idle()

# if __name__ == '__main__':
#     main()
print(os.getenv("TELEGRAM_TOKEN"))