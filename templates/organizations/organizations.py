from flask import render_template, request, redirect, url_for, flash, session, Blueprint
from templates.base.database import get_db
from templates.base.requirements import permission_required
from templates.roles.permissions import Permissions
from templates.base.organization_utils import get_user_organizations_list, has_organization_access
bluprint_organizations_routes = Blueprint("organizations", __name__)

def init_user_organizations_table():
    """Инициализирует таблицу связей пользователей и организаций, если она не существует"""
    db = get_db()
    try:
        # Проверяем, существует ли таблица
        db.execute("SELECT 1 FROM user_organizations LIMIT 1")
    except Exception:
        # Таблица не существует, создаем
        db.execute('''
            CREATE TABLE IF NOT EXISTS user_organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                organization_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
                UNIQUE(user_id, organization_id)
            )
        ''')
        db.execute('CREATE INDEX IF NOT EXISTS idx_user_organizations_user ON user_organizations(user_id)')
        db.execute('CREATE INDEX IF NOT EXISTS idx_user_organizations_org ON user_organizations(organization_id)')
        db.commit()

def get_user_organizations(user_id):
    """Получить список ID организаций пользователя"""
    init_user_organizations_table()
    db = get_db()
    rows = db.execute('SELECT organization_id FROM user_organizations WHERE user_id = ?', 
                     (user_id,)).fetchall()
    # Преобразуем sqlite3.Row в список словарей
    return [row['organization_id'] for row in rows]

def has_organization_access(user_id, org_id):
    """Проверить доступ пользователя к организации"""
    # Сначала проверяем, является ли пользователь супер-админом
    if is_superadmin():
        return True
    
    # Проверяем, есть ли глобальный доступ
    if has_global_organization_access():
        return True
    
    # Проверяем доступ через таблицу связей
    init_user_organizations_table()
    db = get_db()
    access = db.execute('SELECT 1 FROM user_organizations WHERE user_id = ? AND organization_id = ?',
                       (user_id, org_id)).fetchone()
    
    return access is not None

def is_superadmin():
    """Проверяет, является ли текущий пользователь супер-админом"""
    user_role = session.get('role')
    return user_role == 'admin'

def has_global_organization_access():
    """Проверяет, имеет ли текущий пользователь глобальный доступ ко всем организациям"""
    # Проверяем через права в сессии
    permissions = session.get('permissions', [])
    # Предположим, что есть специальное право для глобального доступа
    # Например, Permissions.organizations_view_all
    # Пока проверяем по роли
    user_role = session.get('role')
    return user_role in ['admin', 'manager']

@bluprint_organizations_routes.route('/organizations')
@permission_required(Permissions.organizations_read)
def organizations():
    db = get_db()
    user_id = session.get('user_id')
    
    # Получаем фильтр из GET-параметров
    organization_filter = request.args.get('organization_id', type=int)
    
    # Базовый запрос
    query = '''
        SELECT o.*, 
               COUNT(DISTINCT d.id) as devices_count,
               COUNT(DISTINCT p.id) as providers_count,
               COUNT(DISTINCT t.id) as todos_count
        FROM organizations o
        LEFT JOIN devices d ON o.id = d.organization_id
        LEFT JOIN providers p ON o.id = p.organization_id
        LEFT JOIN todos t ON o.id = t.organization_id
    '''
    
    where_clauses = []
    params = []
    
    # Проверяем права доступа
    if session.get('role') not in ['admin', 'manager']:
        # Ограничиваем доступом пользователя
        where_clauses.append('''
            o.id IN (
                SELECT organization_id FROM user_organizations WHERE user_id = ?
            )
        ''')
        params.append(user_id)
    
    # Добавляем фильтр по организации (если нужно)
    if organization_filter:
        where_clauses.append('o.id = ?')
        params.append(organization_filter)
    
    # Собираем запрос
    if where_clauses:
        query += ' WHERE ' + ' AND '.join(where_clauses)
    
    query += '''
        GROUP BY o.id
        ORDER BY 
            CASE o.type
                WHEN 'ООО' THEN 1
                WHEN 'ИП' THEN 2
                WHEN 'Самозанятый' THEN 3
                ELSE 4
            END,
            o.name
    '''
    
    organizations_list = db.execute(query, tuple(params)).fetchall()
    
    # Получаем все организации для фильтра (для админов/менеджеров)
    if session.get('role') in ['admin', 'manager']:
        filter_organizations = db.execute('SELECT id, name FROM organizations ORDER BY name').fetchall()
    else:
        filter_organizations = get_user_organizations_list(user_id)
    
    return render_template('organizations/organizations.html', 
                         organizations=organizations_list,
                         filter_organizations=filter_organizations,
                         selected_org=organization_filter,
                         show_all=session.get('role') in ['admin', 'manager'])


