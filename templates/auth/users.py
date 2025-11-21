from flask import render_template, request, redirect, url_for, flash, session, Blueprint
from werkzeug.security import generate_password_hash, check_password_hash

from functools import wraps
from templates.base.requirements import admin_required, login_required, permission_required, permissions_required_all, permissions_required_any
from templates.roles.database_roles import read_all_roles, read_roles_for_user, save_roles_to_user

from templates.roles.permissions import Permissions, Role

from templates.auth.user import User, find_user_by_name, find_user_by_id

from sqlalchemy.orm import Session
from sqlalchemy import select
from templates.base.db import get_session

bluprint_user_routes = Blueprint("users", __name__)

# обновление разрешения пользователя, на случай, если он настраивал сам себя
def update_effective_permissions():
    user = find_user_by_id(session['user_id'])
    session['permissions'] = list(user.get_effective_permissions())

@bluprint_user_routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user:User = find_user_by_name(username)

        if user and user.verify_password(password):
            session['logged_in'] = True
            session['user_id'] = user.id
            session['username'] = user.name
            update_effective_permissions()
            flash('Вы успешно вошли в систему!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')
    
    return render_template('auth/login.html')

@bluprint_user_routes.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'success')
    return redirect(url_for('index'))

# ========== МАРШРУТЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ==========

@bluprint_user_routes.route('/users')
@permissions_required_any([Permissions.users_read, Permissions.users_manage])
def users():
    with get_session() as s:
        users_list = s.query(User).all()
        return render_template('auth/users.html', users=users_list)

def parse_incoming_roles(all_roles:list[Role], request):
    selected_roles = set()
    for r in all_roles:
        if str(r.id) in request.form.keys():
            selected_roles.add(r)
    
    return selected_roles

@bluprint_user_routes.route('/create_user', methods=['GET', 'POST'])
@permission_required(Permissions.users_manage)
def create_user():
    with get_session() as s:
        
        roles = s.query(Role).all()
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']

            selected_roles = parse_incoming_roles(roles, request)

            # Проверяем, существует ли пользователь с таким именем
            existing_user = find_user_by_name(username)
            
            if existing_user:
                flash('Пользователь с таким именем уже существует', 'error')
                return render_template('auth/create_user.html', roles=roles)
            
            # Хешируем пароль и создаем пользователя
            password_hash = generate_password_hash(password)
                
            try:
                user = User()
                user.name = username
                user.password = password_hash
                user.roles = list(selected_roles)
                s.add(user)
                s.commit()
                flash('Пользователь успешно создан!', 'success')
                return redirect(url_for('users.users'))
            except Exception as e:
                flash(f'Ошибка при создании пользователя: {str(e)}', 'error')
            
            return render_template('auth/create_user.html')

        return render_template('auth/create_user.html', roles=roles)



@bluprint_user_routes.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@permission_required(Permissions.users_manage)
def edit_user(user_id):

    with get_session() as s:
        roles = s.query(Role).all()
        user = find_user_by_id(user_id, s)
        print(f"Редактируем пользователя {user.name}")
    
    
        if request.method == 'POST':
            username = request.form['username']
            role = request.form['role']
            new_password = request.form.get('new_password', '')

            selected_roles = parse_incoming_roles(roles, request)

            user.roles = list(selected_roles)

            try:
                # Обновляем основные данные пользователя
                if new_password:
                    # Если указан новый пароль, обновляем его
                    user.password = generate_password_hash(new_password)
                
                user.name = username
                
                s.commit()
                print("Данные пользователя успешно обновлены")
                flash('Данные пользователя успешно обновлены!', 'success')
                # обновляем разрешения пользователя, на случай, если он настраивал сам себя
                update_effective_permissions()
                return redirect(url_for('users.users'))
            except Exception as e:
                flash(f'Ошибка при обновлении пользователя: {str(e)}', 'error')
                return redirect(url_for('users.users'))
        
        for role in roles:
            for user_role in user.roles:
                if role.id == user_role.id:
                    role.checked = "checked"

        return render_template('auth/edit_user.html', user=user, roles=roles)

@bluprint_user_routes.route('/delete_user/<int:user_id>')
@permission_required(Permissions.users_manage)
def delete_user(user_id):
    # Запрещаем удаление самого себя
    if user_id == session.get('user_id'):
        flash('Вы не можете удалить свою собственную учетную запись', 'error')
        return redirect(url_for('users.users'))
    
    with get_session() as s:
        user = find_user_by_id(user_id, s)
        s.delete(user)
        s.commit()
        flash('Пользователь успешно удален!', 'success')
    
    return redirect(url_for('users.users'))

@bluprint_user_routes.route('/change_password', methods=['GET', 'POST'])
@permission_required(Permissions.users_manage)
def change_password():
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        if new_password != confirm_password:
            flash('Новый пароль и подтверждение не совпадают', 'error')
            return render_template('auth/change_password.html')
        with get_session() as s:
            user = find_user_by_id(session['user_id'], s)
        
        
        if user and user.verify_password(current_password):
            new_password_hash = generate_password_hash(new_password)
            user.password = new_password_hash
            s.commit()
            flash('Пароль успешно изменен!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Текущий пароль указан неверно', 'error')
    
    return render_template('auth/change_password.html')
