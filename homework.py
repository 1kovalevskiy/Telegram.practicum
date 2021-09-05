import os
import time
import requests
import telegram
from dotenv import load_dotenv
import logging


load_dotenv()

PRAKTIKUM_TOKEN = os.getenv('PRAKTIKUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

bot = telegram.Bot(token=TELEGRAM_TOKEN)

_log_format = '%(asctime)s, %(levelname)s, %(name)s, %(message)s'


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
    stream_handler = TelegramLoggingHandler()
    stream_handler.setLevel(logging.ERROR)
    stream_handler.setFormatter(logging.Formatter(_log_format))
    return stream_handler


def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(get_file_handler())
    logger.addHandler(get_stream_handler())
    return logger


logger = get_logger(__name__)


def parse_homework_status(homework):
    homework_name = homework['homework_name']
    if homework['status'] == 'rejected':
        logger.info('Домашку нужно доделать')
        verdict = 'К сожалению, в работе нашлись ошибки.'
    elif homework['status'] == 'reviewing':
        logger.info('Домашку начали проверять')
        return f'Домашка {homework_name} взята в работу'
    else:
        logger.info('С домашкой все ОК')
        verdict = 'Ревьюеру всё понравилось, работа зачтена!'
    return f'У вас проверили работу "{homework_name}"!\n\n{verdict}'


def get_homeworks(current_timestamp=1581604970):
    url = 'https://praktikum.yandex.ru/api/user_api/homework_statuses/'
    headers = {'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'}
    payload = {'from_date': current_timestamp}
    homework_statuses = requests.get(url, headers=headers, params=payload)
    logger.info('Информация о домашке получена')
    return homework_statuses.json()


def send_message(message):
    return bot.send_message(CHAT_ID, message)


def main():
    current_timestamp = int(time.time())  # noqa
    last_homework = None

    while True:
        try:
            homeworks = get_homeworks(current_timestamp)
            logger.info('Список домашек получен')
            if homeworks.get('homeworks') == []:
                logger.info('нету домашних работ')
                time.sleep(5 * 60)
                continue
            else:
                homework = homeworks['homeworks'][0]
            if homework != last_homework:
                logger.info('Статус изменился')
                last_homework = homework
                verdict = parse_homework_status(homework)
                response = send_message(verdict)
                logger.info(response)
            time.sleep(20 * 60)

        except Exception as e:
            logger.error(f'Бот упал с ошибкой: {e}')
            time.sleep(5 * 60)


if __name__ == '__main__':
    main()
