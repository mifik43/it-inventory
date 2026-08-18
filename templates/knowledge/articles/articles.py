from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from templates.base.database_helper import db
from templates.base.requirements import permissions_required
from templates.roles.permissions import Permissions
from models import Article, User, ArticleScreenshot
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import uuid

# Настройки для загрузки файлов
UPLOAD_FOLDER = 'static/uploads'
SCREENSHOTS_FOLDER = 'static/uploads/screenshots'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

# Создаем папки для загрузок при запуске
os.makedirs(SCREENSHOTS_FOLDER, exist_ok=True)

bluprint_articles_routes = Blueprint("articles", __name__)

@bluprint_articles_routes.route('/articles_list')
@permissions_required(Permissions.articles_read)
def articles_list():
    # Получаем список статей с автором
    articles = db.session.query(Article, User.username.label('author_name'))\
        .join(User, Article.author_id == User.id)\
        .filter(Article.is_published == True)\
        .order_by(Article.updated_at.desc())\
        .all()

    # Уникальные категории (только опубликованные)
    categories = db.session.query(Article.category)\
        .filter(Article.is_published == True)\
        .distinct()\
        .order_by(Article.category)\
        .all()
    category_list = [cat[0] for cat in categories]  # извлекаем значения

    # Статистика: количество статей, обновлённых сегодня
    today = datetime.now().date()
    today_updated = db.session.query(db.func.count(Article.id))\
        .filter(db.func.date(Article.updated_at) == today)\
        .filter(Article.is_published == True)\
        .scalar() or 0

    return render_template('knowledge/articles/articles.html',
                           articles=articles,
                           categories=category_list,
                           today_updated=today_updated)


