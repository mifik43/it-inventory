from flask import session
from templates.base.database import get_db

def get_user_organizations_list(user_id, include_all=False):
    """Получить список организаций для пользователя"""
    db = get_db()
    
    # Проверяем, является ли пользователь супер-админом или менеджером
    user = db.execute('SELECT role FROM users WHERE id = ?', (user_id,)).fetchone()
    
    if not user:
        return []
    
    if user['role'] in ['admin', 'manager'] and include_all:
        # Супер-админы и менеджеры видят все организации
        return db.execute('SELECT id, name FROM organizations ORDER BY name').fetchall()
    else:
        # Обычные пользователи видят только свои организации
        return db.execute('''
            SELECT o.id, o.name FROM organizations o
            INNER JOIN user_organizations uo ON o.id = uo.organization_id
            WHERE uo.user_id = ?
            ORDER BY o.name
        ''', (user_id,)).fetchall()

def has_organization_access(user_id, organization_id):
    """Проверяет, есть ли у пользователя доступ к организации"""
    db = get_db()
    
    # Проверяем роль пользователя
    user = db.execute('SELECT role FROM users WHERE id = ?', (user_id,)).fetchone()
    
    if not user:
        return False
    
    if user['role'] in ['admin', 'manager']:
        return True
    
    # Проверяем связь в таблице user_organizations
    access = db.execute('''
        SELECT 1 FROM user_organizations 
        WHERE user_id = ? AND organization_id = ?
    ''', (user_id, organization_id)).fetchone()
    
    return access is not None

def check_organization_access_decorator(func):
    """Декоратор для проверки доступа к организации"""
    from functools import wraps
    from flask import flash, redirect, url_for, session
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        user_id = session.get('user_id')
        
        # Если в kwargs есть organization_id, проверяем доступ
        if 'organization_id' in kwargs:
            if not has_organization_access(user_id, kwargs['organization_id']):
                flash('У вас нет доступа к этой организации', 'error')
                return redirect(url_for('index'))
        
        # Если в kwargs есть id сущности, проверяем через parent_id
        elif 'id' in kwargs or 'item_id' in kwargs:
            # Эта логика будет переопределена в каждом конкретном декораторе
            pass
            
        return func(*args, **kwargs)
    return wrapper