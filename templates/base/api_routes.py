from flask import Blueprint, jsonify, session
from templates.base.database import get_db

bluprint_api_routes = Blueprint("api", __name__)

@bluprint_api_routes.route('/api/user/organizations')
def get_user_organizations():
    """API для получения организаций текущего пользователя"""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'organizations': []})
    
    db = get_db()
    
    # Проверяем роль пользователя
    user = db.execute('SELECT role FROM users WHERE id = ?', (user_id,)).fetchone()
    
    if user['role'] in ['admin', 'manager']:
        # Супер-админы и менеджеры видят все организации
        organizations = db.execute('SELECT id, name FROM organizations ORDER BY name').fetchall()
    else:
        # Обычные пользователи видят только свои организации
        organizations = db.execute('''
            SELECT o.id, o.name FROM organizations o
            INNER JOIN user_organizations uo ON o.id = uo.organization_id
            WHERE uo.user_id = ?
            ORDER BY o.name
        ''', (user_id,)).fetchall()
    
    return jsonify({'organizations': [dict(org) for org in organizations]})