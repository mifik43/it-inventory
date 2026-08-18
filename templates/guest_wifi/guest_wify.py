from flask import render_template, request, redirect, url_for, flash, session, Blueprint, send_file
from datetime import datetime

from templates.base.database_helper import db
from templates.base.requirements import permissions_required, permissions_required_all
from templates.roles.permissions import Permissions
from models import GuestWifi
from logger import logger
from sqlalchemy import func, or_

from templates.guest_wifi.wifi_utils import download_wifi_template, import_guest_wifi_from_excel, export_guest_wifi_to_excel

bluprint_guest_wifi_routes = Blueprint("guest_wifi", __name__)



@bluprint_guest_wifi_routes.route('/guest_wifi')
@permissions_required([Permissions.guest_wifi_read])
def guest_wifi():
    logger.info('Открыт список гостевого WiFi')
    total_wifi_count = GuestWifi.query.count()
    active_wifi_count = GuestWifi.query.filter_by(status='Активен').count()
    total_wifi_price = db.session.query(func.coalesce(func.sum(GuestWifi.price), 0)).filter(GuestWifi.status == 'Активен').scalar() or 0
    wifi_cities_count = db.session.query(func.count(func.distinct(GuestWifi.city))).scalar() or 0

    recent_wifi = GuestWifi.query.order_by(GuestWifi.created_at.desc()).limit(5).all()
    wifi_by_city = db.session.query(
        GuestWifi.city,
        func.count(GuestWifi.id).label('count'),
        func.coalesce(func.sum(GuestWifi.price), 0).label('total_price')
    ).filter(GuestWifi.status == 'Активен') \
     .group_by(GuestWifi.city) \
     .order_by(func.coalesce(func.sum(GuestWifi.price), 0).desc()) \
     .all()

    wifi_list = GuestWifi.query.order_by(GuestWifi.city, GuestWifi.organization).all()

    return render_template('guest_wifi/guest_wifi.html',
                         total_wifi_count=total_wifi_count,
                         active_wifi_count=active_wifi_count,
                         total_wifi_price=total_wifi_price,
                         wifi_cities_count=wifi_cities_count,
                         recent_wifi=recent_wifi,
                         wifi_by_city=wifi_by_city,
                         wifi_list=wifi_list)

