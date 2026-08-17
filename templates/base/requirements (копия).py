from functools import wraps
from flask import flash, redirect, url_for, session, abort, request
from models import User
import inspect

from logger import logger

from ..roles.database_roles import read_roles_for_user
from ..roles.permissions import Role

def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(int(user_id))
    return None

def get_current_user_permissions():
    user = get_current_user()
    user_roles = read_roles_for_user(user.id)
    user_permissions = Role.get_effective_permissions(user_roles)
    return list(user_permissions)

def login_required(f):
    """Декоратор для проверки аутентификации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_current_user():
            flash('Требуется авторизация', 'error')
            logger.info(f"Flash: Требуется авторизация (error) ({f.__name__})")
            print('Запрос без авторизации. Перенаправляем на страницу авторизации')
            abort(401)
        return f(*args, **kwargs)
    return decorated_function




def permissions_required(permissions):
    if not isinstance(permissions, (list, tuple)):
        permissions = [permissions]
    """Декоратор для проверки наличия хотя бы одного из указанных разрешений"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            # Получаем разрешения пользователя
            user_permissions = get_current_user_permissions()
            
            # Проверяем, есть ли у пользователя хотя бы одно из требуемых разрешений
            has_permission = any(perm in user_permissions for perm in permissions)
            
            if not has_permission:
                flash('Недостаточно прав для доступа к этой странице', 'error')
                logger.info(f"Flash: Недостаточно прав для доступа к этой странице (error) ({f.__name__})")
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def permissions_required_all(permissions):
    if not isinstance(permissions, (list, tuple)):
        permissions = [permissions]
    """Декоратор для проверки наличия всех указанных разрешений"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            
            # Получаем разрешения пользователя
            user_permissions = get_current_user_permissions()
            
            # Проверяем, есть ли у пользователя все требуемые разрешения
            has_all_permissions = all(perm in user_permissions for perm in permissions)
            
            if not has_all_permissions:
                flash('Недостаточно прав для доступа к этой странице', 'error')
                logger.info(f"Flash: Недостаточно прав для доступа к этой странице (error) ({f.__name__})")
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Декоратор для проверки ролей

def roles_required(*roles):
    """Декоратор для проверки наличия одной из указанных ролей"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current_user = get_current_user()
            
            if current_user.role not in roles:
                flash(f'Доступ запрещен. Требуется одна из ролей: {", ".join(roles)}', 'error')
                logger.info(f"Flash: Доступ запрещен. Требуется одна из ролей: {', '.join(roles)} (error) ({f.__name__})")
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def permission_required(permission):
    """Декоратор для проверки одного разрешения (старый стиль для обратной совместимости)"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current_user = get_current_user()
            
            # Получаем разрешения пользователя
            user_permissions = get_current_user_permissions()
            logger.debug(f"Проверка разрешения '{permission}' для пользователя {current_user.username} (ID: {current_user.id}). Разрешения пользователя: {user_permissions}")
            
            # Проверяем наличие разрешения
            if permission not in user_permissions:
                flash('Недостаточно прав для доступа к этой странице', 'error')
                logger.error(f"Недостаточно прав для доступа к этой странице ({f.__name__})")
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def permissions_required_all(permissions):
    """Декоратор для проверки наличия всех указанных разрешений"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current_user = get_current_user()
            # Получаем разрешения пользователя
            user_permissions = get_current_user_permissions()
            
            # Проверяем, есть ли у пользователя все требуемые разрешения
            has_all_permissions = all(perm in user_permissions for perm in permissions)
            
            if not has_all_permissions:
                flash('Недостаточно прав для доступа к этой странице', 'error')
                logger.info(f"Flash: Недостаточно прав для доступа к этой странице (error) ({f.__name__})")
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Декоратор для проверки ролей

def roles_required(*roles):
    """Декоратор для проверки наличия одной из указанных ролей"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current_user = get_current_user()
            
            if current_user.role not in roles:
                flash(f'Доступ запрещен. Требуется одна из ролей: {", ".join(roles)}', 'error')
                logger.info(f"Flash: Доступ запрещен. Требуется одна из ролей: {', '.join(roles)} (error) ({f.__name__})")
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Декоратор для проверки владения ресурсом

def owner_required(model_class, id_param='id'):
    """Декоратор для проверки, что пользователь является владельцем ресурса"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current_user = get_current_user()
            
            # Если пользователь администратор, разрешаем доступ
            if current_user.role == 'admin':
                return f(*args, **kwargs)
            
            # Получаем ID ресурса из параметров маршрута
            resource_id = kwargs.get(id_param)
            if not resource_id:
                flash('Ресурс не найден', 'error')
                logger.info(f"Flash: Ресурс не найден (error) ({f.__name__})")
                return redirect(url_for('index'))
            
            # Получаем ресурс из БД
            from templates.base.database import get_db
            db = get_db()
            
            # Определяем таблицу на основе имени класса модели
            table_name = model_class.__name__.lower() + 's'
            
            # Проверяем, существует ли ресурс и принадлежит ли он текущему пользователю
            resource = db.execute(
                f'SELECT * FROM {table_name} WHERE id = ? AND user_id = ?',
                (resource_id, current_user.id)
            ).fetchone()
            
            if not resource:
                flash('Доступ запрещен. Вы не являетесь владельцем этого ресурса', 'error')
                logger.info(f"Flash: Доступ запрещен. Вы не являетесь владельцем этого ресурса (error) ({f.__name__})")
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Декоратор для проверки, что пользователь активен

def active_user_required(f):
    """Декоратор для проверки, что учетная запись пользователя активна"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user = get_current_user()
        
        # Проверяем, активен ли пользователь
        from templates.base.database import get_db
        db = get_db()
        
        user_data = db.execute(
            'SELECT is_active FROM users WHERE id = ?',
            (current_user.id,)
        ).fetchone()
        
        if not user_data or user_data['is_active'] == 0:
            flash('Ваша учетная запись неактивна', 'error')
            logger.info(f"Flash: Ваша учетная запись неактивна (error) ({f.__name__})")
            return redirect(url_for('users.logout'))
        
        return f(*args, **kwargs)
    return decorated_function

# Вспомогательные функции для проверки прав в шаблонах

def has_permission(permission_name):
    current_user = get_current_user()
    """Проверяет наличие разрешения у текущего пользователя (для использования в шаблонах)"""
    
    user_permissions = current_user.get_permissions()
    return permission_name in user_permissions


def has_any_permission(permission_names):
    current_user = get_current_user()
    """Проверяет наличие хотя бы одного разрешения из списка (для использования в шаблонах)"""
    
    current_user = get_current_user()
    user_permissions = current_user.get_permissions()
    return any(perm in user_permissions for perm in permission_names)
    
def has_all_permissions(permission_names):
    current_user = get_current_user()
    """Проверяет наличие всех разрешений из списка (для использования в шаблонах)"""
    
    user_permissions = current_user.get_permissions()
    return all(perm in user_permissions for perm in permission_names)
    
    return False