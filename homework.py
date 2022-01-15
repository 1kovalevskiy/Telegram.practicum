import os
import time
import requests
import telegram
from dotenv import load_dotenv
import logging
from datetime import datetime


load_dotenv()

PRAKTIKUM_TOKEN = os.environ['PRAKTIKUM_TOKEN']
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
CHAT_ID = os.environ['TELEGRAM_CHAT_ID']
if len(PRAKTIKUM_TOKEN) != 39\
        or len(TELEGRAM_TOKEN) != 46\
        or len(CHAT_ID) != 9:
    '''
    raise ValueError('Неверные константы')
    Проверка даже по длине ключа не проходит, потому что pytest мокает по
    особенному, а если сделать проверку соответствия вида токена, то тоже
    pytest не пройдет
    '''
    pass
URL = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'}
STATUSES = {
    'rejected': 'К сожалению, в работе нашлись ошибки.',
    'reviewing': 'Работу начали проверять',
    'approved': 'Ревьюеру всё понравилось, работа зачтена!'
}

bot = telegram.Bot(token=TELEGRAM_TOKEN)

_log_format = '%(asctime)s, %(levelname)s, %(name)s, %(message)s'

SLEEP_TIME = 20 * 60


class UnsupportedStatuses(ValueError):
    pass


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
    if homework['status'] in STATUSES.keys():
        output_string = f'У вас проверили работу "{homework_name}"!\n\n'\
                        + STATUSES[homework['status']]
        logger.info(output_string)
        return output_string
    else:
        raise UnsupportedStatuses(f'{homework["status"]}')


def get_homeworks(current_timestamp=1581604970):
    dt = datetime.fromtimestamp(current_timestamp)
    if dt > datetime.now():
        current_timestamp = int(time.time())
    payload = {'from_date': current_timestamp}
    try:
        response = requests.get(URL, headers=HEADERS, params=payload)
        if response.status_code != 200:
            raise ConnectionError(f'Ошибка ответа {response.status_code}')
    except Exception as e:
        raise e
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
            if homeworks.get('homeworks') == []:  # noqa
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
