# Добавьте импорт
from templates.base.organization_utils import get_user_organizations_list, has_organization_access

# Обновите функции аналогично
@bluprint_guest_wifi_routes.route('/guest_wifi')
@permission_required(Permissions.guest_wifi_read)
def guest_wifi():
    db = get_db()
    user_id = session.get('user_id')
    
    if session.get('role') in ['admin', 'manager']:
        wifi_list = db.execute('''
            SELECT w.*, o.name as organization_name 
            FROM guest_wifi w
            LEFT JOIN organizations o ON w.organization_id = o.id
            ORDER BY w.created_at DESC
        ''').fetchall()
    else:
        wifi_list = db.execute('''
            SELECT w.*, o.name as organization_name 
            FROM guest_wifi w
            LEFT JOIN organizations o ON w.organization_id = o.id
            WHERE w.organization_id IN (
                SELECT organization_id FROM user_organizations WHERE user_id = ?
            ) OR w.organization_id IS NULL
            ORDER BY w.created_at DESC
        ''', (user_id,)).fetchall()
    
    organizations = get_user_organizations_list(user_id, include_all=True)
    organization_filter = request.args.get('organization_id', type=int)
    
    return render_template('guest_wifi/guest_wifi.html',
                         wifi_list=wifi_list,
                         organizations=organizations,
                         selected_org=organization_filter)

