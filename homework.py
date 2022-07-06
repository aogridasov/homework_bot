import logging
import os
import requests
import sys
import telegram
import time

from dotenv import load_dotenv

import exceptions


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 20
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    level=logging.INFO
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
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        raise exceptions.ApiIsNotRespondingException(
            'Ошибка подключения. Проблемы с доступом к API Яндекса.'
        )
    print(response.json())
    return response.json()


def check_response(response):
    """Проверяет корректность ответа API."""
    if (not isinstance(response['homeworks'], list)
            or (
                response['homeworks']
                and not isinstance(response['homeworks'][0], dict)
    )
    ):
        raise exceptions.ApiAnswerIsIncorrectException(
            'API прислал нетипичный ответ. Структура ответа некорректна.'
        )

    homework = response['homeworks'][0]
    homework_name = 'lesson_name'
    homework_status = 'status'
    if not (homework_name or homework_status in homework.keys()):
        raise exceptions.ApiAnswerIsIncorrectException(
            ('API прислал нетипичный ответ.'
             'Не найдено название домашки или её статус.')
        )

    return homework


def parse_status(homework):
    """
    Извлекает статус из ответа API статус конкретной дз.
    Формирует сообщение о статусе дз для отправки в ТГ.
    """
    print(homework)
    homework_name = homework['lesson_name']
    print(homework_name)
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """
    Проверяет доступность элементов окружения.
    3 из 3 доступны - возвращает True, else - возвращает False.
    """
    if all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)):
        return True
    return False


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
            logger.debug(
                f'Обновлений нет. API прислал пустой словарь: {error}'
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
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
