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

def permissions_required(permissions:list[Permissions]):
    print(f"Создаю декоратор для проверки {permissions}")
    def check_permission(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            
            print(f"Проверяем {permissions} для пользователя с id={session['user_id']} ({session['username']})")
            roles:Role = read_roles_for_user(session['user_id'])


            is_granted = False
            for p in permissions:
                is_granted |= any(role.is_permission_granted(p) for role in roles)

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