@bluprint_guest_wifi_routes.route('/add_guest_wifi', methods=['GET', 'POST'])
@permissions_required([Permissions.guest_wifi_manage])
def add_guest_wifi():
    if request.method == 'POST':
        city = request.form['city']
        price = request.form.get('price', 0)
        organization = request.form.get('organization', '')
        status = request.form.get('status', 'Активен')
        ssid = request.form.get('ssid', '')
        password = request.form.get('password', '')
        ip_range = request.form.get('ip_range', '')
        speed = request.form.get('speed', '')
        contract_number = request.form.get('contract_number', '')
        contract_date = request.form.get('contract_date', '')
        contact_person = request.form.get('contact_person', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        installation_date = request.form.get('installation_date', '')
        renewal_date = request.form.get('renewal_date', '')
        notes = request.form.get('notes', '')
        
        # Преобразуем цену в число
        try:
            price = float(price) if price else 0
        except ValueError:
            price = 0
        
        try:
            logger.info('Добавление записи гостевого WiFi', extra={'city': city, 'organization': organization, 'ssid': ssid})
            wifi_record = GuestWifi(
                city=city,
                price=price,
                organization=organization,
                status=status,
                ssid=ssid,
                password=password,
                ip_range=ip_range,
                speed=speed,
                contract_number=contract_number,
                contract_date=contract_date,
                contact_person=contact_person,
                phone=phone,
                email=email,
                installation_date=installation_date,
                renewal_date=renewal_date,
                notes=notes
            )
            db.session.add(wifi_record)
            db.session.commit()
            flash('Гостевой WiFi успешно добавлен!', 'success')
            logger.info(f'Гостевой WiFi добавлен: id={wifi_record.id}')
            return redirect(url_for('guest_wifi.guest_wifi'))
        except Exception as e:
            db.session.rollback()
            logger.error(f'Ошибка при добавлении гостевого WiFi: {e}', exc_info=True)
            flash(f'Ошибка при добавлении гостевого WiFi: {str(e)}', 'error')
    
    return render_template('guest_wifi/add_guest_wifi.html')

@bluprint_guest_wifi_routes.route('/edit_guest_wifi/<int:wifi_id>', methods=['GET', 'POST'])
@permissions_required([Permissions.guest_wifi_manage])
def edit_guest_wifi(wifi_id):
    wifi = GuestWifi.query.get(wifi_id)
    if not wifi:
        logger.warning(f'Запись гостевого WiFi не найдена: id={wifi_id}')
        flash('Запись гостевого WiFi не найдена', 'error')
        return redirect(url_for('guest_wifi.guest_wifi'))
    
    if request.method == 'POST':
        city = request.form['city']
        price = request.form.get('price', 0)
        organization = request.form.get('organization', '')
        status = request.form.get('status', 'Активен')
        ssid = request.form.get('ssid', '')
        password = request.form.get('password', '')
        ip_range = request.form.get('ip_range', '')
        speed = request.form.get('speed', '')
        contract_number = request.form.get('contract_number', '')
        contract_date = request.form.get('contract_date', '')
        contact_person = request.form.get('contact_person', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        installation_date = request.form.get('installation_date', '')
        renewal_date = request.form.get('renewal_date', '')
        notes = request.form.get('notes', '')
        
        # Преобразуем цену в число
        try:
            price = float(price) if price else 0
        except ValueError:
            price = 0
        
        try:
            logger.info(f'Обновление гостевого WiFi id={wifi_id}', extra={'city': city, 'organization': organization})
            wifi.city = city
            wifi.price = price
            wifi.organization = organization
            wifi.status = status
            wifi.ssid = ssid
            wifi.password = password
            wifi.ip_range = ip_range
            wifi.speed = speed
            wifi.contract_number = contract_number
            wifi.contract_date = contract_date
            wifi.contact_person = contact_person
            wifi.phone = phone
            wifi.email = email
            wifi.installation_date = installation_date
            wifi.renewal_date = renewal_date
            wifi.notes = notes
            db.session.commit()
            flash('Данные гостевого WiFi успешно обновлены!', 'success')
            logger.info(f'Гостевой WiFi обновлен: id={wifi_id}')
            return redirect(url_for('guest_wifi.guest_wifi'))
        except Exception as e:
            db.session.rollback()
            logger.error(f'Ошибка при обновлении гостевого WiFi id={wifi_id}: {e}', exc_info=True)
            flash(f'Ошибка при обновлении гостевого WiFi: {str(e)}', 'error')
    
    return render_template('guest_wifi/edit_guest_wifi.html', wifi=wifi)

@bluprint_guest_wifi_routes.route('/delete_guest_wifi/<int:wifi_id>')
@permissions_required([Permissions.guest_wifi_manage])
def delete_guest_wifi(wifi_id):
    try:
        logger.info(f'Удаление гостевого WiFi id={wifi_id}')
        wifi = GuestWifi.query.get(wifi_id)
        if not wifi:
            logger.warning(f'Попытка удалить несуществующий гостевой WiFi id={wifi_id}')
            flash('Запись гостевого WiFi не найдена', 'error')
            return redirect(url_for('guest_wifi.guest_wifi'))
        db.session.delete(wifi)
        db.session.commit()
        flash('Гостевой WiFi успешно удален!', 'success')
        logger.info(f'Гостевой WiFi удалён: id={wifi_id}')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Ошибка при удалении гостевого WiFi id={wifi_id}: {e}', exc_info=True)
        flash(f'Ошибка при удалении гостевого WiFi: {str(e)}', 'error')
    
    return redirect(url_for('guest_wifi.guest_wifi'))

# Добавим также поиск для гостевого WiFi
@bluprint_guest_wifi_routes.route('/guest_wifi_search')
@permissions_required([Permissions.guest_wifi_read])
def guest_wifi_search():
    query = request.args.get('q', '')
    logger.info(f'Поиск гостевого WiFi: query="{query}"')
    search_pattern = f'%{query}%'
    wifi_list = GuestWifi.query.filter(
        or_(
            GuestWifi.city.ilike(search_pattern),
            GuestWifi.organization.ilike(search_pattern),
            GuestWifi.ssid.ilike(search_pattern),
            GuestWifi.contact_person.ilike(search_pattern)
        )
    ).order_by(GuestWifi.city, GuestWifi.organization).all()
    logger.debug(f'Найдено записей гостевого WiFi: {len(wifi_list)}')
    return render_template('guest_wifi/guest_wifi.html', wifi_list=wifi_list, search_query=query)

# ========== МАРШРУТЫ ДЛЯ ЭКСПОРТА/ИМПОРТА ГОСТЕВОГО WIFI ==========

@bluprint_guest_wifi_routes.route('/export/guest_wifi')
@permissions_required([Permissions.guest_wifi_read])
def export_guest_wifi():
    """Экспорт гостевого WiFi в Excel"""
    logger.info('Запрошен экспорт гостевого WiFi в Excel')
    try:
        excel_file = export_guest_wifi_to_excel()
        filename = f'guest_wifi_export_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
        logger.info(f'Формирование файла Excel завершено: {filename}')
        return send_file(
            excel_file,
            download_name=filename,
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        logger.error(f'Ошибка при экспорте гостевого WiFi: {e}', exc_info=True)
        flash(f'Ошибка при экспорте данных: {str(e)}', 'error')
        return redirect(url_for('guest_wifi.guest_wifi'))

@bluprint_guest_wifi_routes.route('/import/guest_wifi', methods=['GET', 'POST'])
@permissions_required([Permissions.guest_wifi_manage])
def import_guest_wifi():
    """Импорт гостевого WiFi из Excel"""
    if request.method == 'POST':
        if 'excel_file' not in request.files:
            logger.warning('Файл не выбран для импорта гостевого WiFi')
            flash('Файл не выбран', 'error')
            return redirect(request.url)
        
        file = request.files['excel_file']
        if file.filename == '':
            logger.warning('Выбран пустой файл для импорта гостевого WiFi')
            flash('Файл не выбран', 'error')
            return redirect(request.url)
        
        if not file.filename.endswith(('.xlsx', '.xls')):
            logger.warning(f'Попытка импорта неподдерживаемого файла: {file.filename}')
            flash('Поддерживаются только файлы Excel (.xlsx, .xls)', 'error')
            return redirect(request.url)
        
        try:
            logger.info(f'Начало импорта гостевого WiFi из файла: {file.filename}')
            success, message = import_guest_wifi_from_excel(file)
            if success:
                logger.info(f'Импорт гостевого WiFi завершен успешно: {file.filename}')
                flash(message, 'success')
            else:
                logger.error(f'Импорт гостевого WiFi завершен с ошибками: {message}')
                flash(message, 'error')
            return redirect(url_for('guest_wifi.guest_wifi'))
        except Exception as e:
            logger.error(f'Ошибка при импорте гостевого WiFi: {e}', exc_info=True)
            flash(f'Ошибка при импорте данных: {str(e)}', 'error')
            return redirect(request.url)
    
    logger.info('Открыта форма импорта гостевого WiFi')
    return render_template('guest_wifi/import_wifi.html')

@bluprint_guest_wifi_routes.route('/download_wifi_template')
@permissions_required([Permissions.guest_wifi_manage])
def download_wifi_template_route():
    """Скачать шаблон для импорта гостевого WiFi"""
    try:
        return download_wifi_template()
    except Exception as e:
        flash(f'Ошибка при создании шаблона: {str(e)}', 'error')
        return redirect(url_for('guest_wifi.import_guest_wifi'))