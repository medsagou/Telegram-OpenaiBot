#!/usr/bin/env python
# pylint: disable=unused-argument
# This program is dedicated to the public domain under the CC0 license.

"""
First, a few callback functions are defined. Then, those functions are passed to
the Application and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Example of a bot-user conversation using nested ConversationHandlers.
Send /start to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging
from typing import Any, Dict, Tuple
import os
from dotenv import load_dotenv

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)


import whisper
import warnings


from bot.utilities import getOpenAiClient, chat

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# State definitions for top level conversation
SELECTING_ACTION, ADDING_MEMBER, ADDING_SELF, DESCRIBING_SELF = map(chr, range(4))
# State definitions for second level conversation
SELECTING_LEVEL, SELECTING_GENDER = map(chr, range(4, 6))
# State definitions for descriptions conversation
SELECTING_FEATURE, TYPING = map(chr, range(6, 8))
# Meta states
STOPPING, SHOWING = map(chr, range(8, 10))

# Question variable
SHOWING_TRANSCRIPTION_GIVE_COMMAND, \
    SHOWING_TRANSCRIPTION_EXECUTION, \
    SHOWING_TRANSCRIPTION, \
    SHOWING_TRANSCRIPTION_SUMMARY = map(chr, range(10, 14))
# Shortcut for ConversationHandler.END
END = ConversationHandler.END

# Different constants for this example
(
    PARENTS,
    CHILDREN,
    SELF,
    GENDER,
    MALE,
    FEMALE,
    AGE,
    NAME,
    START_OVER,
    FEATURES,
    CURRENT_FEATURE,
    CURRENT_LEVEL,
    QUESTION,
    TRANSCRIPTION,
) = map(chr, range(10, 24))


dataDirPath = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "data")

load_dotenv()
API_KEY = os.getenv("CHATGPT_API")
client = getOpenAiClient(API_KEY=API_KEY)
# Helper
def _name_switcher(level: str) -> Tuple[str, str]:
    if level == PARENTS:
        return "Father", "Mother"
    return "Brother", "Sister"


# Top level conversation callbacks
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Select an action: Adding parent/child or show data."""
    text = (
        "We are waiting for your Questions\n\n"
        "\t/stop - Stop the bot."
    )

    # buttons = [
    #     [
    #         InlineKeyboardButton(text="Transcription", callback_data=str(ADDING_MEMBER)),
    #         InlineKeyboardButton(text="Forward Message", callback_data=str(ADDING_MEMBER)),
    #     ],
    #     [
    #         InlineKeyboardButton(text="Transcription + summary", callback_data=str(ADDING_SELF)),
    #     ],
    #     [
    #         InlineKeyboardButton(text="Transcription + execution", callback_data=str(SHOWING)),
    #     ],
    #     [
    #         InlineKeyboardButton(text="Transcription + give command", callback_data=str(END)),
    #     ],
    # ]
    # keyboard = InlineKeyboardMarkup(buttons)

    # If we're starting over we don't need to send a new message

    if context.user_data.get(START_OVER):
        await update.callback_query.answer()
        # await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        await update.callback_query.edit_message_text(text=text)
    else:
        await update.message.reply_text(
            "How can I help you?"
        )
        # await update.message.reply_text(text=text, reply_markup=keyboard)
        await update.message.reply_text(text=text)

    context.user_data[START_OVER] = False
    return QUESTION


async def get_question_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    file = await context.bot.get_file(update.message.voice)
    file.download_to_drive(os.path.join(dataDirPath, "user_audio.ogg"))
    warnings.simplefilter("ignore")
    model = whisper.load_model("tiny")
    result = model.transcribe(audio=os.path.join(dataDirPath, "user_audio.ogg"))
    context.user_data["question"] = result["text"]
    return TRANSCRIPTION


