import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class SocialMediaManager:
    """Универсальный менеджер для работы со всеми социальными сетями"""
    
    def __init__(self):
        self.platforms = {}
        self._init_platforms()
    
    def _init_platforms(self):
        """Инициализация менеджеров для всех платформ"""
        platform_configs = {
            'twitter': ('twitter_api', 'TwitterManager'),
            'vk': ('vk_api', 'VKManager'),
            'telegram': ('telegram_api', 'TelegramManager'),
            'instagram': ('instagram_api', 'InstagramManager'),
            'odnoklassniki': ('ok_api', 'OdnoklassnikiManager'),
            'rutube': ('rutube_api', 'RutubeManager'),
        }
        
        for platform, (module_name, class_name) in platform_configs.items():
            try:
                # Динамический импорт
                module = __import__(f'templates.social.{module_name}', 
                                   fromlist=[class_name])
                manager_class = getattr(module, class_name)
                self.platforms[platform] = manager_class()
                logger.info(f"Менеджер для {platform} успешно загружен")
            except ImportError as e:
                logger.warning(f"Не удалось загрузить менеджер для {platform}: {str(e)}")
            except Exception as e:
                logger.warning(f"Ошибка при инициализации менеджера для {platform}: {str(e)}")
    
    def publish_post(self, content: str, platforms: List[str], 
                    media_files: Optional[List[str]] = None) -> Dict:
        """
        Публикация поста в выбранные соцсети
        """
        results = {}
        
        for platform in platforms:
            if platform not in self.platforms:
                results[platform] = {
                    'success': False,
                    'error': f'Платформа {platform} не настроена'
                }
                continue
            
            try:
                platform_manager = self.platforms[platform]
                
                # Определяем тип контента и используем соответствующий метод
                if media_files and len(media_files) > 0:
                    first_file = media_files[0]
                    
                    # Определяем тип файла
                    if first_file.endswith(('.mp4', '.mov', '.avi')):
                        if hasattr(platform_manager, 'upload_video'):
                            results[platform] = platform_manager.upload_video(first_file, content)
                        elif platform == 'telegram':
                            results[platform] = platform_manager.send_video(first_file, content)
                        elif platform == 'rutube':
                            results[platform] = platform_manager.post(content, first_file)
                        else:
                            results[platform] = platform_manager.post(content, first_file)
                    elif first_file.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                        if hasattr(platform_manager, 'upload_photo'):
                            results[platform] = platform_manager.upload_photo(first_file, content)
                        elif platform == 'telegram':
                            results[platform] = platform_manager.send_photo(first_file, content)
                        else:
                            results[platform] = platform_manager.post(content, first_file)
                    else:
                        results[platform] = platform_manager.post(content)
                else:
                    results[platform] = platform_manager.post(content)
                    
            except Exception as e:
                logger.error(f"Ошибка публикации в {platform}: {str(e)}")
                results[platform] = {
                    'success': False,
                    'error': str(e)
                }
        
        return results
    
    def get_available_platforms(self) -> List[str]:
        """Получение списка доступных платформ"""
        return list(self.platforms.keys())
    
    def get_platform_status(self, platform: str) -> Dict:
        """Проверка статуса подключения к платформе"""
        if platform not in self.platforms:
            return {'available': False, 'error': 'Платформа не настроена'}
        
        try:
            manager = self.platforms[platform]
            if hasattr(manager, 'check_connection'):
                return manager.check_connection()
            else:
                return {'available': True, 'message': 'Платформа доступна'}
        except Exception as e:
            return {'available': False, 'error': str(e)}