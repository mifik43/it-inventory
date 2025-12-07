from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, timedelta
import json

from templates.base.database import get_db
from templates.base.requirements import permission_required, login_required
from templates.roles.permissions import Permissions

bluprint_social_routes = Blueprint("social", __name__)

# Маршрут для публикации статьи
@bluprint_social_routes.route('/social/publish/article/<int:article_id>', methods=['GET', 'POST'])
@login_required  # Пока уберем проверку прав для теста
def publish_article(article_id):
    """Публикация статьи в социальные сети"""
    db = get_db()
    
    # Получаем статью
    article = db.execute('''
        SELECT a.*, u.username as author_name 
        FROM articles a 
        JOIN users u ON a.author_id = u.id 
        WHERE a.id = ?
    ''', (article_id,)).fetchone()
    
    if not article:
        flash('Статья не найдена', 'error')
        return redirect(url_for('articles.articles_list'))
    
    if request.method == 'POST':
        platforms = request.form.getlist('platforms')
        publish_option = request.form.get('publish_option', 'now')
        scheduled_time = request.form.get('scheduled_time')
        
        if not platforms:
            flash('Выберите хотя бы одну платформу для публикации', 'error')
            return render_template('social/publish_article.html', 
                                 article=article,
                                 platforms=['twitter', 'vk', 'telegram', 'instagram', 'odnoklassniki', 'rutube'])
        
        # Формируем контент для публикации
        content = f"{article['title']}\n\n{article['content'][:500]}..."
        if len(article['content']) > 500:
            content += f"\n\nЧитать полностью: /articles/{article_id}"
        
        # Добавляем теги, если есть
        if article['tags']:
            tags = article['tags'].split(',')
            hashtags = ' '.join([f"#{tag.strip().replace(' ', '')}" for tag in tags[:3]])
            content += f"\n\n{hashtags}"
        
        # Сохраняем в базу (для теста просто покажем результат)
        flash(f'Статья "{article["title"]}" будет опубликована в: {", ".join(platforms)}', 'success')
        return redirect(url_for('articles.view_article', article_id=article_id))
    
    # GET запрос - показываем форму
    return render_template('social/publish_article.html', 
                         article=article,
                         platforms=['twitter', 'vk', 'telegram', 'instagram', 'odnoklassniki', 'rutube'],
                         min_date=(datetime.now() + timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M'))

# Маршрут для публикации заметки
@bluprint_social_routes.route('/social/publish/note/<int:note_id>', methods=['GET', 'POST'])
@login_required  # Пока уберем проверку прав для теста
def publish_note(note_id):
    """Публикация заметки в социальные сети"""
    db = get_db()
    
    # Получаем заметку
    note = db.execute('''
        SELECT n.*, u.username as author_name 
        FROM notes n 
        JOIN users u ON n.author_id = u.id 
        WHERE n.id = ? AND n.author_id = ?
    ''', (note_id, session['user_id'])).fetchone()
    
    if not note:
        flash('Заметка не найдена', 'error')
        return redirect(url_for('notes.notes_list'))
    
    if request.method == 'POST':
        platforms = request.form.getlist('platforms')
        publish_option = request.form.get('publish_option', 'now')
        scheduled_time = request.form.get('scheduled_time')
        
        if not platforms:
            flash('Выберите хотя бы одну платформу для публикации', 'error')
            return render_template('social/publish_note.html', 
                                 note=note,
                                 platforms=['twitter', 'vk', 'telegram', 'instagram', 'odnoklassniki', 'rutube'])
        
        # Формируем контент для публикации
        content = f"{note['title']}\n\n{note['content']}"
        
        # Сохраняем в базу (для теста просто покажем результат)
        flash(f'Заметка "{note["title"]}" будет опубликована в: {", ".join(platforms)}', 'success')
        return redirect(url_for('notes.notes_list'))
    
    # GET запрос - показываем форму
    return render_template('social/publish_note.html', 
                         note=note,
                         platforms=['twitter', 'vk', 'telegram', 'instagram', 'odnoklassniki', 'rutube'],
                         min_date=(datetime.now() + timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M'))

# Маршруты для истории и запланированных
@bluprint_social_routes.route('/social/history')
@login_required
def social_history():
    """История публикаций"""
    db = get_db()
    
    posts = db.execute('''
        SELECT sp.*, 
               a.title as article_title, 
               n.title as note_title,
               u.username as publisher_name
        FROM social_posts sp
        LEFT JOIN articles a ON sp.article_id = a.id
        LEFT JOIN notes n ON sp.note_id = n.id
        JOIN users u ON sp.user_id = u.id
        WHERE sp.user_id = ?
        ORDER BY sp.published_at DESC
        LIMIT 50
    ''', (session['user_id'],)).fetchall()
    
    return render_template('social/history.html', posts=posts)

@bluprint_social_routes.route('/social/save_platform_config/<platform>', methods=['POST'])
@login_required
def save_platform_config(platform):
    """Сохранение настроек платформы в .env файл"""
    try:
        env_file = '.env'
        
        # Читаем существующие настройки
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                lines = f.readlines()
        else:
            lines = []
        
        # Подготавливаем новые настройки для этой платформы
        new_settings = {}
        
        if platform == 'twitter':
            new_settings = {
                'TWITTER_API_KEY': request.form.get('api_key', '').strip(),
                'TWITTER_API_SECRET': request.form.get('api_secret', '').strip(),
                'TWITTER_ACCESS_TOKEN': request.form.get('access_token', '').strip(),
                'TWITTER_ACCESS_SECRET': request.form.get('access_secret', '').strip(),
            }
        elif platform == 'vk':
            new_settings = {
                'VK_ACCESS_TOKEN': request.form.get('access_token', '').strip(),
                'VK_GROUP_ID': request.form.get('group_id', '').strip(),
            }
        elif platform == 'telegram':
            new_settings = {
                'TELEGRAM_BOT_TOKEN': request.form.get('bot_token', '').strip(),
                'TELEGRAM_CHAT_ID': request.form.get('chat_id', '').strip(),
            }
        elif platform == 'instagram':
            new_settings = {
                'INSTAGRAM_USERNAME': request.form.get('username', '').strip(),
                'INSTAGRAM_PASSWORD': request.form.get('password', '').strip(),
            }
        elif platform == 'odnoklassniki':
            new_settings = {
                'OK_ACCESS_TOKEN': request.form.get('access_token', '').strip(),
                'OK_APPLICATION_KEY': request.form.get('application_key', '').strip(),
                'OK_SECRET_KEY': request.form.get('secret_key', '').strip(),
                'OK_GROUP_ID': request.form.get('group_id', '').strip(),
            }
        elif platform == 'rutube':
            new_settings = {
                'RUTUBE_EMAIL': request.form.get('email', '').strip(),
                'RUTUBE_PASSWORD': request.form.get('password', '').strip(),
            }
        
        # Обновляем или добавляем настройки
        updated_lines = []
        settings_to_add = new_settings.copy()
        
        for line in lines:
            line_stripped = line.strip()
            if line_stripped and not line_stripped.startswith('#'):
                for key in list(settings_to_add.keys()):
                    if line_stripped.startswith(key + '='):
                        # Заменяем существующую строку
                        updated_lines.append(f"{key}={settings_to_add[key]}\n")
                        settings_to_add.pop(key)
                        break
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)
        
        # Добавляем новые настройки
        for key, value in settings_to_add.items():
            updated_lines.append(f"{key}={value}\n")
        
        # Сохраняем файл
        with open(env_file, 'w') as f:
            f.writelines(updated_lines)
        
        flash(f'Настройки для {platform} успешно сохранены в .env файл', 'success')
        flash('⚠️ Для применения изменений необходимо перезапустить сервер', 'warning')
        
    except Exception as e:
        flash(f'Ошибка при сохранении настроек: {str(e)}', 'error')
    
    return redirect(url_for('social.social_platforms'))

@bluprint_social_routes.route('/social/scheduled')
@login_required
def scheduled_posts():
    """Запланированные публикации"""
    db = get_db()
    
    scheduled = db.execute('''
        SELECT sp.*, 
               a.title as article_title, 
               n.title as note_title,
               u.username as publisher_name
        FROM scheduled_posts sp
        LEFT JOIN articles a ON sp.source_type = 'article' AND sp.source_id = a.id
        LEFT JOIN notes n ON sp.source_type = 'note' AND sp.source_id = n.id
        JOIN users u ON sp.user_id = u.id
        WHERE sp.user_id = ? AND sp.status = 'scheduled'
        ORDER BY sp.scheduled_time ASC
    ''', (session['user_id'],)).fetchall()
    
    return render_template('social/scheduled.html', scheduled_posts=scheduled)

@bluprint_social_routes.route('/social/cancel_scheduled/<int:post_id>')
@login_required
def cancel_scheduled(post_id):
    """Отмена запланированной публикации"""
    db = get_db()
    
    post = db.execute('SELECT * FROM scheduled_posts WHERE id = ? AND user_id = ?', 
                     (post_id, session['user_id'])).fetchone()
    
    if not post:
        flash('Запланированная публикация не найдена', 'error')
        return redirect(url_for('social.scheduled_posts'))
    
    db.execute('UPDATE scheduled_posts SET status = "cancelled" WHERE id = ?', (post_id,))
    db.commit()
    
    flash('Запланированная публикация отменена', 'success')
    return redirect(url_for('social.scheduled_posts'))

@bluprint_social_routes.route('/social/platforms')
@login_required
def social_platforms():
    """Настройки платформ"""
    return render_template('social/platforms.html')

@bluprint_social_routes.route('/social/test_platform/<platform>')
@login_required
def test_platform(platform):
    """Тестирование платформы"""
    flash(f'Тестирование платформы {platform} (в разработке)', 'info')
    return redirect(url_for('social.social_platforms'))

# Контекстный процессор для даты
@bluprint_social_routes.context_processor
def inject_today_date():
    """Добавляет сегодняшнюю дату в контекст"""
    return {'today': datetime.now()}