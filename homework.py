import os
import sys
import time
import logging
from http import HTTPStatus

import requests
import telegram
from telegram.error import TelegramError
from requests import HTTPError, RequestException
from dotenv import load_dotenv

from exceptions import (
    AuthenticationError, BadRequestError, EnvironmentVariableError
)

from logging_utils import LoggerSender


logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    level=logging.DEBUG
)
handler = logging.StreamHandler(sys.stdout)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger = LoggerSender()


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


TIMEOUT = 30
RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


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

    try:
        missing_token = set()

        for key, value in required_tokens.items():
            if not value:
                missing_token.add(key)

        if missing_token:
            raise EnvironmentVariableError(
                f'Variables ({", ".join(missing_token)}) not found '
                'or have an empty value in program environment.'
            )
    except EnvironmentVariableError as error:
        logger.critical(f'{EnvironmentVariableError.__name__}: {error}')
        raise SystemExit(error)


def send_message(bot, message):
    """Sends a message using the Telegram bot to the specified chat."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Successful message sending.')
    except TelegramError as error:
        logger.error(f'{type(error).__name__}: {error}', send_to_tg=False)


def get_api_answer(timestamp):
    """
    Sends a GET request to the API endpoint with the given timestamp.
    Returns parsed API response.

    Raises:
        - AuthenticationError: If the API returns a 401 status code.
        - BadRequestError: If the API returns a 400 status code.
        - HTTPError:
            If the API returns a status code other than 200, 401, or 400.
    """
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp},
            timeout=TIMEOUT,
        )
    except RequestException as error:
        logger.error(f'Error making request to API: {error}')

    if response.status_code == HTTPStatus.UNAUTHORIZED:
        raise AuthenticationError('Invalid token PRACTICUM_TOKEN.')

    if response.status_code == HTTPStatus.BAD_REQUEST:
        raise BadRequestError('Invalid parameter from_date.')

    if response.status_code != HTTPStatus.OK:
        raise HTTPError(
            f'Invalid request status: {response.status_code}'
        )

    return response.json()


def check_response(response):
    """
    Checks the validity of the API response.

    Raises:
        - ValueError: If required keys are not found.
        - TypeError:
            If the response or its 'homeworks' key is not of the expected type.
    """
    if not isinstance(response, dict):
        raise TypeError('The type of response is not a dict.')

    if 'homeworks' not in response or 'current_date' not in response:
        raise ValueError('Invalid API response: required keys not found.')

    if not isinstance(response.get('homeworks'), list):
        raise TypeError('The value for key "homeworks" is not a list.')

    return True


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
    verdict = HOMEWORK_VERDICTS.get(status)

    if not homework_name:
        raise ValueError('Invalid value homework_name.')

    if not verdict:
        raise ValueError(f'Invalid status of homework: {status}')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """The main logic of the bot."""
    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    logger.add_telegram_bot(bot)
    logger.add_send_message_funk(send_message)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks = response.get('homeworks')
            timestamp = response.get('current_date')

            if not homeworks:
                logger.debug('No new statuses of homework.')
            else:
                for homework in homeworks:
                    message = parse_status(homework)
                    send_message(bot, message)
        except (
            AuthenticationError,
            BadRequestError,
            ValueError,
            TypeError,
            HTTPError,
        ) as error:
            message = f'{type(error).__name__}: {error}'
            logger.error(message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.exception(message)

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
