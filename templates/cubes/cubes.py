# Добавьте импорт
from templates.base.organization_utils import get_user_organizations_list, has_organization_access

# Обновите функции
@bluprint_cubes_routes.route('/cubes')
@permission_required(Permissions.cubes_read)
def cubes():
    db = get_db()
    user_id = session.get('user_id')
    
    if session.get('role') in ['admin', 'manager']:
        cubes_list = db.execute('''
            SELECT c.*, o.name as organization_name 
            FROM cubes c
            LEFT JOIN organizations o ON c.organization_id = o.id
            ORDER BY c.name
        ''').fetchall()
    else:
        cubes_list = db.execute('''
            SELECT c.*, o.name as organization_name 
            FROM cubes c
            LEFT JOIN organizations o ON c.organization_id = o.id
            WHERE c.organization_id IN (
                SELECT organization_id FROM user_organizations WHERE user_id = ?
            ) OR c.organization_id IS NULL
            ORDER BY c.name
        ''', (user_id,)).fetchall()
    
    organizations = get_user_organizations_list(user_id, include_all=True)
    organization_filter = request.args.get('organization_id', type=int)

    return render_template('cubes/cubes.html',
                         cubes=cubes_list,
                         organizations=organizations,
                         selected_org=organization_filter)
