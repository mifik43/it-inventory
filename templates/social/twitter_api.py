import logging
import tweepy
from .config import SocialConfig

logger = logging.getLogger(__name__)

class TwitterManager:
    def __init__(self):
        self.config = SocialConfig()
        self.api = self._init_client()
    
    def _init_client(self):
        """Инициализация клиента Twitter"""
        try:
            if not all([self.config.TWITTER_API_KEY, self.config.TWITTER_API_SECRET,
                       self.config.TWITTER_ACCESS_TOKEN, self.config.TWITTER_ACCESS_SECRET]):
                logger.warning("Twitter API ключи не настроены")
                return None
            
            auth = tweepy.OAuth1UserHandler(
                self.config.TWITTER_API_KEY, 
                self.config.TWITTER_API_SECRET,
                self.config.TWITTER_ACCESS_TOKEN,
                self.config.TWITTER_ACCESS_SECRET
            )
            api = tweepy.API(auth)
            
            # Проверяем подключение
            api.verify_credentials()
            logger.info("Twitter клиент успешно инициализирован")
            return api
            
        except Exception as e:
            logger.error(f"Ошибка инициализации Twitter клиента: {str(e)}")
            return None
    
    def post(self, content, image_path=None):
        """Публикация твита"""
        if not self.api:
            return {
                'success': False,
                'error': 'Twitter клиент не инициализирован. Проверьте настройки API.'
            }
        
        try:
            if image_path:
                media = self.api.media_upload(image_path)
                tweet = self.api.update_status(status=content, media_ids=[media.media_id])
            else:
                tweet = self.api.update_status(status=content)
            
            return {
                'success': True,
                'tweet_id': tweet.id,
                'url': f'https://twitter.com/user/status/{tweet.id}'
            }
        except Exception as e:
            logger.error(f"Ошибка публикации в Twitter: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_connection(self):
        """Проверка подключения к Twitter"""
        if not self.api:
            return {'available': False, 'error': 'Клиент не инициализирован'}
        
        try:
            self.api.verify_credentials()
            return {'available': True, 'message': 'Twitter доступен'}
        except Exception as e:
            return {'available': False, 'error': str(e)}