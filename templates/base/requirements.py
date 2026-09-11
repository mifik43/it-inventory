from functools import wraps
from flask import flash, redirect, url_for, session, abort, request
from models import User
import inspect

from logger import logger
from templates.roles.database_roles import read_roles_for_user
from templates.roles.permissions import Role
from .module_registry import is_module_enabled

def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(int(user_id))
    return None

def get_current_user_permissions():
    user = get_current_user()
    if not user:
        return []
    user_roles = read_roles_for_user(user.id)
    user_permissions = Role.get_effective_permissions(user_roles)
    return list(user_permissions)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_current_user():
            flash('Требуется авторизация', 'error')
            abort(401)
        return f(*args, **kwargs)
    return decorated_function

def permissions_required(permissions):
    if not isinstance(permissions, (list, tuple)):
        permissions = [permissions]
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_permissions = get_current_user_permissions()
            has_permission = any(perm in user_permissions for perm in permissions)
            if not has_permission:
                flash('Недостаточно прав для доступа к этой странице', 'error')
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def permissions_required_all(permissions):
    if not isinstance(permissions, (list, tuple)):
        permissions = [permissions]
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_permissions = get_current_user_permissions()
            has_all_permissions = all(perm in user_permissions for perm in permissions)
            if not has_all_permissions:
                flash('Недостаточно прав для доступа к этой странице', 'error')
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def permission_required(permission):
    """Одиночное разрешение (для обратной совместимости)"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
                      
            user_permissions = get_current_user_permissions()
            if permission not in user_permissions:
                flash('Недостаточно прав для доступа к этой странице', 'error')
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def module_enabled(module_key):
    from functools import wraps
    from flask import flash, redirect, url_for
    """Блокирует доступ к страницам отключённого модуля."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not is_module_enabled(module_key):
                flash('Этот модуль отключён администратором', 'warning')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator