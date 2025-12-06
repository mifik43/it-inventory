import logging
import requests
import hashlib
import json
from .config import SocialConfig

logger = logging.getLogger(__name__)

class OdnoklassnikiManager:
    def __init__(self):
        self.config = SocialConfig()
        self.api_url = "https://api.ok.ru/fb.do"
    
    def _generate_sig(self, params):
        """
        Генерация подписи для запроса к OK API
        """
        sorted_params = sorted(params.items())
        sig_string = ''.join([f"{k}={v}" for k, v in sorted_params])
        sig_string += self.config.OK_SECRET_KEY
        return hashlib.md5(sig_string.encode('utf-8')).hexdigest().lower()
    
    def post(self, text, photo_path=None):
        """
        Публикация поста в группу Одноклассников
        """
        try:
            if not all([self.config.OK_ACCESS_TOKEN, self.config.OK_APPLICATION_KEY, 
                       self.config.OK_SECRET_KEY, self.config.OK_GROUP_ID]):
                return {
                    'success': False,
                    'error': 'OK API ключи не настроены'
                }
            
            # Базовые параметры
            params = {
                'method': 'mediatopic.post',
                'gid': self.config.OK_GROUP_ID,
                'type': 'GROUP_THEME',
                'format': 'json',
                'application_key': self.config.OK_APPLICATION_KEY,
                'access_token': self.config.OK_ACCESS_TOKEN
            }
            
            # Текст поста
            if text:
                params['text'] = text
            
            # Если есть фото
            if photo_path:
                # Сначала загружаем фото
                photo_token = self._upload_photo(photo_path)
                if photo_token:
                    params['attachment'] = json.dumps({
                        'media': [{
                            'type': 'photo',
                            'list': [{'id': photo_token}]
                        }]
                    })
            
            # Добавляем подпись
            params['sig'] = self._generate_sig(params)
            
            # Отправляем запрос
            response = requests.post(self.api_url, data=params)
            response.raise_for_status()
            
            result = response.json()
            
            if 'error' in result:
                return {
                    'success': False,
                    'error': result['error']
                }
            
            return {
                'success': True,
                'post_id': result.get('topic_id'),
                'url': f"https://ok.ru/group/{self.config.OK_GROUP_ID}/topic/{result.get('topic_id')}"
            }
            
        except Exception as e:
            logger.error(f"Ошибка публикации в Одноклассниках: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _upload_photo(self, photo_path):
        """
        Загрузка фото на сервер Одноклассников
        """
        try:
            # Получаем URL для загрузки
            upload_params = {
                'method': 'photosV2.getUploadUrl',
                'application_key': self.config.OK_APPLICATION_KEY,
                'access_token': self.config.OK_ACCESS_TOKEN,
                'format': 'json'
            }
            
            upload_params['sig'] = self._generate_sig(upload_params)
            
            response = requests.get(self.api_url, params=upload_params)
            response.raise_for_status()
            
            upload_data = response.json()
            
            if 'error' in upload_data:
                raise Exception(upload_data['error'])
            
            # Загружаем фото
            upload_url = upload_data.get('upload_url')
            
            with open(photo_path, 'rb') as photo:
                files = {'photo': photo}
                upload_response = requests.post(upload_url, files=files)
                upload_response.raise_for_status()
                
                photo_data = upload_response.json()
                
                if 'photos' in photo_data and photo_data['photos']:
                    return photo_data['photos'][photo_path]['token']
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка загрузки фото в Одноклассники: {str(e)}")
            return None
    
    def check_connection(self):
        """Проверка подключения к Одноклассникам"""
        try:
            if not all([self.config.OK_ACCESS_TOKEN, self.config.OK_APPLICATION_KEY, 
                       self.config.OK_SECRET_KEY]):
                return {'available': False, 'error': 'API ключи не настроены'}
            
            params = {
                'method': 'users.getCurrentUser',
                'application_key': self.config.OK_APPLICATION_KEY,
                'access_token': self.config.OK_ACCESS_TOKEN,
                'format': 'json'
            }
            
            params['sig'] = self._generate_sig(params)
            
            response = requests.get(self.api_url, params=params)
            response.raise_for_status()
            
            result = response.json()
            
            if 'error' in result:
                return {'available': False, 'error': result['error']}
            
            return {'available': True, 'message': 'Одноклассники доступны'}
            
        except Exception as e:
            return {'available': False, 'error': str(e)}