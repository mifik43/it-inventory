from flask import render_template, request, redirect, url_for, flash, session, Blueprint
from database import get_db
from werkzeug.security import generate_password_hash, check_password_hash

from functools import wraps
from requirements import admin_required, login_required
from database_roles import read_all_roles

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
            session['logged_in'] = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
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
@admin_required
def users():
    db = get_db()
    users_list = db.execute('SELECT id, username, role, created_at FROM users').fetchall()
    return render_template('auth/users.html', users=users_list)


@bluprint_user_routes.route('/create_user', methods=['GET', 'POST'])
@admin_required
def create_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        db = get_db()
        
        # Проверяем, существует ли пользователь с таким именем
        existing_user = db.execute(
            'SELECT id FROM users WHERE username = ?', (username,)
        ).fetchone()
        
        if existing_user:
            flash('Пользователь с таким именем уже существует', 'error')
            return render_template('auth/create_user.html')
        
        # Хешируем пароль и создаем пользователя
        password_hash = generate_password_hash(password)
            
        try:
            db.execute(
                'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                (username, password_hash, role)
            )
            db.commit()
            flash('Пользователь успешно создан!', 'success')
            return redirect(url_for('users.users'))
        except Exception as e:
            flash(f'Ошибка при создании пользователя: {str(e)}', 'error')
        
        return render_template('auth/create_user.html')

    return render_template('auth/create_user.html')



@bluprint_user_routes.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    db = get_db()

    roles = read_all_roles(db)
    
    if request.method == 'POST':
        username = request.form['username']
        role = request.form['role']
        new_password = request.form.get('new_password', '')

        selected_roles = set()
        for r in roles:
            if str(k) in request.form.keys():
                selected_roles.add(r)
                print(f"Для пользователя {username} добавлена роль {r.name}")

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
    return render_template('edit_user.html', user=user, roles=roles)

@bluprint_user_routes.route('/delete_user/<int:user_id>')
@admin_required
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
@login_required
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
