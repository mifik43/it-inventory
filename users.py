from flask import render_template, request, redirect, url_for, flash, session, Blueprint
from database import get_db, find_user_id_by_name
from werkzeug.security import generate_password_hash, check_password_hash

from functools import wraps
from requirements import admin_required, login_required, permission_required, permissions_required_all, permissions_required_any
from database_roles import read_all_roles, read_roles_for_user, save_roles_to_user

from permissions import Permissions, Role

bluprint_user_routes = Blueprint("users", __name__)

@bluprint_user_routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()
        
        if user and check_password_hash(user['password_hash'], password):

            user_roles = read_roles_for_user(user['id'], db)
            effective_permissions = Role.get_effective_permissions(user_roles)

            session['logged_in'] = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['permissions'] = list(effective_permissions)
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
    db = get_db()
    users_list = db.execute('SELECT id, username, role, created_at FROM users').fetchall()
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
    db = get_db()
    roles = read_all_roles(db)
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        selected_roles = parse_incoming_roles(roles, request)
        # Проверяем, существует ли пользователь с таким именем
        existing_user = db.execute(
            'SELECT id FROM users WHERE username = ?', (username,)
        ).fetchone()
        
        if existing_user:
            flash('Пользователь с таким именем уже существует', 'error')
            return render_template('auth/create_user.html', roles=roles)
        
        # Хешируем пароль и создаем пользователя
        password_hash = generate_password_hash(password)
            
        try:
            db.execute(
                'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                (username, password_hash, role)
            )

            user_id = find_user_id_by_name(username, db)
            save_roles_to_user(user_id, selected_roles, db)

            db.commit()
            flash('Пользователь успешно создан!', 'success')
            return redirect(url_for('users.users'))
        except Exception as e:
            flash(f'Ошибка при создании пользователя: {str(e)}', 'error')
        
        return render_template('auth/create_user.html')

    return render_template('auth/create_user.html', roles=roles)



@bluprint_user_routes.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@permission_required(Permissions.users_manage)
def edit_user(user_id):
    db = get_db()

    roles = read_all_roles(db)
    user_roles = read_roles_for_user(user_id)
    
    if request.method == 'POST':
        username = request.form['username']
        role = request.form['role']
        new_password = request.form.get('new_password', '')

        selected_roles = parse_incoming_roles(roles, request)
        if selected_roles == set(user_roles):
            print("Роли не требуют обновления")
        else:
            print("Обновляем роли")
            save_roles_to_user(user_id, selected_roles, db)

        try:
            # Обновляем основные данные пользователя
            if new_password:
                # Если указан новый пароль, обновляем его
                password_hash = generate_password_hash(new_password)
                db.execute(
                    'UPDATE users SET username = ?, role = ?, password_hash = ? WHERE id = ?',
                    (username, role, password_hash, user_id)
                )
                flash('Данные пользователя и пароль успешно обновлены!', 'success')
            else:
                # Если пароль не указан, обновляем только остальные данные
                db.execute(
                    'UPDATE users SET username = ?, role = ? WHERE id = ?',
                    (username, role, user_id)
                )
                flash('Данные пользователя успешно обновлены!', 'success')
            
            db.commit()
            return redirect(url_for('users.users'))
        except Exception as e:
            flash(f'Ошибка при обновлении пользователя: {str(e)}', 'error')
    
    user = db.execute('SELECT id, username, role FROM users WHERE id = ?', (user_id,)).fetchone()
    for role in roles:
        for user_role in user_roles:
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
    
    db = get_db()
    try:
        db.execute('DELETE FROM users WHERE id = ?', (user_id,))
        db.commit()
        flash('Пользователь успешно удален!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении пользователя: {str(e)}', 'error')
    
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
        
        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE id = ?', (session['user_id'],)
        ).fetchone()
        
        if user and check_password_hash(user['password_hash'], current_password):
            new_password_hash = generate_password_hash(new_password)
            db.execute(
                'UPDATE users SET password_hash = ? WHERE id = ?',
                (new_password_hash, session['user_id'])
            )
            db.commit()
            flash('Пароль успешно изменен!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Текущий пароль указан неверно', 'error')
    
    return render_template('auth/change_password.html')
