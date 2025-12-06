import logging
import requests
from .config import SocialConfig

logger = logging.getLogger(__name__)

class TelegramManager:
    def __init__(self):
        self.config = SocialConfig()
        self.base_url = f"https://api.telegram.org/bot{self.config.TELEGRAM_BOT_TOKEN}"
    
    def post(self, text, chat_id=None, parse_mode="HTML", disable_web_page_preview=False):
        """
        Отправка текстового сообщения в Telegram
        """
        try:
            if not self.config.TELEGRAM_BOT_TOKEN:
                return {
                    'success': False,
                    'error': 'Telegram bot token не настроен'
                }
            
            if not chat_id:
                chat_id = self.config.TELEGRAM_CHAT_ID
            
            if not chat_id:
                return {
                    'success': False,
                    'error': 'Chat ID не указан'
                }
            
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_web_page_preview': disable_web_page_preview
            }
            
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            return {
                'success': True,
                'message_id': result['result']['message_id'],
                'chat_id': result['result']['chat']['id']
            }
            
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения в Telegram: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_photo(self, photo_path, caption="", chat_id=None):
        """
        Отправка фото в Telegram
        """
        try:
            if not chat_id:
                chat_id = self.config.TELEGRAM_CHAT_ID
            
            url = f"{self.base_url}/sendPhoto"
            with open(photo_path, 'rb') as photo:
                files = {'photo': photo}
                data = {
                    'chat_id': chat_id,
                    'caption': caption[:1024]
                }
                
                response = requests.post(url, files=files, data=data)
                response.raise_for_status()
                
                result = response.json()
                
                return {
                    'success': True,
                    'message_id': result['result']['message_id']
                }
                
        except Exception as e:
            logger.error(f"Ошибка отправки фото в Telegram: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_connection(self):
        """
        Получение информации о боте
        """
        try:
            if not self.config.TELEGRAM_BOT_TOKEN:
                return {'available': False, 'error': 'Bot token не настроен'}
            
            url = f"{self.base_url}/getMe"
            response = requests.get(url)
            response.raise_for_status()
            
            return {'available': True, 'message': 'Telegram бот доступен'}
            
        except Exception as e:
            return {'available': False, 'error': str(e)}