async def get_question_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    processing_message = await context.bot.send_message(chat_id=update.effective_chat.id, text="Processing your message...")
    if not ("transcription" in context.user_data.keys()):
        message = update.message
        # Check if the last message was a text message
        if message.text:
            context.user_data["transcription"] = update.message.text
        # Check if the last message was a voice message
        elif message.voice:
            file = await context.bot.get_file(update.message.voice)
            await file.download_to_drive(os.path.join(dataDirPath, "user_audio.ogg"))
            warnings.simplefilter("ignore")
            model = whisper.load_model("tiny")
            result = model.transcribe(audio=os.path.join(dataDirPath, "user_audio.ogg"))
            context.user_data["transcription"] = result["text"]
            # print(result)
        else:
            text = "Please try to send a voice or a text question!!"
            context.bot.delete_message(message_id=processing_message.message_id)
            await update.message.reply_text(text=text)
            return QUESTION


    buttons = [
        [
            InlineKeyboardButton(text="Transcription", callback_data=str(SHOWING_TRANSCRIPTION)),
            InlineKeyboardButton(text="Forward Message", callback_data=str(SHOWING_TRANSCRIPTION_SUMMARY)),
        ],
        [
            InlineKeyboardButton(text="Transcription + summary", callback_data=str(SHOWING_TRANSCRIPTION_SUMMARY)),
        ],
        [
            InlineKeyboardButton(text="Transcription + execution", callback_data=str(SHOWING_TRANSCRIPTION_EXECUTION)),
        ],
        [
            InlineKeyboardButton(text="Transcription + give command", callback_data=str(SHOWING_TRANSCRIPTION_GIVE_COMMAND)),
        ],
        [
            InlineKeyboardButton(text="END", callback_data=str(END)),
        ],
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    text = "Got it! Please select your Choice."

    await context.bot.delete_message(chat_id=update.effective_chat.id,message_id=processing_message.message_id)
    if context.user_data.get(START_OVER):
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    else:
        await update.message.reply_text(text=text, reply_markup=keyboard)

    # await update.message.reply_text(text=text, reply_markup=keyboard)
    context.user_data[START_OVER] = False
    return SELECTING_LEVEL


async def transcription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    return TRANSCRIPTION

async def adding_self(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Add information about yourself."""
    context.user_data[CURRENT_LEVEL] = SELF
    text = "Okay, please tell me about yourself."
    button = InlineKeyboardButton(text="Add info", callback_data=str(MALE))
    keyboard = InlineKeyboardMarkup.from_button(button)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return DESCRIBING_SELF

async def show_transcription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    if context.user_data["transcription"]:
        question = "YOUR TRANSCRIPTION IS :\n\n\t" + str(context.user_data["transcription"])
    else:
        question = "YOUR TRANSCRIPTION IS :\n\n\tNo transcription yet"
    user_data = context.user_data

    buttons = [[InlineKeyboardButton(text="Back", callback_data=str(END))]]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=question, reply_markup=keyboard)
    user_data[START_OVER] = True

    return SHOWING_TRANSCRIPTION

async def show_transcription_summary(update: Update, context:ContextTypes.DEFAULT_TYPE) -> str:
    if context.user_data["transcription"]:
        question = "YOUR TRANSCRIPTION IS :\n\t" + str(context.user_data["transcription"])
        if "summary" not in context.user_data.keys():
            summary = chat(MSGS=[{"role": "user", "content": f"Please summarize the following text:\n{question}"}],
                           MaxToken=500,
                           client=client)
            context.user_data["summary"] = summary
        else:
            summary = context.user_data["summary"]

        question = f"{question}\n\nSUMMARY :\n\t{summary}"
    else:
        question = "YOUR TRANSCRIPTION IS :\n\n\tNo transcription yet"
    user_data = context.user_data

    buttons = [[InlineKeyboardButton(text="Back", callback_data=str(END))]]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=question, reply_markup=keyboard)
    user_data[START_OVER] = True
    return SHOWING_TRANSCRIPTION_SUMMARY


async def show_transcription_execution(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    text = "not working yet..."
    buttons = [[InlineKeyboardButton(text="Back", callback_data=str(END))]]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    # user_data[START_OVER] = True
    return SHOWING_TRANSCRIPTION_EXECUTION


async def show_transcription_give_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    text = "not working yet..."
    buttons = [[InlineKeyboardButton(text="Back", callback_data=str(END))]]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    # user_data[START_OVER] = True
    return SHOWING_TRANSCRIPTION_GIVE_COMMAND


async def show_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Pretty print gathered data."""
    def pretty_print(data: Dict[str, Any], level: str) -> str:
        people = data.get(level)
        if not people:
            return "\nNo information yet."

        return_str = ""
        if level == SELF:
            for person in data[level]:
                return_str += f"\nName: {person.get(NAME, '-')}, Age: {person.get(AGE, '-')}"
        else:
            male, female = _name_switcher(level)

            for person in data[level]:
                gender = female if person[GENDER] == FEMALE else male
                return_str += (
                    f"\n{gender}: Name: {person.get(NAME, '-')}, Age: {person.get(AGE, '-')}"
                )
        return return_str

    user_data = context.user_data
    text = f"Yourself:{pretty_print(user_data, SELF)}"
    text += f"\n\nParents:{pretty_print(user_data, PARENTS)}"
    text += f"\n\nChildren:{pretty_print(user_data, CHILDREN)}"

    buttons = [[InlineKeyboardButton(text="Back", callback_data=str(END))]]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    user_data[START_OVER] = True

    return SHOWING


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """End Conversation by command."""
    await update.message.reply_text("Okay, bye.")

    return END


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """End conversation from InlineKeyboardButton."""
    await update.callback_query.answer()

    text = "See you around!"
    await update.callback_query.edit_message_text(text=text)

    return END


# Second level conversation callbacks
async def select_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Choose to add a parent or a child."""
    text = "You may add a parent or a child. Also you can show the gathered data or go back."
    buttons = [
        [
            InlineKeyboardButton(text="Add parent", callback_data=str(PARENTS)),
            InlineKeyboardButton(text="Add child", callback_data=str(CHILDREN)),
        ],
        [
            InlineKeyboardButton(text="Show data", callback_data=str(SHOWING)),
            InlineKeyboardButton(text="Back", callback_data=str(END)),
        ],
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return SELECTING_LEVEL


async def select_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Choose to add mother or father."""
    level = update.callback_query.data
    context.user_data[CURRENT_LEVEL] = level

    text = "Please choose, whom to add."

    male, female = _name_switcher(level)

    buttons = [
        [
            InlineKeyboardButton(text=f"Add {male}", callback_data=str(MALE)),
            InlineKeyboardButton(text=f"Add {female}", callback_data=str(FEMALE)),
        ],
        [
            InlineKeyboardButton(text="Show data", callback_data=str(SHOWING)),
            InlineKeyboardButton(text="Back", callback_data=str(END)),
        ],
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return SELECTING_GENDER


async def end_second_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Return to top level conversation."""
    context.user_data[START_OVER] = True
    await start(update, context)

    return END


# Third level callbacks
async def select_feature(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Select a feature to update for the person."""
    buttons = [
        [
            InlineKeyboardButton(text="Name", callback_data=str(NAME)),
            InlineKeyboardButton(text="Age", callback_data=str(AGE)),
            InlineKeyboardButton(text="Done", callback_data=str(END)),
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    # If we collect features for a new person, clear the cache and save the gender
    if not context.user_data.get(START_OVER):
        context.user_data[FEATURES] = {GENDER: update.callback_query.data}
        text = "Please select a feature to update."

        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    # But after we do that, we need to send a new message
    else:
        text = "Got it! Please select a feature to update."
        await update.message.reply_text(text=text, reply_markup=keyboard)

    context.user_data[START_OVER] = False
    return SELECTING_FEATURE


async def ask_for_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Prompt user to input data for selected feature."""
    context.user_data[CURRENT_FEATURE] = update.callback_query.data
    text = "Okay, tell me."

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text)

    return TYPING


async def save_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Save input for feature and return to feature selection."""
    user_data = context.user_data
    user_data[FEATURES][user_data[CURRENT_FEATURE]] = update.message.text

    user_data[START_OVER] = True

    return await select_feature(update, context)


async def end_describing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """End gathering of features and return to parent conversation."""
    user_data = context.user_data
    level = user_data[CURRENT_LEVEL]
    if not user_data.get(level):
        user_data[level] = []
    user_data[level].append(user_data[FEATURES])

    # Print upper level menu
    if level == SELF:
        user_data[START_OVER] = True
        await start(update, context)
    else:
        await select_level(update, context)

    return END


async def stop_nested(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Completely end conversation from within nested conversation."""
    await update.message.reply_text("Okay, bye.")

    return STOPPING


description_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(
            select_feature, pattern="^" + str(MALE) + "$|^" + str(FEMALE) + "$"
        )
    ],
    states={
        SELECTING_FEATURE: [
            CallbackQueryHandler(ask_for_input, pattern="^(?!" + str(END) + ").*$")
        ],
        TYPING: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_input)],
    },
    fallbacks=[
        CallbackQueryHandler(end_describing, pattern="^" + str(END) + "$"),
        CommandHandler("stop", stop_nested),
    ],
    map_to_parent={
        # Return to second level menu
        END: SELECTING_LEVEL,
        # End conversation altogether
        STOPPING: STOPPING,
    },
)

# Set up second level ConversationHandler (adding a person)
add_member_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(select_level, pattern="^" + str(ADDING_MEMBER) + "$")],
    states={
        SELECTING_LEVEL: [
            CallbackQueryHandler(select_gender, pattern=f"^{PARENTS}$|^{CHILDREN}$")
        ],
        SELECTING_GENDER: [description_conv],
    },
    fallbacks=[
        CallbackQueryHandler(show_data, pattern="^" + str(SHOWING) + "$"),
        CallbackQueryHandler(end_second_level, pattern="^" + str(END) + "$"),
        CommandHandler("stop", stop_nested),
    ],
    map_to_parent={
        # After showing data return to top level menu
        SHOWING: SHOWING,
        SHOWING_TRANSCRIPTION: SHOWING_TRANSCRIPTION,
        # Return to top level menu
        END: SELECTING_ACTION,
        # End conversation altogether
        STOPPING: END,
    },
)

# Set up top level ConversationHandler (selecting action)
# Because the states of the third level conversation map to the ones of the second level
# conversation, we need to make sure the top level conversation can also handle them
selection_handlers = [
    add_member_conv,
    CallbackQueryHandler(show_data, pattern="^" + str(SHOWING) + "$"),
    CallbackQueryHandler(show_transcription, pattern="^" + str(SHOWING_TRANSCRIPTION) + "$"),
    CallbackQueryHandler(show_transcription_summary, pattern="^" + str(SHOWING_TRANSCRIPTION_SUMMARY) + "$"),
    CallbackQueryHandler(show_transcription_execution, pattern="^" + str(SHOWING_TRANSCRIPTION_EXECUTION) + "$"),
    CallbackQueryHandler(show_transcription_give_command, pattern="^" + str(SHOWING_TRANSCRIPTION_GIVE_COMMAND) + "$"),
    CallbackQueryHandler(adding_self, pattern="^" + str(ADDING_SELF) + "$"),
    CallbackQueryHandler(end, pattern="^" + str(END) + "$"),
]
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("question", start)],
    states={
        SHOWING: [CallbackQueryHandler(start, pattern="^" + str(END) + "$")],
        SHOWING_TRANSCRIPTION: [CallbackQueryHandler(get_question_text, pattern="^" + str(END) + "$")],
        SHOWING_TRANSCRIPTION_SUMMARY: [CallbackQueryHandler(get_question_text, pattern="^" + str(END) + "$")],
        SHOWING_TRANSCRIPTION_EXECUTION: [CallbackQueryHandler(get_question_text, pattern="^" + str(END) + "$")],
        SHOWING_TRANSCRIPTION_GIVE_COMMAND: [CallbackQueryHandler(get_question_text, pattern="^" + str(END) + "$")],
        SELECTING_ACTION: selection_handlers,
        SELECTING_LEVEL: selection_handlers,
        DESCRIBING_SELF: [description_conv],
        # TRANSCRIPTION: [MessageHandler(transcription)],
        QUESTION: [MessageHandler(filters.ALL, get_question_text)],
        STOPPING: [CommandHandler("question", start)],
    },
    fallbacks=[CommandHandler("stop", stop)],
)





















#
# def main() -> None:
#     """Run the bot."""
#     # Create the Application and pass it your bot's token.
#     application = Application.builder().token("6893087151:AAFhmCki7C9pVv03epxMiH_wFNEwcYtoXaQ").build()
#
#     # Set up third level ConversationHandler (collecting features)
#     description_conv = ConversationHandler(
#         entry_points=[
#             CallbackQueryHandler(
#                 select_feature, pattern="^" + str(MALE) + "$|^" + str(FEMALE) + "$"
#             )
#         ],
#         states={
#             SELECTING_FEATURE: [
#                 CallbackQueryHandler(ask_for_input, pattern="^(?!" + str(END) + ").*$")
#             ],
#             TYPING: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_input)],
#         },
#         fallbacks=[
#             CallbackQueryHandler(end_describing, pattern="^" + str(END) + "$"),
#             CommandHandler("stop", stop_nested),
#         ],
#         map_to_parent={
#             # Return to second level menu
#             END: SELECTING_LEVEL,
#             # End conversation altogether
#             STOPPING: STOPPING,
#         },
#     )
#
#     # Set up second level ConversationHandler (adding a person)
#     add_member_conv = ConversationHandler(
#         entry_points=[CallbackQueryHandler(select_level, pattern="^" + str(ADDING_MEMBER) + "$")],
#         states={
#             SELECTING_LEVEL: [
#                 CallbackQueryHandler(select_gender, pattern=f"^{PARENTS}$|^{CHILDREN}$")
#             ],
#             SELECTING_GENDER: [description_conv],
#         },
#         fallbacks=[
#             CallbackQueryHandler(show_data, pattern="^" + str(SHOWING) + "$"),
#             CallbackQueryHandler(end_second_level, pattern="^" + str(END) + "$"),
#             CommandHandler("stop", stop_nested),
#         ],
#         map_to_parent={
#             # After showing data return to top level menu
#             SHOWING: SHOWING,
#             # Return to top level menu
#             END: SELECTING_ACTION,
#             # End conversation altogether
#             STOPPING: END,
#         },
#     )
#
#     # Set up top level ConversationHandler (selecting action)
#     # Because the states of the third level conversation map to the ones of the second level
#     # conversation, we need to make sure the top level conversation can also handle them
#     selection_handlers = [
#         add_member_conv,
#         CallbackQueryHandler(show_data, pattern="^" + str(SHOWING) + "$"),
#         CallbackQueryHandler(adding_self, pattern="^" + str(ADDING_SELF) + "$"),
#         CallbackQueryHandler(end, pattern="^" + str(END) + "$"),
#     ]
#     conv_handler = ConversationHandler(
#         entry_points=[CommandHandler("question", start)],
#         states={
#             SHOWING: [CallbackQueryHandler(start, pattern="^" + str(END) + "$")],
#             SELECTING_ACTION: selection_handlers,
#             SELECTING_LEVEL: selection_handlers,
#             DESCRIBING_SELF: [description_conv],
#             STOPPING: [CommandHandler("question", start)],
#         },
#         fallbacks=[CommandHandler("stop", stop)],
#     )
#
#     application.add_handler(conv_handler)
#
#     # Run the bot until the user presses Ctrl-C
#     application.run_polling(allowed_updates=Update.ALL_TYPES)