@bluprint_organizations_routes.route('/add_organization', methods=['GET', 'POST'])
@permission_required(Permissions.organizations_manage)
def add_organization():
    init_user_organizations_table()
    
    if request.method == 'POST':
        name = request.form['name']
        org_type = request.form['type']
        inn = request.form.get('inn', '')
        contact_person = request.form.get('contact_person', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        address = request.form.get('address', '')
        notes = request.form.get('notes', '')
        
        if not name:
            flash('Название организации обязательно для заполнения', 'error')
            return render_template('organizations/add_organization.html')
        
        db = get_db()
        try:
            cursor = db.execute('''
                INSERT INTO organizations (name, type, inn, contact_person, phone, email, address, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, org_type, inn, contact_person, phone, email, address, notes))
            db.commit()
            
            org_id = cursor.lastrowid
            user_id = session.get('user_id')
            
            # Автоматически даем доступ создателю
            db.execute('INSERT OR IGNORE INTO user_organizations (user_id, organization_id) VALUES (?, ?)',
                      (user_id, org_id))
            db.commit()
            
            flash('Организация успешно добавлена!', 'success')
            return redirect(url_for('organizations.organizations'))
        except Exception as e:
            flash(f'Ошибка при добавлении организации: {str(e)}', 'error')
    
    return render_template('organizations/add_organization.html')

@bluprint_organizations_routes.route('/edit_organization/<int:org_id>', methods=['GET', 'POST'])
@permission_required(Permissions.organizations_manage)
def edit_organization(org_id):
    init_user_organizations_table()
    db = get_db()
    user_id = session.get('user_id')
    
    # Проверяем доступ
    if not has_organization_access(user_id, org_id):
        flash('У вас нет доступа к этой организации', 'error')
        return redirect(url_for('organizations.organizations'))
    
    org = db.execute('SELECT * FROM organizations WHERE id = ?', (org_id,)).fetchone()
    if not org:
        flash('Организация не найдена', 'error')
        return redirect(url_for('organizations.organizations'))
    
    if request.method == 'POST':
        name = request.form['name']
        org_type = request.form['type']
        inn = request.form.get('inn', '')
        contact_person = request.form.get('contact_person', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        address = request.form.get('address', '')
        notes = request.form.get('notes', '')
        
        if not name:
            flash('Название организации обязательно для заполнения', 'error')
            return render_template('organizations/edit_organization.html', org=org)
        
        try:
            db.execute('''
                UPDATE organizations SET 
                name=?, type=?, inn=?, contact_person=?, phone=?, email=?, address=?, notes=?
                WHERE id=?
            ''', (name, org_type, inn, contact_person, phone, email, address, notes, org_id))
            db.commit()
            flash('Данные организации успешно обновлены!', 'success')
            return redirect(url_for('organizations.organizations'))
        except Exception as e:
            flash(f'Ошибка при обновлении организации: {str(e)}', 'error')
    
    return render_template('organizations/edit_organization.html', org=org)

@bluprint_organizations_routes.route('/delete_organization/<int:org_id>')
@permission_required(Permissions.organizations_manage)
def delete_organization(org_id):
    init_user_organizations_table()
    db = get_db()
    user_id = session.get('user_id')
    
    # Проверяем доступ
    if not has_organization_access(user_id, org_id):
        flash('У вас нет доступа к этой организации', 'error')
        return redirect(url_for('organizations.organizations'))
    
    # Проверяем использование в задачах
    tasks_count = db.execute('SELECT COUNT(*) as count FROM todos WHERE organization_id = ?', 
                            (org_id,)).fetchone()
    if tasks_count['count'] > 0:
        flash('Невозможно удалить организацию, так как она используется в задачах', 'error')
        return redirect(url_for('organizations.organizations'))
    
    try:
        db.execute('DELETE FROM user_organizations WHERE organization_id = ?', (org_id,))
        db.execute('DELETE FROM organizations WHERE id = ?', (org_id,))
        db.commit()
        flash('Организация успешно удалена!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении организации: {str(e)}', 'error')
    
    return redirect(url_for('organizations.organizations'))

@bluprint_organizations_routes.route('/organization_users/<int:org_id>')
@permission_required(Permissions.organizations_manage)
def organization_users(org_id):
    """Просмотр пользователей, имеющих доступ к организации"""
    init_user_organizations_table()
    db = get_db()
    user_id = session.get('user_id')
    
    # Проверяем доступ
    if not has_organization_access(user_id, org_id):
        flash('У вас нет доступа к этой организации', 'error')
        return redirect(url_for('organizations.organizations'))
    
    org = db.execute('SELECT * FROM organizations WHERE id = ?', (org_id,)).fetchone()
    
    # Пользователи с доступом
    users_with_access = db.execute('''
        SELECT u.id, u.username, u.email, u.role, uo.created_at
        FROM users u
        INNER JOIN user_organizations uo ON u.id = uo.user_id
        WHERE uo.organization_id = ?
        ORDER BY u.username
    ''', (org_id,)).fetchall()
    
    # Все пользователи
    all_users = db.execute('''
        SELECT id, username, email, role
        FROM users
        WHERE id NOT IN (
            SELECT user_id FROM user_organizations WHERE organization_id = ?
        )
        ORDER BY username
    ''', (org_id,)).fetchall()
    
    return render_template('organizations/organization_users.html',
                         org=org,
                         users_with_access=users_with_access,
                         all_users=all_users)

@bluprint_organizations_routes.route('/add_user_to_organization/<int:org_id>/<int:user_id>')
@permission_required(Permissions.organizations_manage)
def add_user_to_organization(org_id, user_id):
    init_user_organizations_table()
    db = get_db()
    current_user_id = session.get('user_id')
    
    # Проверяем доступ
    if not has_organization_access(current_user_id, org_id):
        flash('У вас нет доступа к этой организации', 'error')
        return redirect(url_for('organizations.organizations'))
    
    try:
        db.execute('INSERT OR IGNORE INTO user_organizations (user_id, organization_id) VALUES (?, ?)',
                  (user_id, org_id))
        db.commit()
        flash('Пользователь успешно добавлен к организации', 'success')
    except Exception as e:
        flash(f'Ошибка при добавлении пользователя: {str(e)}', 'error')
    
    return redirect(url_for('organizations.organization_users', org_id=org_id))

@bluprint_organizations_routes.route('/remove_user_from_organization/<int:org_id>/<int:user_id>')
@permission_required(Permissions.organizations_manage)
def remove_user_from_organization(org_id, user_id):
    init_user_organizations_table()
    db = get_db()
    current_user_id = session.get('user_id')
    
    # Проверяем доступ
    if not has_organization_access(current_user_id, org_id):
        flash('У вас нет доступа к этой организации', 'error')
        return redirect(url_for('organizations.organizations'))
    
    # Не позволяем удалить себя, если это последний пользователь с доступом
    users_count = db.execute('SELECT COUNT(*) as count FROM user_organizations WHERE organization_id = ?',
                            (org_id,)).fetchone()
    
    if users_count['count'] <= 1 and current_user_id == user_id:
        flash('Нельзя удалить последнего пользователя с доступом к организации', 'error')
        return redirect(url_for('organizations.organization_users', org_id=org_id))
    
    try:
        db.execute('DELETE FROM user_organizations WHERE user_id = ? AND organization_id = ?',
                  (user_id, org_id))
        db.commit()
        flash('Пользователь удален из организации', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении пользователя: {str(e)}', 'error')
    
    return redirect(url_for('organizations.organization_users', org_id=org_id))

@bluprint_organizations_routes.route('/my_organizations')
@permission_required(Permissions.organizations_read)
def my_organizations():
    """Страница только с организациями текущего пользователя"""
    init_user_organizations_table()
    db = get_db()
    user_id = session.get('user_id')
    
    organizations_list = db.execute('''
        SELECT o.* FROM organizations o
        INNER JOIN user_organizations uo ON o.id = uo.organization_id
        WHERE uo.user_id = ?
        ORDER BY 
            CASE o.type
                WHEN 'ООО' THEN 1
                WHEN 'ИП' THEN 2
                WHEN 'Самозанятый' THEN 3
                ELSE 4
            END,
            o.name
    ''', (user_id,)).fetchall()
    
    return render_template('organizations/my_organizations.html', 
                         organizations=organizations_list)

@bluprint_organizations_routes.route('/set_global_access/<int:user_id>/<int:enable>')
@permission_required(Permissions.organizations_manage)
def set_global_access(user_id, enable):
    """Установить глобальный доступ пользователю ко всем организациям"""
    db = get_db()
    
    try:
        if enable:
            db.execute('UPDATE users SET role = ? WHERE id = ?', ('manager', user_id))
            flash('Пользователю предоставлен глобальный доступ к организациям', 'success')
        else:
            db.execute('UPDATE users SET role = ? WHERE id = ?', ('user', user_id))
            flash('Глобальный доступ к организациям отозван', 'success')
        db.commit()
    except Exception as e:
        flash(f'Ошибка при изменении прав: {str(e)}', 'error')
    
    return redirect(request.referrer or url_for('organizations.organizations'))