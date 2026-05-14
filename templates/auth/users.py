from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from templates.base.database_helper import db
from models import User

from templates.base.requirements import login_required, get_current_user, permissions_required
from ..roles.permissions import Permissions

from logger import logger


bluprint_user_routes = Blueprint('users', __name__, url_prefix='/users')

@bluprint_user_routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # Используем SQLAlchemy ORM вместо сырых SQL-запросов
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            if user.is_active:
                session['user_id'] = user.id
                flash('Вход выполнен успешно!', 'success')
                logger.info(f"Вход пользователя {username} выполнен успешно")
                return redirect(url_for('index'))
            else:
                flash('Аккаунт отключен', 'error')
                logger.warning("Попытка входа на неактивный аккаунт для пользователя: {}".format(username))
        else:
            flash('Неверное имя пользователя или пароль', 'error')
            logger.error(f"Неудачная попытка входа с именем пользователя: {username}")
    return render_template('auth/login.html')
@bluprint_user_routes.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Выход выполнен успешно!', 'success')
    logger.info("Пользователь вышел из системы")
    return redirect(url_for('index'))

@bluprint_user_routes.route('/profile')
@login_required
def profile(): # пропало, но пока оставляем
    return render_template('auth/profile.html', user=get_current_user())

@bluprint_user_routes.route('/change_password', methods=['POST'])
@permissions_required([Permissions.users_manage])
def change_password():
    logger.info("Попытка изменения пароля для пользователя с ID: {}".format(get_current_user().id))
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    user = get_current_user()
    if not check_password_hash(user.password_hash, old_password):
        flash('Неверный старый пароль', 'error')
        logger.error("Проверка старого пароля не прошла")
    elif new_password != confirm_password:
        flash('Новые пароли не совпадают', 'error')
        logger.warning("Новые пароли для пользователя {} не совпадают".format(user.username))
    elif len(new_password) < 6:
        flash('Пароль должен быть не менее 6 символов', 'error')
        logger.error(f"Пароль слишком короткий (менее 6 символов) для пользователя {user.username}")
    else:
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash('Пароль успешно изменен', 'success')
        logger.info("Пароль успешно обновлен для пользователя {}".format(user.username))
    return redirect(url_for('users.profile'))

# Админские маршруты
@bluprint_user_routes.route('/admin')
@permissions_required([Permissions.users_read, Permissions.users_manage])
def admin_panel():
    users = User.query.all()
    logger.info("Запрос на доступ к админской панели выполнен")

    # Логирование количества пользователей для отладки
    user_count = len(users)
    logger.debug(f"Количество пользователей в базе: {user_count}")

    return render_template('auth/admin_panel.html', users=users)

@bluprint_user_routes.route('/admin/create', methods=['GET', 'POST'])
@permissions_required([Permissions.users_manage])
def create_user():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        email = request.form.get('email')
        full_name = request.form.get('full_name')
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Пользователь с таким именем уже существует', 'error')
            logger.error(f"Попытка создания пользователя с существующим username: {username}")
        else:
            user = User(
                username=username,
                password_hash=generate_password_hash(password),
                role=role,
                email=email,
                full_name=full_name,
                is_active=True
            )
            db.session.add(user)
            db.session.commit()
            flash('Пользователь успешно создан', 'success')
            logger.info("Новый пользователь успешно создан: {}".format(username))
            return redirect(url_for('users.admin_panel'))
    
    return render_template('auth/create_user.html')

@bluprint_user_routes.route('/admin/edit/<int:user_id>', methods=['GET', 'POST'])
@permissions_required([Permissions.users_manage])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    logger.info(f"Попытка редактирования пользователя с ID: {user_id}")
    
    if request.method == 'POST':
        user.username = request.form.get('username')
        user.role = request.form.get('role')
        user.email = request.form.get('email')
        user.full_name = request.form.get('full_name')
        user.is_active = request.form.get('is_active') == 'on'
        
        new_password = request.form.get('new_password')
        if new_password:
            logger.info(f"Пароль для пользователя {user.username} будет изменен")
            user.password_hash = generate_password_hash(new_password)
            logger.debug("Новый хэш пароля успешно сгенерирован")
        
        db.session.commit()
        logger.info(f"Редактирование пользователя {user.username} завершено успешно")

        flash('Пользователь успешно обновлен', 'success')
    else:
        logger.debug(f"Запрос GET для редактирования пользователя с ID: {user_id}")
    return render_template('auth/edit_user.html', user=user)

@bluprint_user_routes.route('/admin/delete/<int:user_id>', methods=['POST'])
@permissions_required([Permissions.users_manage])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)


    current_user = get_current_user()

    # Проверяем, не пытается ли пользователь удалить себя
    if user.id == current_user.id:
        flash('Вы не можете удалить свой собственный аккаунт', 'error')
        logger.error("Вы не можете удалить свой собственный аккаунт")
        return redirect(url_for('users.admin_panel'))
    
    db.session.delete(user)
    db.session.commit()
    flash('Пользователь успешно удален', 'success')
    logger.info(f"Пользователь {user.username} успешно удалён из системы")

    return redirect(url_for('users.admin_panel'))

@bluprint_user_routes.route('/users')
@permissions_required([Permissions.users_read, Permissions.users_manage])
def users():
    logger.info("Запрос на список пользователей выполнен")
    users_list = User.query.all()
    return render_template('auth/users.html', users=users_list)