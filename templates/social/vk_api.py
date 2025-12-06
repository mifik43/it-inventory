import logging
import vk_api
from vk_api.upload import VkUpload
from .config import SocialConfig

logger = logging.getLogger(__name__)

class VKManager:
    def __init__(self):
        self.config = SocialConfig()
        self.vk_session = None
        self.vk = None
        self.upload = None
        self._init_client()
    
    def _init_client(self):
        """Инициализация клиента VK"""
        try:
            if not self.config.VK_ACCESS_TOKEN:
                logger.warning("VK access token не настроен")
                return
            
            self.vk_session = vk_api.VkApi(token=self.config.VK_ACCESS_TOKEN)
            self.vk = self.vk_session.get_api()
            self.upload = VkUpload(self.vk_session)
            logger.info("VK клиент успешно инициализирован")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации VK клиента: {str(e)}")
    
    def post(self, content, images=None):
        """Публикация на стену VK"""
        if not self.vk:
            return {
                'success': False,
                'error': 'VK клиент не инициализирован. Проверьте access token.'
            }
        
        try:
            attachments = []
            
            # Загрузка изображений
            if images:
                for image_path in images:
                    photo = self.upload.photo_wall(image_path, group_id=self.config.VK_GROUP_ID)
                    attachments.append(f"photo{photo[0]['owner_id']}_{photo[0]['id']}")
            
            # Публикация поста
            post = self.vk.wall.post(
                owner_id=f"-{self.config.VK_GROUP_ID}" if self.config.VK_GROUP_ID else None,
                message=content,
                attachments=",".join(attachments) if attachments else None,
                from_group=1 if self.config.VK_GROUP_ID else 0
            )
            
            post_id = post['post_id']
            owner_id = f"-{self.config.VK_GROUP_ID}" if self.config.VK_GROUP_ID else post['post_id']
            
            return {
                'success': True,
                'post_id': post_id,
                'url': f'https://vk.com/wall{owner_id}_{post_id}'
            }
        except Exception as e:
            logger.error(f"Ошибка публикации в VK: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_connection(self):
        """Проверка подключения к VK"""
        if not self.vk:
            return {'available': False, 'error': 'Клиент не инициализирован'}
        
        try:
            self.vk.users.get()
            return {'available': True, 'message': 'VK доступен'}
        except Exception as e:
            return {'available': False, 'error': str(e)}