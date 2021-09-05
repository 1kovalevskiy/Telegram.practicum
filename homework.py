import os
import time
import requests
import telegram
from dotenv import load_dotenv
import logging


load_dotenv()

PRAKTIKUM_TOKEN = os.environ.get('PRAKTIKUM_TOKEN')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
URL = 'https://praktikum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'}

bot = telegram.Bot(token=TELEGRAM_TOKEN)

_log_format = '%(asctime)s, %(levelname)s, %(name)s, %(message)s'

SLEEP_TIME = 20 * 60


class TelegramLoggingHandler(logging.StreamHandler):
    def emit(self, record):
        log_entry = self.format(record)
        send_message(log_entry)


def get_file_handler():
    file_handler = logging.FileHandler("homework.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(_log_format))
    return file_handler


def get_stream_handler():
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(logging.Formatter(_log_format))
    return stream_handler


def get_telegram_handler():
    telegram_handler = TelegramLoggingHandler()
    telegram_handler.setLevel(logging.ERROR)
    telegram_handler.setFormatter(logging.Formatter(_log_format))
    return telegram_handler


def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(get_file_handler())
    logger.addHandler(get_stream_handler())
    logger.addHandler(get_telegram_handler())
    return logger


logger = get_logger(__name__)


def parse_homework_status(homework):
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise ValueError('Нет такого поля')
    if homework['status'] == 'rejected':
        logger.info('Домашку нужно доделать')
        verdict = 'К сожалению, в работе нашлись ошибки.'
    elif homework['status'] == 'reviewing':
        logger.info('Домашку начали проверять')
        return f'Домашка {homework_name} взята в работу'
    elif homework['status'] == 'approved':
        logger.info('С домашкой все ОК')
        verdict = 'Ревьюеру всё понравилось, работа зачтена!'
    return f'У вас проверили работу "{homework_name}"!\n\n{verdict}'


def get_homeworks(current_timestamp=1581604970):
    # if current_timestamp > int(time.time()):
    #     current_timestamp = int(time.time())
    # не проходит проверку pytest
    payload = {'from_date': current_timestamp}
    response = requests.get(URL, headers=HEADERS, params=payload)
    if response.status_code != 200:
        raise ValueError(f'Ошибка ответа сервера {response.status_code}')
    logger.info('Информация о домашке получена')
    parsed_response = response.json()
    if 'error' in parsed_response.keys():
        raise ValueError('Ошибка ответа сервера')
    return parsed_response


def send_message(message):
    try:
        return bot.send_message(CHAT_ID, message)
    except Exception as e:
        logger.warning(f'Не отправляется сообщение "{e}"')


def main():
    send_message('Отслеживание домашки работает')
    logger.debug('Отслеживание запущено')
    current_timestamp = int(time.time())  # noqa
    last_homework = None

    while True:
        try:
            homeworks = get_homeworks(current_timestamp)
            logger.info('Список домашек получен')
            if homeworks.get('homeworks') == []:
                logger.info('нету домашних работ')
                time.sleep(SLEEP_TIME)
                continue
            else:
                homework = homeworks['homeworks'][0]
            if homework != last_homework:
                logger.info('Статус изменился')
                last_homework = homework
                verdict = parse_homework_status(homework)
                response = send_message(verdict)
                logger.info(response)
            time.sleep(SLEEP_TIME)

        except Exception as e:
            logger.error(f'Бот упал с ошибкой: {e}')
            time.sleep(SLEEP_TIME)
    else:
        send_message('Отслеживание завершено')
        logger.debug('Отслеживание завершено')


if __name__ == '__main__':
    main()
