import os
import sys
import time
import logging
from http import HTTPStatus

import requests
import telegram
from telegram.error import TelegramError
from requests import HTTPError
from dotenv import load_dotenv

from exceptions import EmptyResponseFromAPI, EnvironmentVariableError


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


formatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(funcName)s %(lineno)d %(message)s'
)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
file_handler = logging.FileHandler(__file__ + '.log', encoding='utf-8')
file_handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(stream_handler)
logger.addHandler(file_handler)


def check_tokens():
    """
    Ensure the presence and non-emptiness of required environment variables.

    Raises:
        - EnvironmentVariableError:
            If any required variable is not found or is empty.
    """
    required_tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }

    has_all_tokens = True

    for key, value in required_tokens.items():
        if not value:
            logger.critical(f'Token not found: {key}')
            has_all_tokens = False

    if not has_all_tokens:
        raise EnvironmentVariableError(
            'Tokens not found or have an empty values in program environment.'
        )


def send_message(bot, message):
    """Sends a message using the Telegram bot to the specified chat."""
    try:
        logger.debug(f'Start trying to send message: {message}')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Successful message sending: {message}')
        return True
    except TelegramError as error:
        logger.error(f'Error sending the message: {error}')
        return False


def get_api_answer(timestamp):
    """
    Sends a GET request to the API endpoint with the given timestamp.
    Returns parsed API response.

    Raises:
        - HTTPError:
            If the API returns a status code other than 200.
    """
    request_data = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp},
    }

    logger.debug(
        'Start an API request: '
        'url: {url}, '
        'headers: {headers}, '
        'params: {params}'.format(**request_data)
    )

    try:
        response = requests.get(**request_data)
    except Exception as error:
        raise ConnectionError(
            f'{error}. Request_data: '
            'url: {url}, '
            'headers: {headers}, '
            'params: {params}'.format(**request_data)
        )

    if response.status_code != HTTPStatus.OK:
        raise HTTPError(
            f'Invalid request status. '
            f'Status code: {response.status_code}, '
            f'reason: {response.reason},'
            f'text: {response.text}.'
        )

    logger.debug(
        'Successful an API request: '
        'url: {url}, '
        'headers: {headers}, '
        'params: {params}'.format(**request_data)
    )

    return response.json()


def check_response(response):
    """
    Checks the validity of the API response.

    Raises:
        - EmptyResponseFromAPI: If required key (homeworks) are not found.
        - TypeError:
            If the response or its 'homeworks' key is not of the expected type.
    """
    if not isinstance(response, dict):
        raise TypeError('The type of response is not a dict.')

    if 'homeworks' not in response:
        raise EmptyResponseFromAPI(
            'Invalid API response: key "homeworks" not found.'
        )

    homeworks = response.get('homeworks')

    if not isinstance(homeworks, list):
        raise TypeError('The value for key "homeworks" is not a list.')

    return homeworks


def parse_status(homework):
    """
    Parses the status of a homework submission.
    If successful - returns a status change message.

    Raises:
        - ValueError:
            If the 'status' key is not a valid key in HOMEWORK_VERDICTS.
    """
    homework_name = homework.get('homework_name')
    status = homework.get('status')

    if not homework_name:
        raise ValueError('Invalid value homework_name.')

    if status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Invalid status of homework: {status}')

    return (
        'Изменился статус проверки работы '
        f'"{homework_name}". {HOMEWORK_VERDICTS[status]}'
    )


def main():
    """The main logic of the bot."""
    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0
    messages = {
        'new': '',
        'last': '',
    }

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)

            if homeworks:
                homework = homeworks[0]
                messages['new'] = parse_status(homework)
            else:
                messages['new'] = 'No new status of homework.'

            if messages['new'] != messages['last']:
                if send_message(bot, messages['new']):
                    messages['last'] = messages['new']
                    timestamp = response.get('current_date', timestamp)
            else:
                logger.debug(messages['new'])
        except EmptyResponseFromAPI as error:
            logger.exception(f'Сбой в работе программы: {error}')
        except Exception as error:
            messages['new'] = f'Сбой в работе программы: {error}'
            logger.exception(messages['new'])

            if messages['new'] != messages['last']:
                send_message(bot, messages['new'])
                messages['last'] = messages['new']
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
