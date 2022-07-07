import logging
import os
import requests
import sys
import telegram
import time

from http import HTTPStatus
from dotenv import load_dotenv

import exceptions
import settings


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


logging.basicConfig(
    level=logging.DEBUG
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)

formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)
handler.setFormatter(formatter)


def send_message(bot, message):
    """Отправляет сообщение в Telegram-чат."""
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)


def get_api_answer(current_timestamp):
    """
    Делает запрос к API YandexДомашки.
    Приводит его к Python-читаемому формату.
    """
    timestamp = current_timestamp or round(int(time.time()))
    params = {'from_date': timestamp}
    response = requests.get(settings.ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != HTTPStatus.OK:
        raise exceptions.ApiIsNotRespondingError(
            'Ошибка подключения. Проблемы с доступом к API Яндекса.'
        )
    return response.json()


def check_response(response):
    """Проверяет корректность ответа API."""
    if isinstance(response, list) and isinstance(response[0], dict):
        response = response[0]

    if 'homeworks' not in response:
        raise exceptions.ApiAnswerIsIncorrectError(
            'API прислал нетипичный ответ. Структура ответа некорректна.'
        )

    if (
        response['homeworks']
        and not isinstance(response['homeworks'][0], dict)
    ) or not isinstance(response['homeworks'], list):
        raise exceptions.ApiAnswerIsIncorrectError(
            'API прислал нетипичный ответ. Структура ответа некорректна.'
        )

    homeworks = response['homeworks']
    if homeworks:
        homework = homeworks[0]
    else:
        raise IndexError(f'{homeworks}')

    return homework


def parse_status(homework):
    """
    Извлекает из ответа API статус конкретной дз.
    Формирует сообщение о статусе дз для отправки в ТГ.
    """
    homework_name_key = 'homework_name'
    status_key = 'status'

    if (
        isinstance(homework, dict)
            and (homework_name_key and status_key in homework.keys())):
        homework_name = homework[homework_name_key]
        homework_status = homework[status_key]

        if homework_status in settings.HOMEWORK_STATUSES:
            verdict = settings.HOMEWORK_STATUSES[homework_status]
        else:
            raise exceptions.HomeworkStatusIsInvalidError(
                'Нетипичный статус проверки домашней работы.'
            )

        return (
            f'Изменился статус проверки работы "{homework_name}". {verdict}'
        )

    raise KeyError(
        'В ответе отсутствуют название и/или статус работы.'
    )


def check_tokens():
    """
    Проверяет доступность элементов окружения.
    3 из 3 доступны - возвращает True, else - возвращает False.
    """
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Основная логика работы бота."""
    ERROR_MESSAGES = []

    if not check_tokens():
        logger.critical(
            'Отсутствует как минимум один токен. Закрываем бота.'
        )
        exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = round(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            message = parse_status(homework)
        except IndexError as error:
            logger.info(
                f'Обновлений нет. API прислал пустой список: {error}'
            )
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message not in ERROR_MESSAGES:
                send_message(bot, message)
                ERROR_MESSAGES.append(message)
        else:
            try:
                send_message(bot, message)
                logger.info(
                    f'Бот отправил следующее сообщение в чат: {message}'
                )
            except telegram.TelegramError as error:
                logger.error(f' Сбой при отправке сообщения: {error}')
        finally:
            current_timestamp = round(time.time())
            time.sleep(settings.RETRY_TIME)


if __name__ == '__main__':
    main()
