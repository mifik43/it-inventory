from flask import render_template, request, redirect, url_for, flash, Blueprint, session
from sqlalchemy import or_

from templates.base.database_helper import db
from templates.base.requirements import permissions_required, get_current_user
from templates.roles.permissions import Permissions
from templates.base.organization_utils import ALL_ORGANIZATIONS, get_user_visible_organizations, filter_by_organization
from models import Device, Organization
from logger import logger

bluprint_devices_routes = Blueprint("devices", __name__)

@bluprint_devices_routes.route('/devices')
@permissions_required([Permissions.devices_read])
def devices():
    user = get_current_user()
    current_org_id = session.get('current_org_id')
    query = Device.query
    # Если суперадмин и выбраны все организации, фильтр пропускает все
    if current_org_id == ALL_ORGANIZATIONS:
        pass
    else:
        query = filter_by_organization(query, Device, current_org_id)
    devices_list = query.order_by(Device.name).all()
    return render_template('devices/devices.html', devices=devices_list)

@bluprint_devices_routes.route('/add_device', methods=['GET', 'POST'])
@permissions_required([Permissions.devices_manage])
def add_device():
    user = get_current_user()
    current_org_id = session.get('current_org_id')
    organizations = get_user_visible_organizations(user=user)

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

        # Определяем организацию
        org_id = current_org_id

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
                specifications=specifications,
                organization_id=org_id
            )
            db.session.add(device)
            db.session.commit()
            flash('Устройство успешно добавлено!', 'success')
            logger.info(f"Устройство добавлено: {device.name}, организация_id={org_id}")
            return redirect(url_for('devices.devices'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении устройства: {str(e)}', 'error')
            logger.error(f"Ошибка добавления устройства: {str(e)}")

    return render_template('devices/add_device.html', organizations=organizations, current_org_id=current_org_id)

@bluprint_devices_routes.route('/edit_device/<int:device_id>', methods=['GET', 'POST'])
@permissions_required([Permissions.devices_manage])
def edit_device(device_id):
    user = get_current_user()
    device = Device.query.get_or_404(device_id)
    organizations = filter_by_organization(user)

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

        
        device.organization_id = None

        try:
            db.session.commit()
            flash('Устройство успешно обновлено!', 'success')
            logger.info(f"Устройство обновлено: id={device.id}, name={device.name}")
            return redirect(url_for('devices.devices'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении устройства: {str(e)}', 'error')
            logger.error(f"Ошибка обновления устройства id={device.id}: {str(e)}")

    return render_template('devices/edit_device.html', device=device, organizations=organizations)

@bluprint_devices_routes.route('/delete_device/<int:device_id>')
@permissions_required([Permissions.devices_manage])
def delete_device(device_id):
    device = Device.query.get_or_404(device_id)
    try:
        db.session.delete(device)
        db.session.commit()
        flash('Устройство успешно удалено!', 'success')
        logger.info(f"Устройство удалено: id={device.id}, name={device.name}")
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении устройства: {str(e)}', 'error')
        logger.error(f"Ошибка удаления устройства id={device.id}: {str(e)}")
    return redirect(url_for('devices.devices'))

@bluprint_devices_routes.route('/search')
@permissions_required([Permissions.devices_read])
def search():
    user = get_current_user()
    current_org_id = session.get('current_org_id')
    query = request.args.get('q', '')
    search_pattern = f'%{query}%'
    
    query_filter = Device.query.filter(
        or_(
            Device.name.ilike(search_pattern),
            Device.model.ilike(search_pattern),
            Device.serial_number.ilike(search_pattern),
            Device.assigned_to.ilike(search_pattern)
        )
    )

    if current_org_id:
        query_filter = query_filter.filter_by(organization_id=current_org_id)
    else:
        query_filter = query_filter.filter(Device.organization_id.is_(None))

    devices = query_filter.order_by(Device.created_at.desc()).all()
    return render_template('devices/devices.html', devices=devices, search_query=query)