@bluprint_articles_routes.route('/add_article', methods=['GET', 'POST'])
@permissions_required(Permissions.articles_manage)
def add_article():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        category = request.form.get('category', '').strip()
        tags = request.form.get('tags', '').strip()
        is_published = request.form.get('is_published') == '1'

        if not title or not content:
            flash('Заголовок и содержание обязательны для заполнения', 'error')
            return render_template('knowledge/articles/add_article.html')

        # Создаём статью через ORM
        article = Article(
            title=title,
            content=content,
            category=category,
            tags=tags,
            author_id=session['user_id'],
            is_published=is_published
        )
        db.session.add(article)
        db.session.flush()  # чтобы получить article.id до коммита

        # Обработка скриншотов
        uploaded_count = 0
        if 'screenshots' in request.files:
            files = request.files.getlist('screenshots')
            for file in files:
                if file and file.filename:
                    screenshot_info = save_screenshot(file, article.id)
                    if screenshot_info:
                        screenshot = ArticleScreenshot(
                            article_id=article.id,
                            filename=screenshot_info['filename'],
                            original_filename=screenshot_info['original_filename'],
                            file_size=screenshot_info['file_size']
                        )
                        db.session.add(screenshot)
                        uploaded_count += 1

        try:
            db.session.commit()
            flash(f'Статья успешно создана! {"Загружено " + str(uploaded_count) + " скриншотов." if uploaded_count else ""}', 'success')
            return redirect(url_for('articles.view_article', article_id=article.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при создании статьи: {str(e)}', 'error')

    return render_template('knowledge/articles/add_article.html')


@bluprint_articles_routes.route('/delete_article/<int:article_id>')
@permissions_required(Permissions.articles_manage)
def delete_article(article_id):
    article = Article.query.get(article_id)
    if not article:
        flash('Статья не найдена', 'error')
        return redirect(url_for('articles.articles_list'))

    # Проверка прав
    if article.author_id != session['user_id'] and session.get('role') != 'admin':
        flash('У вас нет прав для удаления этой статьи', 'error')
        return redirect(url_for('articles.articles_list'))

    try:
        # Удаляем связанные скриншоты (файлы и записи)
        for screenshot in article.screenshots:
            delete_screenshot_file(screenshot.filename)
        # Удаляем статью (каскадное удаление скриншотов, если настроено в модели)
        db.session.delete(article)
        db.session.commit()
        flash('Статья и все связанные скриншоты успешно удалены!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении статьи: {str(e)}', 'error')

    return redirect(url_for('articles.articles_list'))


@bluprint_articles_routes.route('/edit_article/<int:article_id>', methods=['GET', 'POST'])
@permissions_required(Permissions.articles_manage)
def edit_article(article_id):
    article = Article.query.get(article_id)
    if not article:
        flash('Статья не найдена', 'error')
        return redirect(url_for('articles.articles_list'))

    if article.author_id != session['user_id'] and session.get('role') != 'admin':
        flash('У вас нет прав для редактирования этой статьи', 'error')
        return redirect(url_for('articles.articles_list'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        category = request.form.get('category', '').strip()
        tags = request.form.get('tags', '').strip()
        is_published = request.form.get('is_published') == '1'

        if not title or not content:
            flash('Заголовок и содержание обязательны для заполнения', 'error')
            return render_template('knowledge/articles/edit_article.html',
                                   article=article,
                                   screenshots=article.screenshots)

        # Обновляем поля
        article.title = title
        article.content = content
        article.category = category
        article.tags = tags
        article.is_published = is_published
        article.updated_at = datetime.utcnow()

        # Обработка новых скриншотов
        if 'screenshots' in request.files:
            files = request.files.getlist('screenshots')
            for file in files:
                if file and file.filename:
                    screenshot_info = save_screenshot(file, article.id)
                    if screenshot_info:
                        screenshot = ArticleScreenshot(
                            article_id=article.id,
                            filename=screenshot_info['filename'],
                            original_filename=screenshot_info['original_filename'],
                            file_size=screenshot_info['file_size']
                        )
                        db.session.add(screenshot)

        try:
            db.session.commit()
            flash('Статья успешно обновлена!', 'success')
            return redirect(url_for('articles.view_article', article_id=article.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении статьи: {str(e)}', 'error')

    return render_template('knowledge/articles/edit_article.html',
                           article=article,
                           screenshots=article.screenshots)


@bluprint_articles_routes.route('/articles/<int:article_id>')
@permissions_required(Permissions.articles_read)
def view_article(article_id):
    # Увеличиваем счётчик просмотров
    article = Article.query.get(article_id)
    if not article:
        flash('Статья не найдена', 'error')
        return redirect(url_for('articles.articles_list'))

    article.views += 1
    db.session.commit()

    # Получаем автора
    author = User.query.get(article.author_id)

    return render_template('knowledge/articles/view_article.html',
                           article=article,
                           screenshots=article.screenshots,
                           author_name=author.username if author else 'Неизвестен')


@bluprint_articles_routes.route('/articles/screenshot/<int:screenshot_id>/description', methods=['POST'])
@permissions_required(Permissions.articles_manage)
def update_screenshot_description(screenshot_id):
    data = request.get_json()
    if not data or 'description' not in data:
        return jsonify({'success': False, 'error': 'Неверные данные'})

    screenshot = ArticleScreenshot.query.get(screenshot_id)
    if not screenshot:
        return jsonify({'success': False, 'error': 'Скриншот не найден'})

    # Проверка прав
    article = Article.query.get(screenshot.article_id)
    if article.author_id != session['user_id'] and session.get('role') != 'admin':
        return jsonify({'success': False, 'error': 'Нет прав доступа'})

    try:
        screenshot.description = data['description']
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@bluprint_articles_routes.route('/delete_screenshot/<int:screenshot_id>')
@permissions_required(Permissions.articles_manage)
def delete_screenshot(screenshot_id):
    screenshot = ArticleScreenshot.query.get(screenshot_id)
    if not screenshot:
        flash('Скриншот не найден', 'error')
        return redirect(url_for('articles.articles_list'))

    article = Article.query.get(screenshot.article_id)
    if article.author_id != session['user_id'] and session.get('role') != 'admin':
        flash('У вас нет прав для удаления этого скриншота', 'error')
        return redirect(url_for('articles.view_article', article_id=article.id))

    try:
        # Удаляем файл
        delete_screenshot_file(screenshot.filename)
        db.session.delete(screenshot)
        db.session.commit()
        flash('Скриншот успешно удален!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении скриншота: {str(e)}', 'error')

    return redirect(url_for('articles.edit_article', article_id=article.id))


# ========== Вспомогательные функции ==========

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_screenshot(file, article_id):
    if file and file.filename and allowed_file(file.filename):
        # Проверяем размер
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        if file_size > MAX_FILE_SIZE:
            raise ValueError(f"Файл слишком большой. Максимальный размер: {MAX_FILE_SIZE // (1024*1024)}MB")

        filename = secure_filename(file.filename)
        unique_filename = f"{article_id}_{uuid.uuid4().hex[:8]}_{filename}"
        filepath = os.path.join(SCREENSHOTS_FOLDER, unique_filename)
        file.save(filepath)

        return {
            'filename': unique_filename,
            'original_filename': filename,
            'file_size': file_size,
            'filepath': filepath
        }
    return None


def delete_screenshot_file(filename):
    """Удаляет физический файл скриншота"""
    try:
        os.remove(os.path.join(SCREENSHOTS_FOLDER, filename))
    except OSError:
        pass  