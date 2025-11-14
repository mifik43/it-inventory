from flask import render_template, request, redirect, url_for, flash, session, Blueprint

from templates.base.database import get_db
from templates.base.requirements import permission_required, permissions_required_all, permissions_required_any
from templates.roles.permissions import Permissions

from werkzeug.utils import secure_filename
from datetime import datetime
import os
import jsonify


# Настройки для загрузки файлов
UPLOAD_FOLDER = 'static/uploads'
SCREENSHOTS_FOLDER = 'static/uploads/screenshots'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# app.config['SCREENSHOTS_FOLDER'] = SCREENSHOTS_FOLDER

# Создаем папки для загрузок при запуске
os.makedirs(SCREENSHOTS_FOLDER, exist_ok=True)

bluprint_articles_routes = Blueprint("articles", __name__)

@bluprint_articles_routes.route('/articles_list')
@permission_required(Permissions.articles_read)
def articles_list():
    db = get_db()
    articles = db.execute('''
        SELECT a.*, u.username as author_name 
        FROM articles a 
        JOIN users u ON a.author_id = u.id 
        WHERE a.is_published = 1
        ORDER BY a.updated_at DESC
    ''').fetchall()
    
    # Получаем уникальные категории для фильтра
    categories = db.execute('SELECT DISTINCT category FROM articles ORDER BY category').fetchall()
    category_list = [cat['category'] for cat in categories]
    
    # Статистика для сегодня
    today = datetime.now().strftime('%Y-%m-%d')
    today_updated = db.execute('''
        SELECT COUNT(*) as count FROM articles 
        WHERE DATE(updated_at) = ? AND is_published = 1
    ''', (today,)).fetchone()['count']
    
    return render_template('knowledge/articles/articles.html', 
                         articles=articles, 
                         categories=category_list,
                         today_updated=today_updated)



