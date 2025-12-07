from flask import render_template, request, redirect, url_for, flash, session, Blueprint

from templates.base.database import get_db
from templates.base.requirements import permission_required, permissions_required_all, permissions_required_any
from templates.roles.permissions import Permissions
from templates.base.organization_utils import get_user_organizations_list, has_organization_access

bluprint_devices_routes = Blueprint("devices", __name__)

@bluprint_devices_routes.route('/devices')
@permission_required(Permissions.devices_read)
def devices():
    db = get_db()
    devices = db.execute('''
        SELECT * FROM devices 
        ORDER BY created_at DESC
    ''').fetchall()
    return render_template('devices/devices.html', devices=devices)

@bluprint_devices_routes.route('/add_device', methods=['GET', 'POST'])
@permission_required(Permissions.devices_manage)
def add_device():
    if request.method == 'POST':
        name = request.form['name']
        model = request.form.get('model', '')  # Новое поле
        device_type = request.form['type']
        serial_number = request.form['serial_number']
        mac_address = request.form.get('mac_address', '')
        ip_address = request.form.get('ip_address', '')
        location = request.form['location']
        status = request.form['status']
        assigned_to = request.form.get('assigned_to', '')
        specifications = request.form.get('specifications', '')
        
        db = get_db()
        try:
            db.execute('''
                INSERT INTO devices 
                (name, model, type, serial_number, mac_address, ip_address, location, status, assigned_to, specifications)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, model, device_type, serial_number, mac_address, ip_address, location, status, assigned_to, specifications))
            db.commit()
            flash('Устройство успешно добавлено!', 'success')
            return redirect(url_for('devices.devices'))
        except Exception as e:
            flash(f'Ошибка при добавлении устройства: {str(e)}', 'error')
    
    return render_template('devices/add_device.html')

@bluprint_devices_routes.route('/edit_device/<int:device_id>', methods=['GET', 'POST'])
@permission_required(Permissions.devices_manage)
def edit_device(device_id):
    db = get_db()
    
    if request.method == 'POST':
        name = request.form['name']
        model = request.form.get('model', '')  # Новое поле
        device_type = request.form['type']
        serial_number = request.form['serial_number']
        mac_address = request.form.get('mac_address', '')
        ip_address = request.form.get('ip_address', '')
        location = request.form['location']
        status = request.form['status']
        assigned_to = request.form.get('assigned_to', '')
        specifications = request.form.get('specifications', '')
        
        try:
            db.execute('''
                UPDATE devices SET 
                name=?, model=?, type=?, serial_number=?, mac_address=?, ip_address=?, 
                location=?, status=?, assigned_to=?, specifications=?
                WHERE id=?
            ''', (name, model, device_type, serial_number, mac_address, ip_address, 
                  location, status, assigned_to, specifications, device_id))
            db.commit()
            flash('Устройство успешно обновлено!', 'success')
            return redirect(url_for('devices.devices'))
        except Exception as e:
            flash(f'Ошибка при обновлении устройства: {str(e)}', 'error')
    
    device = db.execute('SELECT * FROM devices WHERE id=?', (device_id,)).fetchone()
    return render_template('devices/edit_device.html', device=device)

@bluprint_devices_routes.route('/delete_device/<int:device_id>')
@permission_required(Permissions.devices_manage)
def delete_device(device_id):
    db = get_db()
    try:
        db.execute('DELETE FROM devices WHERE id=?', (device_id,))
        db.commit()
        flash('Устройство успешно удалено!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении устройства: {str(e)}', 'error')
    
    return redirect(url_for('devices.devices'))

@bluprint_devices_routes.route('/search')
@permission_required(Permissions.devices_read)
def search():
    query = request.args.get('q', '')
    db = get_db()
    
    devices = db.execute('''
        SELECT * FROM devices 
        WHERE name LIKE ? OR model LIKE ? OR serial_number LIKE ? OR assigned_to LIKE ?
        ORDER BY created_at DESC
    ''', (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%')).fetchall()
    
    return render_template('devices/devices.html', devices=devices, search_query=query)