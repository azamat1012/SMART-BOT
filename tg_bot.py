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
    from google.cloud import dialogflow
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, session_id)
    text_input = dialogflow.TextInput(text=text, language_code=language_code)
    query_input = dialogflow.QueryInput(text=text_input)
    response = session_client.detect_intent(
        request={"session": session, "query_input": query_input}
    )
    logger.info(f"Вопрос принят: {response.query_result.intent.display_name}")

    return response


def handle_messages(update: Update, context: CallbackContext) -> None:
    project_id = os.environ['PROJECT_ID']
    if not project_id:
        logger.error(
            "PROJECT_ID не был найден. Пожалуйста, напишите PROJECT_ID в .env")
    session_id = str(update.message.chat_id)
    text = update.message.text
    language_code = "ru"
    user = update.message.from_user
    try:
        response = detect_intent_texts(
            project_id, session_id, text, language_code)
        if not response.query_result.intent.is_fallback:
            update.message.reply_text(response.query_result.fulfillment_text)
            logger.info(
                f"Отправлен ответ пользователю: {user}:\n{response.query_result.fulfillment_text}")
    except Exception as e:
        logger.error(f"Ошибка при обработке вопроса: {str(e)}")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    load_dotenv()
    tg_bot_token = os.environ['TG_BOT_TOKEN']
    admin_chat_id = os.getenv('ADMIN_CHAT_ID_TG')
    while True:
        try:
            updater = Updater(tg_bot_token)
            dp = updater.dispatcher
            dp.add_handler(CommandHandler('start', handle_messages))
            dp.add_handler(MessageHandler(
                Filters.text & (~Filters.command), handle_messages
            ))
            telegram_handler = TelegramLogHandler(updater.bot, admin_chat_id)
            telegram_handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s')
            telegram_handler.setFormatter(formatter)
            logger.addHandler(telegram_handler)
            logger.info("Бот начинается")
            updater.start_polling()
            updater.idle()
        except Exception as e:
            logger.error(f"Бот упал: {e}")
            sleep(5)
            continue


if __name__ == "__main__":
    main()