@bluprint_articles_routes.route('/add_article', methods=['GET', 'POST'])
@permission_required(Permissions.articles_manage)
def add_article():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        category = request.form['category']
        tags = request.form.get('tags', '')
        is_published = request.form.get('is_published') == '1'
        
        # Валидация
        if not title or not content:
            flash('Заголовок и содержание обязательны для заполнения', 'error')
            return render_template('knowledge/articles/add_article.html')
        
        db = get_db()
        try:
            # Создаем статью
            cursor = db.execute('''
                INSERT INTO articles (title, content, category, tags, author_id, is_published)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (title, content, category, tags, session['user_id'], is_published))
            article_id = cursor.lastrowid
            
            # Обработка загруженных скриншотов
            if 'screenshots' in request.files:
                files = request.files.getlist('screenshots')
                uploaded_count = 0
                
                for file in files:
                    if file and file.filename:  # Проверяем, что файл выбран
                        screenshot_info = save_screenshot(file, article_id)
                        if screenshot_info:
                            db.execute('''
                                INSERT INTO article_screenshots (article_id, filename, original_filename, file_size)
                                VALUES (?, ?, ?, ?)
                            ''', (article_id, screenshot_info['filename'], 
                                  screenshot_info['original_filename'], screenshot_info['file_size']))
                            uploaded_count += 1
                
                if uploaded_count > 0:
                    flash(f'Статья успешно создана! Загружено {uploaded_count} скриншотов.', 'success')
                else:
                    flash('Статья успешно создана!', 'success')
            
            db.commit()
            return redirect(url_for('articles.view_article', article_id=article_id))
            
        except Exception as e:
            db.rollback()
            flash(f'Ошибка при создании статьи: {str(e)}', 'error')
    
    return render_template('knowledge/articles/add_article.html')


@bluprint_articles_routes.route('/delete_article/<int:article_id>')
@permission_required(Permissions.articles_manage)
def delete_article(article_id):
    db = get_db()
    article = db.execute('SELECT * FROM articles WHERE id = ?', (article_id,)).fetchone()
    
    if not article:
        flash('Статья не найдена', 'error')
        return redirect(url_for('articles.articles_list'))
    
    # Проверяем права доступа
    if article['author_id'] != session['user_id'] and session['role'] != 'admin':
        flash('У вас нет прав для удаления этой статьи', 'error')
        return redirect(url_for('articles.articles_list'))
    
    try:
        # Удаляем связанные скриншоты
        screenshots = db.execute('SELECT * FROM article_screenshots WHERE article_id = ?', (article_id,)).fetchall()
        for screenshot in screenshots:
            delete_screenshot(screenshot['id'])
        
        # Удаляем статью
        db.execute('DELETE FROM articles WHERE id = ?', (article_id,))
        db.commit()
        flash('Статья и все связанные скриншоты успешно удалены!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении статьи: {str(e)}', 'error')
    
    return redirect(url_for('articles.articles_list'))

# ========== МАРШРУТЫ ДЛЯ СКРИНШОТОВ СТАТЕЙ ==========

@bluprint_articles_routes.route('/edit_article/<int:article_id>', methods=['GET', 'POST'])
@permission_required(Permissions.articles_manage)
def edit_article(article_id):
    db = get_db()
    article = db.execute('SELECT * FROM articles WHERE id = ?', (article_id,)).fetchone()
    
    if not article:
        flash('Статья не найдена', 'error')
        return redirect(url_for('articles.articles_list'))
    
    # Проверяем права доступа
    if article['author_id'] != session['user_id'] and session['role'] != 'admin':
        flash('У вас нет прав для редактирования этой статьи', 'error')
        return redirect(url_for('articles.articles_list'))
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        category = request.form['category']
        tags = request.form.get('tags', '')
        is_published = request.form.get('is_published') == '1'
        
        if not title or not content:
            flash('Заголовок и содержание обязательны для заполнения', 'error')
            return render_template('knowledge/articles/edit_article.html', article=article, screenshots=get_article_screenshots(article_id))
        
        try:
            db.execute('''
                UPDATE articles SET 
                title=?, content=?, category=?, tags=?, is_published=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (title, content, category, tags, is_published, article_id))
            db.commit()
            
            # Обработка загруженных скриншотов
            if 'screenshots' in request.files:
                files = request.files.getlist('screenshots')
                for file in files:
                    if file and file.filename:  # Проверяем, что файл выбран
                        screenshot_info = save_screenshot(file, article_id)
                        if screenshot_info:
                            db.execute('''
                                INSERT INTO article_screenshots (article_id, filename, original_filename, file_size)
                                VALUES (?, ?, ?, ?)
                            ''', (article_id, screenshot_info['filename'], 
                                  screenshot_info['original_filename'], screenshot_info['file_size']))
                            db.commit()
            
            flash('Статья успешно обновлена!', 'success')
            return redirect(url_for('articles.view_article', article_id=article_id))
        except Exception as e:
            flash(f'Ошибка при обновлении статьи: {str(e)}', 'error')
    
    return render_template('knowledge/articles/edit_article.html', 
                         article=article, 
                         screenshots=get_article_screenshots(article_id))


@bluprint_articles_routes.route('/articles/<int:article_id>')
@permission_required(Permissions.articles_read)
def view_article(article_id):
    db = get_db()
    
    # Увеличиваем счетчик просмотров
    db.execute('UPDATE articles SET views = views + 1 WHERE id = ?', (article_id,))
    db.commit()
    
    article = db.execute('''
        SELECT a.*, u.username as author_name 
        FROM articles a 
        JOIN users u ON a.author_id = u.id 
        WHERE a.id = ?
    ''', (article_id,)).fetchone()
    
    if not article:
        flash('Статья не найдена', 'error')
        return redirect(url_for('articles.articles_list'))
    
    return render_template('knowledge/articles/view_article.html', 
                         article=article, 
                         screenshots=get_article_screenshots(article_id))


