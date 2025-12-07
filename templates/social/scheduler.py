
import json
import time
import threading
from datetime import datetime, timedelta
import logging

from templates.base.database import get_db
from .social_manager import SocialMediaManager

logger = logging.getLogger(__name__)

class SocialScheduler:
    """Планировщик для отложенных публикаций"""
    
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
                logger.error(f"Ошибка в планировщике: {str(e)}")
            
            # Пауза 60 секунд между проверками
            for _ in range(60):
                if not self.running:
                    break
                time.sleep(1)
    
    def _check_scheduled_posts(self):
        """Проверка запланированных публикаций"""
        with self.app.app_context():
            db = get_db()
            
            # Получаем посты, которые нужно опубликовать
            now = datetime.now()
            scheduled_posts = db.execute('''
                SELECT sp.*, 
                       a.content as article_content, a.title as article_title,
                       n.content as note_content, n.title as note_title
                FROM scheduled_posts sp
                LEFT JOIN articles a ON sp.source_type = 'article' AND sp.source_id = a.id
                LEFT JOIN notes n ON sp.source_type = 'note' AND sp.source_id = n.id
                WHERE sp.status = 'scheduled' 
                AND sp.scheduled_time <= ?
                ORDER BY sp.scheduled_time
            ''', (now,)).fetchall()
            
            for post in scheduled_posts:
                try:
                    # Меняем статус на "обрабатывается"
                    db.execute('UPDATE scheduled_posts SET status = "processing" WHERE id = ?', 
                              (post['id'],))
                    db.commit()
                    
                    # Определяем контент для публикации
                    if post['source_type'] == 'article':
                        content = f"{post['article_title']}\n\n{post['article_content'][:500]}..."
                    else:
                        content = f"{post['note_title']}\n\n{post['note_content']}"
                    
                    # Получаем список платформ
                    platforms = json.loads(post['platforms'])
                    
                    # Публикуем
                    results = self.social_manager.publish_post(content, platforms)
                    
                    # Сохраняем в историю
                    if post['source_type'] == 'article':
                        source_id_field = 'article_id'
                    else:
                        source_id_field = 'note_id'
                    
                    db.execute(f'''
                        INSERT INTO social_posts 
                        ({source_id_field}, content, platforms, results, status, user_id, published_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (post['source_id'], content, json.dumps(platforms), 
                          json.dumps(results), 'published', post['user_id'], now))
                    
                    # Обновляем статус запланированного поста
                    success_count = sum(1 for r in results.values() if r.get('success'))
                    if success_count > 0:
                        new_status = 'completed'
                    else:
                        new_status = 'failed'
                    
                    db.execute('''
                        UPDATE scheduled_posts 
                        SET status = ?, completed_at = ?
                        WHERE id = ?
                    ''', (new_status, now, post['id']))
                    
                    db.commit()
                    
                    logger.info(f"Опубликован запланированный пост {post['id']} в {success_count} платформ")
                    
                except Exception as e:
                    logger.error(f"Ошибка при публикации запланированного поста {post['id']}: {str(e)}")
                    
                    # Обновляем статус на "ошибка"
                    db.execute('UPDATE scheduled_posts SET status = "failed" WHERE id = ?', 
                              (post['id'],))
                    db.commit()
    
    def schedule_post(self, source_type, source_id, platforms, scheduled_time, user_id):
        """Планирование новой публикации"""
        with self.app.app_context():
            db = get_db()
            
            db.execute('''
                INSERT INTO scheduled_posts 
                (source_type, source_id, platforms, scheduled_time, user_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (source_type, source_id, json.dumps(platforms), scheduled_time, user_id))
            
            db.commit()
            logger.info(f"Запланирована новая публикация на {scheduled_time}")