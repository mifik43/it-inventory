from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from templates.base.database_helper import db
from models import User, Role, UserRole
from templates.base.requirements import login_required, get_current_user, permissions_required
from ..roles.permissions import Permissions
from ..roles.database_roles import read_roles_for_user, save_roles_to_user
from ..roles.permissions import Role as PermRole
from logger import logger

bluprint_user_routes = Blueprint('users', __name__, url_prefix='/users')

def update_effective_permissions():
    """Обновляет разрешения пользователя в сессии"""
    user_id = session.get('user_id')
    if user_id:
        user_roles = read_roles_for_user(user_id)
        effective_permissions = PermRole.get_effective_permissions(user_roles)
        session['permissions'] = [p.value for p in effective_permissions]

@bluprint_user_routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Проверка на пустые поля
        if not username or not password:
            flash('Введите имя пользователя и пароль', 'error')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(username=username).first()
        if user and user.is_active and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            update_effective_permissions()
            flash('Вход выполнен успешно!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')
    
    return render_template('auth/login.html')

@bluprint_user_routes.route('/logout')
def logout():
    session.clear()
    flash('Выход выполнен успешно!', 'success')
    logger.info("Пользователь вышел из системы")
    return redirect(url_for('index'))

@bluprint_user_routes.route('/profile')
@login_required
def profile():
    user = get_current_user()
    return render_template('auth/profile.html', user=user)

@bluprint_user_routes.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        user = get_current_user()
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not old_password or not new_password or not confirm_password:
            flash('Все поля обязательны для заполнения', 'error')
            return redirect(url_for('users.change_password'))
        
        if not check_password_hash(user.password_hash, old_password):
            flash('Неверный старый пароль', 'error')
        elif new_password != confirm_password:
            flash('Новые пароли не совпадают', 'error')
        elif len(new_password) < 6:
            flash('Пароль должен быть не менее 6 символов', 'error')
        else:
            user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            flash('Пароль успешно изменен', 'success')
            return redirect(url_for('users.profile'))
        
        return redirect(url_for('users.change_password'))
    
    return render_template('auth/change_password.html')

@bluprint_user_routes.route('/admin')
@permissions_required([Permissions.users_read, Permissions.users_manage])
def admin_panel():
    users = User.query.all()
    logger.info("Запрос на админскую панель")
    return render_template('auth/admin_panel.html', users=users)

@bluprint_user_routes.route('/admin/create', methods=['GET', 'POST'])
@permissions_required([Permissions.users_manage])
def create_user():
    all_roles = Role.query.all()
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        email = request.form.get('email')
        full_name = request.form.get('full_name')
        selected_roles = request.form.getlist('roles')
        
        
        if not username or not password:
            flash('Имя пользователя и пароль обязательны', 'error')
            return render_template('auth/create_user.html', roles=all_roles)
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует', 'error')
            logger.error("Попытка создания пользователя с существующим username: %s", username)
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
            db.session.flush()
            
            # Назначаем роли
            for role_id in selected_roles:
                user_role = UserRole(user_id=user.id, role_id=int(role_id))
                db.session.add(user_role)
            
            db.session.commit()
            flash('Пользователь успешно создан', 'success')
            logger.info("Новый пользователь создан: %s", username)
            return redirect(url_for('users.admin_panel'))
    
    # Для GET: все роли не отмечены
    for role in all_roles:
        role.checked = False
    
    return render_template('auth/create_user.html', roles=all_roles)

@bluprint_user_routes.route('/admin/edit/<int:user_id>', methods=['GET', 'POST'])
@permissions_required([Permissions.users_manage])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    all_roles = Role.query.all()
    user_role_ids = [ur.role_id for ur in UserRole.query.filter_by(user_id=user.id).all()]
    
    if request.method == 'POST':
        user.username = request.form.get('username')
        user.role = request.form.get('role')
        user.email = request.form.get('email')
        user.full_name = request.form.get('full_name')
        # Получаем статус из выпадающего списка
        is_active_val = request.form.get('is_active')
        user.is_active = True if is_active_val == '1' else False
        
        new_password = request.form.get('new_password')
        if new_password and len(new_password) >= 6:
            user.password_hash = generate_password_hash(new_password)
        elif new_password and len(new_password) < 6:
            flash('Новый пароль должен быть не менее 6 символов', 'error')
            return render_template('auth/edit_user.html', user=user, roles=all_roles)
        
        # Обновляем роли
        selected_roles = request.form.getlist('roles')
        UserRole.query.filter_by(user_id=user.id).delete()
        for role_id in selected_roles:
            user_role = UserRole(user_id=user.id, role_id=int(role_id))
            db.session.add(user_role)
        
        db.session.commit()
        flash('Пользователь успешно обновлен', 'success')
        return redirect(url_for('users.admin_panel'))
    
    for role in all_roles:
        role.checked = role.id in user_role_ids
    
    return render_template('auth/edit_user.html', user=user, roles=all_roles)

@bluprint_user_routes.route('/admin/delete/<int:user_id>', methods=['POST'])
@permissions_required([Permissions.users_manage])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    current_user = get_current_user()
    
    if user.id == current_user.id:
        flash('Вы не можете удалить свой собственный аккаунт', 'error')
        logger.error("Попытка удалить самого себя пользователем %s", current_user.username)
        return redirect(url_for('users.admin_panel'))
    
    db.session.delete(user)
    db.session.commit()
    flash('Пользователь успешно удален', 'success')
    logger.info("Пользователь %s удален", user.username)
    return redirect(url_for('users.admin_panel'))

@bluprint_user_routes.route('/users')
@permissions_required([Permissions.users_read, Permissions.users_manage])
def users():
    users_list = User.query.all()
    return render_template('auth/users.html', users=users_list)

@bluprint_user_routes.route('/admin/toggle_active/<int:user_id>', methods=['POST'])
@permissions_required([Permissions.users_manage])
def toggle_user_active(user_id):
    user = User.query.get_or_404(user_id)
    current_user = get_current_user()
    
    if user.id == current_user.id:
        flash('Вы не можете изменить статус своего собственного аккаунта', 'error')
        return redirect(url_for('users.admin_panel'))
    
    user.is_active = not user.is_active
    db.session.commit()
    status = 'активирован' if user.is_active else 'деактивирован'
    flash(f'Пользователь {user.username} {status}', 'success')
    return redirect(url_for('users.admin_panel'))