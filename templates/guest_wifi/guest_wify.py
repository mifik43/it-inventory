from flask import render_template, request, redirect, url_for, flash, session, Blueprint, send_file
from datetime import datetime

from templates.base.database import get_db
from templates.base.requirements import permission_required, permissions_required_all, permissions_required_any
from templates.roles.permissions import Permissions

from templates.guest_wifi.wifi_utils import download_wifi_template, import_guest_wifi_from_excel, export_guest_wifi_to_excel

bluprint_guest_wifi_routes = Blueprint("guest_wifi", __name__)



@bluprint_guest_wifi_routes.route('/guest_wifi')
@permission_required(Permissions.guest_wifi_read)
def guest_wifi():
    db = get_db()
    wifi_stats = db.execute('''
    SELECT 
        COUNT(*) as total_count,
        SUM(CASE WHEN status = "Активен" THEN 1 ELSE 0 END) as active_count,
        SUM(CASE WHEN status = "Активен" THEN price ELSE 0 END) as total_price,
        COUNT(DISTINCT city) as cities_count
    FROM guest_wifi
''').fetchone()

    total_wifi_count = wifi_stats['total_count'] or 0
    active_wifi_count = wifi_stats['active_count'] or 0
    total_wifi_price = wifi_stats['total_price'] or 0
    wifi_cities_count = wifi_stats['cities_count'] or 0

    # Последние добавленные точки WiFi
    recent_wifi = db.execute('''
        SELECT * FROM guest_wifi 
        ORDER BY created_at DESC 
        LIMIT 5
    ''').fetchall()

    # WiFi по городам
    wifi_by_city = db.execute('''
        SELECT city, COUNT(*) as count, SUM(price) as total_price
        FROM guest_wifi 
        WHERE status = "Активен"
        GROUP BY city 
        ORDER BY total_price DESC
    ''').fetchall()    

    wifi_list = db.execute('''
        SELECT * FROM guest_wifi 
        ORDER BY city, organization
    ''').fetchall()

    return render_template('guest_wifi/guest_wifi.html',
                         total_wifi_count=total_wifi_count,
                         active_wifi_count=active_wifi_count,
                         total_wifi_price=total_wifi_price,
                         wifi_cities_count=wifi_cities_count,
                         recent_wifi=recent_wifi,
                         wifi_by_city=wifi_by_city,
                         wifi_list=wifi_list) 

@bluprint_guest_wifi_routes.route('/add_guest_wifi', methods=['GET', 'POST'])
@permission_required(Permissions.guest_wifi_manage)
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
        
        db = get_db()
        try:
            db.execute('''
                INSERT INTO guest_wifi 
                (city, price, organization, status, ssid, password, ip_range, speed, 
                 contract_number, contract_date, contact_person, phone, email, 
                 installation_date, renewal_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                city, price, organization, status, ssid, password, ip_range, speed,
                contract_number, contract_date, contact_person, phone, email,
                installation_date, renewal_date, notes
            ))
            db.commit()
            flash('Гостевой WiFi успешно добавлен!', 'success')
            return redirect(url_for('guest_wifi.guest_wifi'))
        except Exception as e:
            flash(f'Ошибка при добавлении гостевого WiFi: {str(e)}', 'error')
    
    return render_template('guest_wifi/add_guest_wifi.html')

@bluprint_guest_wifi_routes.route('/edit_guest_wifi/<int:wifi_id>', methods=['GET', 'POST'])
@permission_required(Permissions.guest_wifi_manage)
def edit_guest_wifi(wifi_id):
    db = get_db()
    
    wifi = db.execute('SELECT * FROM guest_wifi WHERE id=?', (wifi_id,)).fetchone()
    if not wifi:
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
            db.execute('''
                UPDATE guest_wifi SET 
                city=?, price=?, organization=?, status=?, ssid=?, password=?, ip_range=?, speed=?,
                contract_number=?, contract_date=?, contact_person=?, phone=?, email=?,
                installation_date=?, renewal_date=?, notes=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (
                city, price, organization, status, ssid, password, ip_range, speed,
                contract_number, contract_date, contact_person, phone, email,
                installation_date, renewal_date, notes, wifi_id
            ))
            db.commit()
            flash('Данные гостевого WiFi успешно обновлены!', 'success')
            return redirect(url_for('guest_wifi.guest_wifi'))
        except Exception as e:
            flash(f'Ошибка при обновлении гостевого WiFi: {str(e)}', 'error')
    
    return render_template('guest_wifi/edit_guest_wifi.html', wifi=wifi)

