import os
import logging
from time import sleep

from dotenv import load_dotenv
from google.cloud import dialogflow
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext, Filters


logger = logging.getLogger(__name__)


class TelegramLogHandler(logging.Handler):
    def __init__(self, bot, chat_id):
        super().__init__()
        self.bot = bot
        self.chat_id = chat_id

    def emit(self, record):
        log_entry = self.format(record)
        try:
            self.bot.send_message(chat_id=self.chat_id, text=log_entry)
        except Exception as e:
            print(f"Бот упал с ошибкой: {e}")


def detect_intent_texts(project_id, session_id, text, language_code):
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, session_id)
    text_input = dialogflow.TextInput(text=text, language_code=language_code)
    query_input = dialogflow.QueryInput(text=text_input)
    response = session_client.detect_intent(
        request={"session": session, "query_input": query_input}
    )
    logger.info(f"Вопрос принят: {response.query_result.intent.display_name}")

    return response


def handle_messages(update: Update, context: CallbackContext, project_id: str) -> None:
    session_id = f"tg-{update.message.chat_id}"
    text = update.message.text
    language_code = "ru"
    user = update.message.from_user
    response = detect_intent_texts(project_id, session_id, text, language_code)
    if not response.query_result.intent.is_fallback:
        update.message.reply_text(response.query_result.fulfillment_text)
        logger.info(
            f"Отправлен ответ пользователю: {user}:\n{response.query_result.fulfillment_text}")


def start_bot(tg_bot_token: str, admin_chat_id: str, project_id: str):
    updater = Updater(tg_bot_token, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('start', lambda update,
                   context: handle_messages(update, context, project_id)))
    dp.add_handler(MessageHandler(
        Filters.text & (~Filters.command), lambda update, context: handle_messages(update, context, project_id)))
    telegram_handler = TelegramLogHandler(updater.bot, admin_chat_id)
    telegram_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    telegram_handler.setFormatter(formatter)
    logger.addHandler(telegram_handler)
    logger.info("Бот начинается")
    updater.start_polling()

    try:
        updater.idle()
    except Exception as e:
        logger.error(f"Бот упал: {e}")
        raise


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    load_dotenv()

    tg_bot_token = os.environ.get('TG_BOT_TOKEN')
    admin_chat_id = os.environ.get('ADMIN_CHAT_ID_TG')
    project_id = os.environ.get('PROJECT_ID')

    if not tg_bot_token:
        logger.error(
            "TG_BOT_TOKEN не найден. Пожалуйста, добавьте TG_BOT_TOKEN в .env")
        return
    if not admin_chat_id:
        logger.error(
            "ADMIN_CHAT_ID_TG не найден. Пожалуйста, добавьте ADMIN_CHAT_ID_TG в .env")
        return
    if not project_id:
        logger.error(
            "PROJECT_ID не найден. Пожалуйста, добавьте PROJECT_ID в .env")
        return

    while True:
        try:
            start_bot(tg_bot_token, admin_chat_id, project_id)
        except Exception as e:
            logger.error(f"Ошибка в работе бота: {e}")
            sleep(5)
            continue


if __name__ == "__main__":
    main()
