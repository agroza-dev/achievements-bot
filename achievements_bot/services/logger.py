import logging
import os
from logging.handlers import TimedRotatingFileHandler
from achievements_bot import config


def setup_logging():
    log_dir = config.LOGS_DIR
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, 'bot.log')
    debug_file = os.path.join(log_dir, 'debug.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    log = logging.getLogger()
    log.setLevel(logging.DEBUG)

    handler = TimedRotatingFileHandler(log_file, when='midnight', interval=1, backupCount=7, encoding='utf-8')
    handler.suffix = "%d-%m-%Y"
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    log.addHandler(handler)

    handler = TimedRotatingFileHandler(debug_file, when='midnight', interval=1, backupCount=2, encoding='utf-8')
    handler.suffix = "%d-%m-%Y"
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)
    log.addHandler(handler)

    return log


# Запуск настройки при импорте
logger = setup_logging()
