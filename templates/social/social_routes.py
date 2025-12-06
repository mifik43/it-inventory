from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, timedelta
import json

from templates.base.database import get_db
from templates.base.requirements import permission_required, login_required
from templates.roles.permissions import Permissions

bluprint_social_routes = Blueprint("social", __name__)

@bluprint_social_routes.route('/social/publish/article/<int:article_id>', methods=['GET', 'POST'])
@permission_required(Permissions.articles_manage)
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
            content += f"\n\nЧитать полностью на портале"
        
        # Добавляем теги, если есть
        if article['tags']:
            tags = article['tags'].split(',')
            hashtags = ' '.join([f"#{tag.strip().replace(' ', '')}" for tag in tags[:3]])
            content += f"\n\n{hashtags}"
        
        # Сохраняем информацию о публикации
        try:
            db.execute('''
                INSERT INTO social_posts 
                (article_id, content, platforms, status, user_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (article_id, content, json.dumps(platforms), 
                  'published', session['user_id']))
            
            db.commit()
            flash(f'Статья подготовлена для публикации в {len(platforms)} соцсетях', 'success')
            return redirect(url_for('articles.view_article', article_id=article_id))
            
        except Exception as e:
            flash(f'Ошибка при сохранении публикации: {str(e)}', 'error')
    
    # GET запрос - показываем форму
    return render_template('social/publish_article.html', 
                         article=article,
                         platforms=['twitter', 'vk', 'telegram', 'instagram', 'odnoklassniki', 'rutube'],
                         min_date=(datetime.now() + timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M'))

@bluprint_social_routes.route('/social/publish/note/<int:note_id>', methods=['GET', 'POST'])
@permission_required(Permissions.notes_manage)
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
        
        # Сохраняем информацию о публикации
        try:
            db.execute('''
                INSERT INTO social_posts 
                (note_id, content, platforms, status, user_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (note_id, content, json.dumps(platforms), 
                  'published', session['user_id']))
            
            db.commit()
            flash(f'Заметка подготовлена для публикации в {len(platforms)} соцсетях', 'success')
            return redirect(url_for('notes.notes_list'))
            
        except Exception as e:
            flash(f'Ошибка при сохранении публикации: {str(e)}', 'error')
    
    # GET запрос - показываем форму
    return render_template('social/publish_note.html', 
                         note=note,
                         platforms=['twitter', 'vk', 'telegram', 'instagram', 'odnoklassniki', 'rutube'],
                         min_date=(datetime.now() + timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M'))

@bluprint_social_routes.route('/social/history')
@login_required
def social_history():
    """История публикаций в социальные сети"""
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
        ORDER BY sp.created_at DESC
        LIMIT 50
    ''', (session['user_id'],)).fetchall()
    
    # Парсим результаты для отображения
    for post in posts:
        if post['platforms']:
            try:
                post['platforms_parsed'] = json.loads(post['platforms'])
            except:
                post['platforms_parsed'] = []
    
    return render_template('social/history.html', posts=posts)

@bluprint_social_routes.route('/social/scheduled')
@login_required
def scheduled_posts():
    """Список запланированных публикаций"""
    db = get_db()
    
    scheduled = db.execute('''
        SELECT sp.*, 
               a.title as article_title, 
               n.title as note_title,
               u.username as publisher_name
        FROM social_posts sp
        LEFT JOIN articles a ON sp.article_id = a.id
        LEFT JOIN notes n ON sp.note_id = n.id
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
    
    post = db.execute('SELECT * FROM social_posts WHERE id = ? AND user_id = ?', 
                     (post_id, session['user_id'])).fetchone()
    
    if not post:
        flash('Запланированная публикация не найдена', 'error')
        return redirect(url_for('social.scheduled_posts'))
    
    db.execute('UPDATE social_posts SET status = "cancelled" WHERE id = ?', (post_id,))
    db.commit()
    
    flash('Запланированная публикация отменена', 'success')
    return redirect(url_for('social.scheduled_posts'))