@bluprint_guest_wifi_routes.route('/delete_guest_wifi/<int:wifi_id>')
@permission_required(Permissions.guest_wifi_manage)
def delete_guest_wifi(wifi_id):
    db = get_db()
    try:
        db.execute('DELETE FROM guest_wifi WHERE id=?', (wifi_id,))
        db.commit()
        flash('Гостевой WiFi успешно удален!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении гостевого WiFi: {str(e)}', 'error')
    
    return redirect(url_for('guest_wifi.guest_wifi'))

# Добавим также поиск для гостевого WiFi
@bluprint_guest_wifi_routes.route('/guest_wifi_search')
@permission_required(Permissions.guest_wifi_read)
def guest_wifi_search():
    query = request.args.get('q', '')
    db = get_db()
    
    wifi_list = db.execute('''
        SELECT * FROM guest_wifi 
        WHERE city LIKE ? OR organization LIKE ? OR ssid LIKE ? OR contact_person LIKE ?
        ORDER BY city, organization
    ''', (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%')).fetchall()
    
    return render_template('guest_wifi/guest_wifi.html', wifi_list=wifi_list, search_query=query)

# ========== МАРШРУТЫ ДЛЯ ЭКСПОРТА/ИМПОРТА ГОСТЕВОГО WIFI ==========

@bluprint_guest_wifi_routes.route('/export/guest_wifi')
@permission_required(Permissions.guest_wifi_read)
def export_guest_wifi():
    """Экспорт гостевого WiFi в Excel"""
    try:
        excel_file = export_guest_wifi_to_excel()
        filename = f'guest_wifi_export_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
        
        return send_file(
            excel_file,
            download_name=filename,
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        flash(f'Ошибка при экспорте данных: {str(e)}', 'error')
        return redirect(url_for('guest_wifi.guest_wifi'))

@bluprint_guest_wifi_routes.route('/import/guest_wifi', methods=['GET', 'POST'])
@permission_required(Permissions.guest_wifi_manage)
def import_guest_wifi():
    """Импорт гостевого WiFi из Excel"""
    if request.method == 'POST':
        if 'excel_file' not in request.files:
            flash('Файл не выбран', 'error')
            return redirect(request.url)
        
        file = request.files['excel_file']
        if file.filename == '':
            flash('Файл не выбран', 'error')
            return redirect(request.url)
        
        if not file.filename.endswith(('.xlsx', '.xls')):
            flash('Поддерживаются только файлы Excel (.xlsx, .xls)', 'error')
            return redirect(request.url)
        
        try:
            success, message = import_guest_wifi_from_excel(file)
            
            if success:
                flash(message, 'success')
            else:
                flash(message, 'error')
                
            return redirect(url_for('guest_wifi.guest_wifi'))
            
        except Exception as e:
            flash(f'Ошибка при импорте данных: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('guest_wifi/import_wifi.html')

@bluprint_guest_wifi_routes.route('/download_wifi_template')
@permission_required(Permissions.guest_wifi_manage)
def download_wifi_template_route():
    """Скачать шаблон для импорта гостевого WiFi"""
    try:
        return download_wifi_template()
    except Exception as e:
        flash(f'Ошибка при создании шаблона: {str(e)}', 'error')
        return redirect(url_for('guest_wifi.import_guest_wifi'))