@bluprint_articles_routes.route('/articles/screenshot/<int:screenshot_id>/description', methods=['POST'])
@permission_required(Permissions.articles_manage)
def update_screenshot_description(screenshot_id):
    """Обновляет описание скриншота"""
    db = get_db()
    data = request.get_json()
    
    if not data or 'description' not in data:
        return jsonify({'success': False, 'error': 'Неверные данные'})
    
    screenshot = db.execute('SELECT * FROM article_screenshots WHERE id = ?', (screenshot_id,)).fetchone()
    if not screenshot:
        return jsonify({'success': False, 'error': 'Скриншот не найден'})
    
    # Проверяем права доступа
    article = db.execute('SELECT * FROM articles WHERE id = ?', (screenshot['article_id'],)).fetchone()
    if article['author_id'] != session['user_id'] and session['role'] != 'admin':
        return jsonify({'success': False, 'error': 'Нет прав доступа'})
    
    try:
        db.execute('''
            UPDATE article_screenshots SET description = ? WHERE id = ?
        ''', (data['description'], screenshot_id))
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bluprint_articles_routes.route('/delete_screenshot/<int:screenshot_id>')
@permission_required(Permissions.articles_manage)
def delete_screenshot(screenshot_id):
    """Удаляет скриншот"""
    db = get_db()
    screenshot = db.execute('SELECT * FROM article_screenshots WHERE id = ?', (screenshot_id,)).fetchone()
    
    if not screenshot:
        flash('Скриншот не найден', 'error')
        return redirect(url_for('articles.articles_list'))
    
    # Проверяем права доступа
    article = db.execute('SELECT * FROM articles WHERE id = ?', (screenshot['article_id'],)).fetchone()
    if article['author_id'] != session['user_id'] and session['role'] != 'admin':
        flash('У вас нет прав для удаления этого скриншота', 'error')
        return redirect(url_for('articles.view_article', article_id=article['id']))
    
    if delete_screenshot(screenshot_id):
        flash('Скриншот успешно удален!', 'success')
    else:
        flash('Ошибка при удалении скриншота', 'error')
    
    return redirect(url_for('articles.edit_article', article_id=article['id']))

def allowed_file(filename):
    """Проверяет, разрешено ли расширение файла"""
    if not '.' in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    
    # Проверяем расширение
    if ext not in ALLOWED_EXTENSIONS:
        return False
    
    return True

def save_screenshot(file, article_id):
    """Сохраняет скриншот и возвращает информацию о файле"""
    if file and file.filename and allowed_file(file.filename):
        # Проверяем размер файла
        file.seek(0, 2)  # Перемещаемся в конец файла
        file_size = file.tell()
        file.seek(0)  # Возвращаемся в начало
        
        if file_size > MAX_FILE_SIZE:
            raise ValueError(f"Файл слишком большой. Максимальный размер: {MAX_FILE_SIZE // (1024*1024)}MB")
        
        filename = secure_filename(file.filename)
        # Создаем уникальное имя файла
        import uuid
        unique_filename = f"{article_id}_{uuid.uuid4().hex[:8]}_{filename}"
        filepath = os.path.join(SCREENSHOTS_FOLDER, unique_filename)
        
        # Сохраняем файл
        file.save(filepath)
        
        return {
            'filename': unique_filename,
            'original_filename': filename,
            'file_size': file_size,
            'filepath': filepath
        }
    return None

def get_article_screenshots(article_id):
    """Получает все скриншоты для статьи"""
    db = get_db()
    return db.execute('''
        SELECT * FROM article_screenshots 
        WHERE article_id = ? 
        ORDER BY upload_order, created_at
    ''', (article_id,)).fetchall()

def delete_screenshot(screenshot_id):
    """Удаляет скриншот"""
    db = get_db()
    screenshot = db.execute('SELECT * FROM article_screenshots WHERE id = ?', (screenshot_id,)).fetchone()
    
    if screenshot:
        # Удаляем файл
        try:
            os.remove(os.path.join(SCREENSHOTS_FOLDER, screenshot['filename']))
        except OSError:
            pass  # Файл уже удален или не существует
        
        # Удаляем запись из БД
        db.execute('DELETE FROM article_screenshots WHERE id = ?', (screenshot_id,))
        db.commit()
        return True
    return False
