import os
from dotenv import load_dotenv

load_dotenv()

class SocialConfig:
    """Конфигурация для социальных сетей"""
    
    # Twitter API
    TWITTER_API_KEY = os.environ.get('TWITTER_API_KEY', '')
    TWITTER_API_SECRET = os.environ.get('TWITTER_API_SECRET', '')
    TWITTER_ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN', '')
    TWITTER_ACCESS_SECRET = os.environ.get('TWITTER_ACCESS_SECRET', '')
    
    # VK API
    VK_ACCESS_TOKEN = os.environ.get('VK_ACCESS_TOKEN', '')
    VK_GROUP_ID = os.environ.get('VK_GROUP_ID', '')
    
    # Telegram
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')
    
    # Instagram
    INSTAGRAM_USERNAME = os.environ.get('INSTAGRAM_USERNAME', '')
    INSTAGRAM_PASSWORD = os.environ.get('INSTAGRAM_PASSWORD', '')
    
    # Одноклассники (OK.ru)
    OK_ACCESS_TOKEN = os.environ.get('OK_ACCESS_TOKEN', '')
    OK_APPLICATION_KEY = os.environ.get('OK_APPLICATION_KEY', '')
    OK_SECRET_KEY = os.environ.get('OK_SECRET_KEY', '')
    OK_GROUP_ID = os.environ.get('OK_GROUP_ID', '')
    
    # Rutube
    RUTUBE_EMAIL = os.environ.get('RUTUBE_EMAIL', '')
    RUTUBE_PASSWORD = os.environ.get('RUTUBE_PASSWORD', '')
    
    # Настройки приложения
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'static/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB