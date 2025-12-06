import logging
import requests
import time
from .config import SocialConfig

logger = logging.getLogger(__name__)

class RutubeManager:
    def __init__(self):
        self.config = SocialConfig()
        self.base_url = "https://rutube.ru/api"
        self.auth_token = None
        self._authenticate()
    
    def _authenticate(self):
        """Аутентификация в Rutube API"""
        try:
            if not self.config.RUTUBE_EMAIL or not self.config.RUTUBE_PASSWORD:
                logger.warning("Rutube учетные данные не настроены")
                return False
            
            auth_url = f"{self.base_url}/accounts/login/"
            
            payload = {
                'email': self.config.RUTUBE_EMAIL,
                'password': self.config.RUTUBE_PASSWORD
            }
            
            response = requests.post(auth_url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            self.auth_token = result.get('auth_token')
            
            if self.auth_token:
                logger.info("Успешная авторизация в Rutube")
                return True
            else:
                logger.error("Не удалось получить токен авторизации")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка авторизации в Rutube: {str(e)}")
            return False
    
    def post(self, content, video_path=None):
        """Публикация в Rutube (загрузка видео)"""
        if not self.auth_token:
            if not self._authenticate():
                return {
                    'success': False,
                    'error': 'Ошибка авторизации в Rutube'
                }
        
        if not video_path:
            return {
                'success': False,
                'error': 'Rutube требует видеофайл для публикации'
            }
        
        try:
            # Создаем запись о видео
            create_url = f"{self.base_url}/videos/"
            
            video_data = {
                'title': content[:100],
                'description': content,
                'category': '1',
                'is_private': False
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Token {self.auth_token}'
            }
            
            response = requests.post(
                create_url,
                json=video_data,
                headers=headers
            )
            response.raise_for_status()
            
            video_info = response.json()
            video_id = video_info.get('id')
            
            if not video_id:
                return {
                    'success': False,
                    'error': 'Не удалось создать видео'
                }
            
            # Получаем URL для загрузки
            upload_url = f"{self.base_url}/videos/{video_id}/upload/"
            
            response = requests.get(upload_url, headers=headers)
            response.raise_for_status()
            
            upload_info = response.json()
            upload_url_link = upload_info.get('url')
            
            if not upload_url_link:
                return {
                    'success': False,
                    'error': 'Не удалось получить URL для загрузки'
                }
            
            # Загружаем видео файл
            with open(video_path, 'rb') as video_file:
                files = {'file': video_file}
                upload_response = requests.put(upload_url_link, files=files)
                upload_response.raise_for_status()
            
            return {
                'success': True,
                'video_id': video_id,
                'url': f"https://rutube.ru/video/{video_id}/"
            }
            
        except Exception as e:
            logger.error(f"Ошибка загрузки видео на Rutube: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_connection(self):
        """Проверка подключения к Rutube"""
        try:
            if not self.config.RUTUBE_EMAIL or not self.config.RUTUBE_PASSWORD:
                return {'available': False, 'error': 'Учетные данные не настроены'}
            
            if not self.auth_token and not self._authenticate():
                return {'available': False, 'error': 'Не удалось аутентифицироваться'}
            
            return {'available': True, 'message': 'Rutube доступен'}
            
        except Exception as e:
            return {'available': False, 'error': str(e)}