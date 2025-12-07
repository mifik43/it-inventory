# Добавьте импорт
from templates.base.organization_utils import get_user_organizations_list, has_organization_access

# Обновите функции
@bluprint_wtware_routes.route('/wtware')
def wtware_list():
    db = get_db()
    user_id = session.get('user_id')
    
    if session.get('role') in ['admin', 'manager']:
        wtware_list = db.execute('''
            SELECT w.*, o.name as organization_name 
            FROM wtware_configs w
            LEFT JOIN organizations o ON w.organization_id = o.id
            ORDER BY w.name
        ''').fetchall()
    else:
        wtware_list = db.execute('''
            SELECT w.*, o.name as organization_name 
            FROM wtware_configs w
            LEFT JOIN organizations o ON w.organization_id = o.id
            WHERE w.organization_id IN (
                SELECT organization_id FROM user_organizations WHERE user_id = ?
            ) OR w.organization_id IS NULL
            ORDER BY w.name
        ''', (user_id,)).fetchall()
    
    return render_template('wtware/wtware_list.html', 
                         wtware_list=wtware_list)