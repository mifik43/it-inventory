from functools import wraps
from flask import flash, session, redirect, url_for

from templates.roles.database_roles import read_roles_for_user
from templates.roles.permissions import Permissions, Role

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

def get_user_permissions():
    """Получение всех разрешений текущего пользователя"""
    if 'user_id' not in session:
        return set()
    
    user_roles = read_roles_for_user(session['user_id'])
    user_permissions = set()
    
    for role in user_roles:
        user_permissions.update(role.permissions)
    
    return user_permissions

def check_permission(permission_name):
    """Проверка наличия разрешения у текущего пользователя"""
    if isinstance(permission_name, str):
        try:
            permission = Permissions[permission_name]
        except KeyError:
            return False
    else:
        permission = permission_name
    
    user_permissions = get_user_permissions()
    return permission in user_permissions

# Декоратор для проверки разрешений
def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not check_permission(permission):
                flash('У вас недостаточно прав для доступа к этой странице', 'error')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def permissions_required_any(permissions):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_permissions = get_user_permissions()
            for permission in permissions:
                if permission in user_permissions:
                    return f(*args, **kwargs)
            flash('У вас недостаточно прав для доступа к этой странице', 'error')
            return redirect(url_for('index'))
        return decorated_function
    return decorator

def permissions_required_all(permissions):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_permissions = get_user_permissions()
            for permission in permissions:
                if permission not in user_permissions:
                    flash('У вас недостаточно прав для доступа к этой странице', 'error')
                    return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def check_permission_any(permission_names):
    """
    Проверяет, есть ли у текущего пользователя хотя бы одно из указанных разрешений
    Используется в шаблонах для отображения элементов интерфейса
    """
    from templates.auth.users import get_effective_permissions
    
    if 'user_id' not in session:
        return False
    
    user_permissions = get_effective_permissions()
    
    # Преобразуем строки в объекты Permissions если нужно
    permissions_to_check = []
    for perm_name in permission_names:
        if isinstance(perm_name, str):
            try:
                perm = Permissions[perm_name]
                permissions_to_check.append(perm)
            except KeyError:
                pass
        else:
            permissions_to_check.append(perm_name)
    
    # Проверяем наличие хотя бы одного разрешения
    for perm in permissions_to_check:
        if perm in user_permissions:
            return True
    
    return False