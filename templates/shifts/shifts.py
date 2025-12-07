# Добавьте импорт
from templates.base.organization_utils import get_user_organizations_list, has_organization_access

# Обновите функции
@bluprint_shifts_routes.route('/shifts')
@permission_required(Permissions.shifts_read)
def shifts_list():
    db = get_db()
    user_id = session.get('user_id')
    
    if session.get('role') in ['admin', 'manager']:
        shifts = db.execute('''
            SELECT s.*, u.username, o.name as organization_name 
            FROM shifts s
            JOIN users u ON s.user_id = u.id
            LEFT JOIN organizations o ON s.organization_id = o.id
            ORDER BY s.shift_date DESC
        ''').fetchall()
    else:
        shifts = db.execute('''
            SELECT s.*, u.username, o.name as organization_name 
            FROM shifts s
            JOIN users u ON s.user_id = u.id
            LEFT JOIN organizations o ON s.organization_id = o.id
            WHERE s.organization_id IN (
                SELECT organization_id FROM user_organizations WHERE user_id = ?
            ) OR s.organization_id IS NULL
            ORDER BY s.shift_date DESC
        ''', (user_id,)).fetchall()
    
    organizations = get_user_organizations_list(user_id, include_all=True)
    organization_filter = request.args.get('organization_id', type=int)
    
    return render_template('shifts/shifts.html',
                         shifts=shifts,
                         organizations=organizations,
                         selected_org=organization_filter)