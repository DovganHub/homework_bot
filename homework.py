import logging
import os
import telegram
import time
import requests
from dotenv import load_dotenv
from http import HTTPStatus

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(
    logging.StreamHandler()
)
load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = 251755913
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена, в ней нашлись ошибки.'
}


class CustomError(Exception):
    """кастомная ошибка на все случаи жизни."""

    pass


def send_message(bot, message):
    """сообщение направляется в телеграм."""
    try:
        bot.send_message(CHAT_ID, message)
        logger.info(
            f'Сообщение в Telegram отправлено: {message}')
    except telegram.TelegramError as error_desc:
        logger.error(
            f'Сообщение в Telegram не отправлено: {error_desc}')


def get_api_answer(url, current_timestamp):
    """отправляет запрос к яндекс апи, в случае ошибок пишет в логер."""
    from_time = current_timestamp
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    payload = {'from_date': from_time}

    try:
        response = requests.get(url, headers=headers, params=payload)
        if response.status_code != HTTPStatus.OK:
            logging.error(
                f'Endpoint is unavailable. API status: {response.status_code}')
            raise CustomError(response.status_code)
        return response.json()
    except Exception as error_desc:
        logging.error(error_desc)
        raise CustomError(response.status_code)


def parse_status(homework):
    """извлекает из ответа апи требуемые значения, документирует ошикби."""
    status = homework.get('status')
    homework_name = homework.get('homework_name')
    verdict = HOMEWORK_STATUSES[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_response(response):
    """проверка, содержится ли в ответе новый статус."""
    homeworks = response.get('homeworks')
    if len(homeworks) == 0:
        error_desc = 'Empty answer!'
        logger.error(error_desc)
        raise CustomError(error_desc)
    elif homeworks is None:
        error_desc = ('Missing "homeworks" key!')
        logger.error(error_desc)
        raise CustomError(error_desc)
    homework_name = homeworks[0].get('homework_name')
    if homework_name is None:
        error_desc = f'Error! "homework_name" is empty: {homework_name}'
        logger.error(error_desc)
        raise CustomError(error_desc)
    status = homeworks[0].get('status')
    if status not in HOMEWORK_STATUSES:
        error_desc = f'Error. Unknown status key: {status}'
        logger.error(error_desc)
        raise CustomError(error_desc)
    elif status is None:
        error_desc = f'Error! "status" is empty: {status}'
        logger.error(error_desc)
        raise CustomError(error_desc)
    return homeworks[0]


def check_tokens():
    """проверка присутствия обязательных переменных окружения."""
    for token in [PRACTICUM_TOKEN, TELEGRAM_TOKEN, CHAT_ID]:
        if token is None:
            logger.critical(
                f'Operation will be terminated: {token} is missing.')
            exit()


def main():
    """инициализируем бота, запускаем рабочий цикл."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    error_flag = True
    while True:
        try:
            response = get_api_answer(ENDPOINT, current_timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework)
                send_message(bot, message)
            logger.info('На фронте без перемен')
            time.sleep(RETRY_TIME)
            current_timestamp = int(time.time())
        except Exception as error:
            error_desc = f'Сбой в работе программы: {error}'
            if error_flag:
                error_flag = False
                send_message(bot, error_desc)
            logging.error(error_desc)
            time.sleep(RETRY_TIME)
            current_timestamp = int(time.time())
            continue


if __name__ == '__main__':
    main()
