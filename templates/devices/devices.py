from flask import render_template, request, redirect, url_for, flash, session, Blueprint
from templates.base.database import get_db
from templates.base.requirements import permission_required
from templates.roles.permissions import Permissions
from templates.base.organization_utils import get_user_organizations_list, has_organization_access

bluprint_devices_routes = Blueprint("devices", __name__)

@bluprint_devices_routes.route('/devices')
@permission_required(Permissions.devices_read)
def devices():
    db = get_db()
    user_id = session.get('user_id')
    
    # Получаем фильтр из GET-параметров
    organization_filter = request.args.get('organization_id', type=int)
    
    # Проверяем, есть ли колонка organization_id в таблице devices
    try:
        db.execute("SELECT organization_id FROM devices LIMIT 1")
        has_organization_column = True
    except sqlite3.OperationalError:
        has_organization_column = False
    
    if has_organization_column:
        # Базовый запрос с организацией
        query = '''
            SELECT d.*, o.name as organization_name 
            FROM devices d
            LEFT JOIN organizations o ON d.organization_id = o.id
        '''
        params = []
        
        where_clauses = []
        
        # Проверяем права доступа
        if session.get('role') not in ['admin', 'manager']:
            # Ограничиваем доступом пользователя
            where_clauses.append('''
                (d.organization_id IN (
                    SELECT organization_id FROM user_organizations WHERE user_id = ?
                ) OR d.organization_id IS NULL)
            ''')
            params.append(user_id)
        
        # Добавляем фильтр по организации
        if organization_filter:
            where_clauses.append('d.organization_id = ?')
            params.append(organization_filter)
        
        # Собираем запрос
        if where_clauses:
            query += ' WHERE ' + ' AND '.join(where_clauses)
        
        query += ' ORDER BY d.created_at DESC'
        
        devices_list = db.execute(query, tuple(params)).fetchall()
    else:
        # Если колонки organization_id еще нет, показываем все устройства
        devices_list = db.execute('''
            SELECT d.*, NULL as organization_name 
            FROM devices d
            ORDER BY d.created_at DESC
        ''').fetchall()
    
    # Получаем организации для фильтра
    organizations = get_user_organizations_list(user_id, include_all=True)
    
    return render_template('devices/devices.html', 
                         devices=devices_list,
                         organizations=organizations,
                         selected_org=organization_filter,
                         has_organization_column=has_organization_column)



@bluprint_devices_routes.route('/add_device', methods=['GET', 'POST'])
@permission_required(Permissions.devices_manage)
def add_device():
    db = get_db()
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        name = request.form['name']
        device_type = request.form['type']
        serial_number = request.form.get('serial_number', '')
        inventory_number = request.form.get('inventory_number', '')
        status = request.form.get('status', 'В работе')
        location = request.form.get('location', '')
        notes = request.form.get('notes', '')
        organization_id = request.form.get('organization_id', None)
        
        if not name:
            flash('Название устройства обязательно', 'error')
            return redirect(url_for('devices.add_device'))
        
        if organization_id and not has_organization_access(user_id, organization_id):
            flash('У вас нет доступа к выбранной организации', 'error')
            return redirect(url_for('devices.add_device'))
        
        try:
            db.execute('''
                INSERT INTO devices (name, type, serial_number, inventory_number, 
                                   status, location, notes, organization_id, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, device_type, serial_number, inventory_number, 
                  status, location, notes, organization_id, user_id))
            db.commit()
            flash('Устройство успешно добавлено!', 'success')
            return redirect(url_for('devices.devices'))
        except Exception as e:
            flash(f'Ошибка при добавлении устройства: {str(e)}', 'error')
    
    organizations = get_user_organizations_list(user_id)
    
    return render_template('devices/add_device.html', organizations=organizations)

@bluprint_devices_routes.route('/edit_device/<int:device_id>', methods=['GET', 'POST'])
@permission_required(Permissions.devices_manage)
def edit_device(device_id):
    db = get_db()
    user_id = session.get('user_id')
    
    device = db.execute('SELECT * FROM devices WHERE id = ?', (device_id,)).fetchone()
    
    if not device:
        flash('Устройство не найдено', 'error')
        return redirect(url_for('devices.devices'))
    
    # Проверяем доступ к организации устройства
    if device['organization_id'] and not has_organization_access(user_id, device['organization_id']):
        flash('У вас нет доступа к этому устройству', 'error')
        return redirect(url_for('devices.devices'))
    
    if request.method == 'POST':
        name = request.form['name']
        device_type = request.form['type']
        serial_number = request.form.get('serial_number', '')
        inventory_number = request.form.get('inventory_number', '')
        status = request.form.get('status', 'В работе')
        location = request.form.get('location', '')
        notes = request.form.get('notes', '')
        organization_id = request.form.get('organization_id', None)
        
        if not name:
            flash('Название устройства обязательно', 'error')
            return redirect(url_for('devices.edit_device', device_id=device_id))
        
        # Проверяем доступ к новой организации
        if organization_id and organization_id != device['organization_id']:
            if not has_organization_access(user_id, organization_id):
                flash('У вас нет доступа к выбранной организации', 'error')
                return redirect(url_for('devices.edit_device', device_id=device_id))
        
        try:
            db.execute('''
                UPDATE devices SET 
                name=?, type=?, serial_number=?, inventory_number=?, 
                status=?, location=?, notes=?, organization_id=?
                WHERE id=?
            ''', (name, device_type, serial_number, inventory_number, 
                  status, location, notes, organization_id, device_id))
            db.commit()
            flash('Устройство успешно обновлено!', 'success')
            return redirect(url_for('devices.devices'))
        except Exception as e:
            flash(f'Ошибка при обновлении устройства: {str(e)}', 'error')
    
    organizations = get_user_organizations_list(user_id)
    
    return render_template('devices/edit_device.html', 
                         device=device,
                         organizations=organizations)