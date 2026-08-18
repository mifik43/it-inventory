import json
import time
import threading
from datetime import datetime
import logging

from templates.base.database_helper import db
from models import ScheduledPost, Article, Note, SocialPost
from .social_manager import SocialMediaManager

logger = logging.getLogger(__name__)

class SocialScheduler:
    """Планировщик для отложенных публикаций (на ORM)"""
    
    def __init__(self, app=None):
        self.app = app
        self.social_manager = SocialMediaManager()
        self.running = False
        self.thread = None
        
    def start(self):
        """Запуск планировщика в отдельном потоке"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()
        logger.info("Планировщик социальных публикаций запущен")
    
    def stop(self):
        """Остановка планировщика"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Планировщик социальных публикаций остановлен")
    
    def _scheduler_loop(self):
        """Основной цикл планировщика"""
        while self.running:
            try:
                self._check_scheduled_posts()
            except Exception as e:
                logger.error(f"Ошибка в планировщике: {str(e)}", exc_info=True)
            
            # Пауза 60 секунд между проверками
            for _ in range(60):
                if not self.running:
                    break
                time.sleep(1)
    
    def _check_scheduled_posts(self):
        """Проверка запланированных публикаций (ORM)"""
        with self.app.app_context():
            now = datetime.now()
            
            # Получаем посты со статусом 'scheduled' и временем <= now
            scheduled_posts = ScheduledPost.query.filter(
                ScheduledPost.status == 'scheduled',
                ScheduledPost.scheduled_time <= now
            ).order_by(ScheduledPost.scheduled_time).all()
            
            for post in scheduled_posts:
                try:
                    # Меняем статус на 'processing'
                    post.status = 'processing'
                    db.session.commit()
                    
                    # Определяем контент в зависимости от источника
                    if post.source_type == 'article':
                        article = Article.query.get(post.source_id)
                        if article:
                            content = f"{article.title}\n\n{article.content[:500]}..."
                        else:
                            content = "Статья удалена"
                    else:  # 'note'
                        note = Note.query.get(post.source_id)
                        if note:
                            content = f"{note.title}\n\n{note.content}"
                        else:
                            content = "Заметка удалена"
                    
                    # Получаем платформы из JSON
                    platforms_raw = json.loads(post.platforms)
                    logger.info(f"Raw platforms from DB: {platforms_raw}")
                    
                    # Приводим к списку строк (если в БД хранятся словари)
                    if isinstance(platforms_raw, list) and platforms_raw:
                        if isinstance(platforms_raw[0], dict):
                            platforms = []
                            for p in platforms_raw:
                                if 'platform' in p:
                                    platforms.append(p['platform'])
                                elif 'name' in p:
                                    platforms.append(p['name'])
                                else:
                                    platforms.append(str(p))
                            logger.info(f"Converted platforms from dicts to strings: {platforms}")
                        else:
                            platforms = platforms_raw
                    else:
                        platforms = platforms_raw
                    
                    logger.info(f"Final platforms list: {platforms}")
                    
                    # Публикуем через SocialMediaManager
                    results = self.social_manager.publish_post(content, platforms)
                    
                    # Создаём запись в social_posts
                    social_post = SocialPost(
                        content=content,
                        platforms=json.dumps(platforms),
                        results=json.dumps(results),
                        status='published',
                        user_id=post.user_id,
                        published_at=now
                    )
                    if post.source_type == 'article':
                        social_post.article_id = post.source_id
                    else:
                        social_post.note_id = post.source_id
                    
                    db.session.add(social_post)
                    
                    # Обновляем статус запланированного поста
                    success_count = sum(1 for r in results.values() if r.get('success'))
                    post.status = 'completed' if success_count > 0 else 'failed'
                    post.completed_at = now
                    
                    db.session.commit()
                    logger.info(f"Опубликован запланированный пост {post.id} в {success_count} платформ")
                    
                except Exception as e:
                    logger.error(f"Ошибка при публикации запланированного поста {post.id}: {str(e)}", exc_info=True)
                    post.status = 'failed'
                    db.session.commit()
    
    def schedule_post(self, source_type, source_id, platforms, scheduled_time, user_id):
        """Планирование новой публикации (ORM)"""
        with self.app.app_context():
            post = ScheduledPost(
                source_type=source_type,
                source_id=source_id,
                platforms=json.dumps(platforms),
                scheduled_time=scheduled_time,
                user_id=user_id,
                status='scheduled'
            )
            db.session.add(post)
            db.session.commit()
            logger.info(f"Запланирована новая публикация на {scheduled_time}")