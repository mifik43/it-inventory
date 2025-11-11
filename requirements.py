from functools import wraps
from flask import flash, session, redirect, url_for

from database_roles import read_roles_for_user
from permissions import Permissions, Role

# Декоратор для проверки авторизации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Пожалуйста, войдите в систему', 'error')
            return redirect(url_for('users.login'))
        return f(*args, **kwargs)
    return decorated_function

# Декоратор для проверки прав администратора
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Пожалуйста, войдите в систему', 'error')
            return redirect(url_for('users.login'))
        if session.get('role') != 'admin':
            flash('Недостаточно прав для выполнения этого действия', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# проверка одного конкретного разрешения
def permission_required(p:Permissions):
    def check_permission(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            
            print(f"Проверяем {p} для пользователя с id={session['user_id']} ({session['username']})")
            roles:Role = read_roles_for_user(session['user_id'])
            effective_permissions = Role.get_effective_permissions(roles)

            is_granted = p in effective_permissions

            if (is_granted):
                print("Можно")
            else:
                print("Нельзя")
                flash('Недостаточно прав для выполнения этого действия', 'error')
                return redirect(url_for('index'))

            result = function(*args, **kwargs)
            return result
        return wrapper
    return check_permission

# наличие любого разрешения из списка разрешений разрешает действие
def permissions_required_any(permissions:list[Permissions]):
    def check_permission(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            
            print(f"Проверяем наличие хотябы одного из {permissions} для пользователя с id={session['user_id']} ({session['username']})")
            roles:Role = read_roles_for_user(session['user_id'])
            effective_permissions = Role.get_effective_permissions(roles)

            #
            is_granted = any(p in effective_permissions for p in permissions)
            if (is_granted):
                print("Можно")
            else:
                print("Нельзя")
                flash('Недостаточно прав для выполнения этого действия', 'error')
                return redirect(url_for('index'))

            result = function(*args, **kwargs)
            return result
        return wrapper
    return check_permission

# требует наличия у пользователя всех разрешений
def permissions_required_all(permissions:list[Permissions]):
    def check_permission(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            
            print(f"Проверяем наличие всех разрешений из {permissions} для пользователя с id={session['user_id']} ({session['username']})")
            roles:Role = read_roles_for_user(session['user_id'])

            effective_permissions = Role.get_effective_permissions(roles)


            is_granted = all(p in effective_permissions for p in permissions)
            if (is_granted):
                print("Можно")
            else:
                print("Нельзя")
                flash('Недостаточно прав для выполнения этого действия', 'error')
                return redirect(url_for('index'))

            result = function(*args, **kwargs)
            return result
        return wrapper
    return check_permission