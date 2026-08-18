import os
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime

# Import logger from the same package to maintain consistency
# from templates.base.logger import setup_logger  # Assuming this is where your logger is defined

def setup_logger(app, log_level=None):
    """
    Настраивает логирование для Flask приложения.
    
    Args:
        app: Flask приложение
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Определяем уровень логирования
    if log_level is None:
        log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'))

    # Создаем папку для логов, если её нет
    log_dir = os.path.join(app.root_path, '..', app.config.get('LOG_DIR', 'logs'))
    log_dir = os.path.abspath(log_dir)
    os.makedirs(log_dir, exist_ok=True)
    
    # Форматтер для логов
    log_format = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # В консоль выводим INFO и выше
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # Основной файл логов (ротация по времени - daily)
    file_handler = TimedRotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        when='midnight',
        interval=1,
        backupCount=30,  # Храним 30 дней логов
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(log_format)
    
    # Обработчик ошибок (отдельный файл)
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, 'error.log'),
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=10,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(log_format)
    
    # Получаем логгер Flask и настраиваем его
    app_logger = logging.getLogger('flask_app')
    app_logger.setLevel(log_level)
    app_logger.addHandler(console_handler)
    app_logger.addHandler(file_handler)
    app_logger.addHandler(error_handler)
    
    # Убираем дублирование логов от Flask
    app.logger.handlers = []
    app.logger.setLevel(log_level)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_handler)
    
    # Логгер для других модулей
    general_logger = logging.getLogger(__name__)
    general_logger.setLevel(log_level)
    general_logger.addHandler(console_handler)
    general_logger.addHandler(file_handler)
    general_logger.addHandler(error_handler)
    
    logger.info('Логирование инициализировано')
    return app_logger

# Add this at the bottom to ensure logger is available globally
logger = logging.getLogger(__name__)
