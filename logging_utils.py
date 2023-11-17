import logging


class LoggerSender():
    """A custom logger class for handling log messages and sending them."""

    def __init__(self):
        """
        Initializes a LoggerSender instance.

        Attributes:
            error_messages (set): A set to keep track of unique error messages.
        """
        self.error_messages = set()

    def critical(self, message):
        """Logs a critical-level message."""
        logging.critical(message)

    def error(self, message, send_to_tg=True):
        """Logs an error-level message and optionally sends it to Telegram."""
        logging.error(message)

        if send_to_tg:
            self.send_message_to_tg(message)

    def exception(self, message):
        """Logs an exception-level message and sends it to Telegram."""
        logging.exception(message)
        self.send_message_to_tg(message)

    def debug(self, message):
        """Logs a debug-level message."""
        logging.debug(message)

    def warning(self, message):
        """Logs a warning-level message."""
        logging.warning(message)

    def info(self, message):
        """Logs an info-level message."""
        logging.info(message)

    def add_telegram_bot(self, bot):
        """Sets the Telegram bot instance for sending messages."""
        self.bot = bot

    def add_send_message_funk(self, send_message_funk):
        """Sets the function for sending messages."""
        self.send_message = send_message_funk

    def send_message_to_tg(self, message):
        """Sends a message to Telegram if a bot and send function are set."""
        if (
            self.bot
            and self.send_message
            and message not in self.error_messages
        ):
            self.error_messages.add(message)
            self.send_message(self.bot, message)
