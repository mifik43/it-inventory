from flask import render_template, request, redirect, url_for, flash, Blueprint
from sqlalchemy import or_

from templates.base.database_helper import db
from templates.base.requirements import permissions_required
from templates.roles.permissions import Permissions
from models import Device

bluprint_devices_routes = Blueprint("devices", __name__)

@bluprint_devices_routes.route('/devices')
@permissions_required([Permissions.devices_read])
def devices():
    devices = Device.query.order_by(Device.created_at.desc()).all()
    return render_template('devices/devices.html', devices=devices)

@bluprint_devices_routes.route('/add_device', methods=['GET', 'POST'])
@permissions_required([Permissions.devices_manage])
def add_device():
    if request.method == 'POST':
        name = request.form['name']
        model = request.form.get('model', '')
        device_type = request.form['type']
        serial_number = request.form['serial_number']
        mac_address = request.form.get('mac_address', '')
        ip_address = request.form.get('ip_address', '')
        location = request.form['location']
        status = request.form['status']
        assigned_to = request.form.get('assigned_to', '')
        specifications = request.form.get('specifications', '')

        try:
            device = Device(
                name=name,
                model=model,
                type=device_type,
                serial_number=serial_number,
                mac_address=mac_address,
                ip_address=ip_address,
                location=location,
                status=status,
                assigned_to=assigned_to,
                specifications=specifications
            )
            db.session.add(device)
            db.session.commit()
            flash('Устройство успешно добавлено!', 'success')
            return redirect(url_for('devices.devices'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении устройства: {str(e)}', 'error')

    return render_template('devices/add_device.html')

@bluprint_devices_routes.route('/edit_device/<int:device_id>', methods=['GET', 'POST'])
@permissions_required([Permissions.devices_manage])
def edit_device(device_id):
    device = Device.query.get_or_404(device_id)

    if request.method == 'POST':
        device.name = request.form['name']
        device.model = request.form.get('model', '')
        device.type = request.form['type']
        device.serial_number = request.form['serial_number']
        device.mac_address = request.form.get('mac_address', '')
        device.ip_address = request.form.get('ip_address', '')
        device.location = request.form['location']
        device.status = request.form['status']
        device.assigned_to = request.form.get('assigned_to', '')
        device.specifications = request.form.get('specifications', '')

        try:
            db.session.commit()
            flash('Устройство успешно обновлено!', 'success')
            return redirect(url_for('devices.devices'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении устройства: {str(e)}', 'error')

    return render_template('devices/edit_device.html', device=device)

@bluprint_devices_routes.route('/delete_device/<int:device_id>')
@permissions_required([Permissions.devices_manage])
def delete_device(device_id):
    device = Device.query.get_or_404(device_id)

    try:
        db.session.delete(device)
        db.session.commit()
        flash('Устройство успешно удалено!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении устройства: {str(e)}', 'error')

    return redirect(url_for('devices.devices'))

@bluprint_devices_routes.route('/search')
@permissions_required([Permissions.devices_read])
def search():
    query = request.args.get('q', '')
    search_pattern = f'%{query}%'
    devices = Device.query.filter(
        or_(
            Device.name.ilike(search_pattern),
            Device.model.ilike(search_pattern),
            Device.serial_number.ilike(search_pattern),
            Device.assigned_to.ilike(search_pattern)
        )
    ).order_by(Device.created_at.desc()).all()

    return render_template('devices/devices.html', devices=devices, search_query=query)