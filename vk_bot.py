import os
import random
import logging
from time import sleep

import vk_api as vk
from vk_api.longpoll import VkLongPoll, VkEventType
from dotenv import load_dotenv
from google.cloud import dialogflow


logger = logging.getLogger(__name__)


class VkLogHandler(logging.Handler):
    def __init__(self, vk_api, chat_id):
        super().__init__()
        self.vk_api = vk_api
        self.chat_id = chat_id

    def emit(self, record):
        log_entry = self.format(record)
        try:
            self.vk_api.messages.send(
                user_id=self.chat_id,
                message=log_entry,
                random_id=random.randint(1, 10000)
            )
        except Exception as e:
            print(f"Ошибка с отправкой сообщения: {e}")


def detect_intent_texts(project_id, session_id, text, language_code):
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, session_id)
    text_input = dialogflow.TextInput(text=text, language_code=language_code)
    query_input = dialogflow.QueryInput(text=text_input)

    response = session_client.detect_intent(
        request={'session': session, 'query_input': query_input}
    )
    return response


def handle_messages(event, vk_api, project_id: str):
    session_id = f"vk-{event.user_id}"
    text = event.text
    language_code = 'ru'
    response = detect_intent_texts(project_id, session_id, text, language_code)
    if not response.query_result.intent.is_fallback:
        vk_api.messages.send(
            user_id=event.user_id,
            message=response.query_result.fulfillment_text,
            random_id=random.randint(1, 10000)
        )
        logger.info(
            f"Отправлен ответ пользователю {session_id}: '{response.query_result.fulfillment_text}'"
        )
    else:
        logger.info("Ответ не отправлен (обнаружен fallback intent)")


def start_bot(vk_bot_token: str, admin_chat_id: str, project_id: str):
    vk_session = vk.VkApi(token=vk_bot_token)
    vk_api = vk_session.get_api()
    logger.info(f"Бот активирован с токеном: {vk_bot_token[:5]}...")
    if admin_chat_id:
        vk_handler = VkLogHandler(vk_api, admin_chat_id)
        vk_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s')
        vk_handler.setFormatter(formatter)
        logger.addHandler(vk_handler)
        logger.info(f"Логи будут отправляться в VK чат: {admin_chat_id}")
    else:
        logger.info("ADMIN_CHAT_ID не указан, логи будут только в консоли")

    longpoll = VkLongPoll(vk_session)
    logger.info("Начинаю слушать события...")

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            logger.info(f"Получен запрос от {event.user_id}: '{event.text}'")
            try:
                handle_messages(event, vk_api, project_id)
            except Exception as e:
                logger.error(f"Ошибка при обработке сообщения: {str(e)}")


def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    load_dotenv()

    vk_bot_token = os.environ.get('VK_BOT_TOKEN')
    admin_chat_id = os.environ.get('ADMIN_CHAT_ID_VK')
    project_id = os.environ.get('PROJECT_ID')

    if not vk_bot_token:
        logger.error(
            "VK_BOT_TOKEN не найден. Пожалуйста, добавьте VK_BOT_TOKEN в .env")
        return
    if not project_id:
        logger.error(
            "PROJECT_ID не найден. Пожалуйста, добавьте PROJECT_ID в .env")
        return

    while True:
        try:
            start_bot(vk_bot_token, admin_chat_id, project_id)
        except Exception as e:
            logger.error(f"Произошла ошибка: {e}")
            sleep(5)
            continue


if __name__ == "__main__":
    main()
