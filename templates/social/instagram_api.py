import logging
import os
from .config import SocialConfig

logger = logging.getLogger(__name__)

class InstagramManager:
    def __init__(self):
        self.config = SocialConfig()
        self.client = None
        
        # Проверяем наличие библиотеки
        try:
            from instagrapi import Client
            self.Client = Client
        except ImportError:
            logger.error("Библиотека instagrapi не установлена")
            return
        
        self._init_client()
    
    def _init_client(self):
        """Инициализация Instagram клиента"""
        try:
            if not self.config.INSTAGRAM_USERNAME or not self.config.INSTAGRAM_PASSWORD:
                logger.warning("Instagram учетные данные не настроены")
                return
            
            self.client = self.Client()
            
            # Пробуем логин
            self.client.login(self.config.INSTAGRAM_USERNAME, self.config.INSTAGRAM_PASSWORD)
            
            logger.info("Instagram клиент успешно инициализирован")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации Instagram клиента: {str(e)}")
    
    def post(self, content, image_path=None):
        """Публикация в Instagram"""
        if not self.client:
            return {
                'success': False,
                'error': 'Instagram клиент не инициализирован. Проверьте учетные данные.'
            }
        
        try:
            if image_path:
                # Загружаем фото
                media = self.client.photo_upload(
                    path=image_path,
                    caption=content
                )
            else:
                # Instagram требует медиа, создаем простой пост
                return {
                    'success': False,
                    'error': 'Instagram требует изображение или видео для публикации'
                }
            
            return {
                'success': True,
                'media_id': media.id,
                'code': media.code,
                'url': f"https://www.instagram.com/p/{media.code}/"
            }
            
        except Exception as e:
            logger.error(f"Ошибка публикации в Instagram: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_connection(self):
        """Проверка подключения к Instagram"""
        if not self.client:
            return {'available': False, 'error': 'Клиент не инициализирован'}
        
        try:
            user_id = self.client.user_id
            info = self.client.user_info(user_id)
            
            return {
                'available': True,
                'message': f'Instagram доступен. Пользователь: {info.username}'
            }
        except Exception as e:
            return {'available': False, 'error': str(e)}