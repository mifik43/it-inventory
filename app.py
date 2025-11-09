from flask import Flask, render_template, request, redirect, url_for, flash, session
from database import init_db, get_db
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

import socket
import os
from datetime import datetime

from users import bluprint_user_routes
from roles_page import bluprint_roles_routes

from functools import wraps
from requirements import admin_required, login_required

from excel_utils import (
    export_devices, export_providers, export_cubes, 
    export_organizations, export_todos, import_from_excel
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-very-secret-key-change-in-production'

app.register_blueprint(bluprint_user_routes)
app.register_blueprint(bluprint_roles_routes)

# Настройки для загрузки файлов
UPLOAD_FOLDER = 'static/uploads'
SCREENSHOTS_FOLDER = 'static/uploads/screenshots'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SCREENSHOTS_FOLDER'] = SCREENSHOTS_FOLDER

# Создаем папки для загрузок при запуске
os.makedirs(SCREENSHOTS_FOLDER, exist_ok=True)

# Инициализация БД при запуске приложения
with app.app_context():
    init_db()

# ========== ОСНОВНЫЕ МАРШРУТЫ ==========
def get_cubes():
    db = get_db()
    cubes_list = db.execute('''
        SELECT * FROM software_cubes 
        ORDER BY created_at DESC
    ''').fetchall()
    return cubes_list

@app.route('/')
def index():
    db = get_db()
    
    # Основная статистика
    devices_count = db.execute('SELECT COUNT(*) as count FROM devices').fetchone()['count']
    active_providers_count = db.execute('SELECT COUNT(*) as count FROM providers WHERE status = "Активен"').fetchone()['count']
    total_monthly_cost = db.execute('SELECT SUM(price) as total FROM providers WHERE status = "Активен"').fetchone()['total'] or 0
    users_count = db.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']

    # Статистика по статьям и заметкам
    articles_count = db.execute('SELECT COUNT(*) as count FROM articles WHERE is_published = 1').fetchone()['count']
    notes_count = db.execute('SELECT COUNT(*) as count FROM notes').fetchone()['count']
    
    # Ближайшие смены (на сегодня и завтра)
    from datetime import datetime, timedelta
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    
    upcoming_shifts = db.execute('''
        SELECT s.*, u.username 
        FROM shifts s 
        JOIN users u ON s.user_id = u.id 
        WHERE s.shift_date BETWEEN ? AND ?
        ORDER BY s.shift_date, s.shift_type
        LIMIT 10
    ''', (today, tomorrow)).fetchall()

    # Статистика по устройствам
    devices_by_type = db.execute('''
        SELECT type, COUNT(*) as count 
        FROM devices 
        GROUP BY type 
        ORDER BY count DESC
    ''').fetchall()
    
    devices_by_status = db.execute('''
        SELECT status, COUNT(*) as count 
        FROM devices 
        GROUP BY status 
        ORDER BY count DESC
    ''').fetchall()
    
    # Последние добавленные устройства
    recent_devices = db.execute('''
        SELECT * FROM devices 
        ORDER BY created_at DESC 
        LIMIT 5
    ''').fetchall()
    
    # Активные провайдеры
    active_providers = db.execute('''
        SELECT * FROM providers 
        WHERE status = "Активен" 
        ORDER BY created_at DESC 
        LIMIT 5
    ''').fetchall()
    
    # Статистика по провайдерам по городам
    providers_by_city = db.execute('''
        SELECT city, COUNT(*) as count 
        FROM providers 
        GROUP BY city 
        ORDER BY count DESC
    ''').fetchall()
    
    # Стоимость по типам услуг
    cost_by_service = db.execute('''
        SELECT service_type, SUM(price) as total_cost 
        FROM providers 
        WHERE status = "Активен" 
        GROUP BY service_type 
        ORDER BY total_cost DESC
    ''').fetchall()

    cubes_list = get_cubes()

    total_cubes_price = 0
    for c in cubes_list:
        total_cubes_price += c['price']
    
    return render_template('dashboard/index.html',
                         devices_count=devices_count,
                         active_providers_count=active_providers_count,
                         total_monthly_cost=total_monthly_cost,
                         users_count=users_count,
                         articles_count=articles_count,
                         notes_count=notes_count,
                         upcoming_shifts=upcoming_shifts,
                         devices_by_type=devices_by_type,
                         devices_by_status=devices_by_status,
                         recent_devices=recent_devices,
                         active_providers=active_providers,
                         providers_by_city=providers_by_city,
                         cost_by_service=cost_by_service,
                         cubes_list=cubes_list,
                         total_cubes_price=total_cubes_price,
                         today=today,
                         tomorrow=tomorrow)


# ========== МАРШРУТЫ ДЛЯ ЭКСПОРТА/ИМПОРТА EXCEL ==========

@app.route('/export/<data_type>')
@login_required
def export_data(data_type):
    """Экспорт данных в Excel"""
    try:
        if data_type == 'devices':
            excel_file = export_devices()
            filename = f'devices_export_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
        elif data_type == 'providers':
            excel_file = export_providers()
            filename = f'providers_export_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
        elif data_type == 'cubes':
            excel_file = export_cubes()
            filename = f'cubes_export_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
        elif data_type == 'organizations':
            excel_file = export_organizations()
            filename = f'organizations_export_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
        elif data_type == 'todos':
            excel_file = export_todos()
            filename = f'todos_export_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
        else:
            flash('Неподдерживаемый тип данных для экспорта', 'error')
            return redirect(request.referrer or url_for('index'))
        
        return send_file(
            excel_file,
            download_name=filename,
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        flash(f'Ошибка при экспорте данных: {str(e)}', 'error')
        return redirect(request.referrer or url_for('index'))

@app.route('/import/<data_type>', methods=['GET', 'POST'])
@admin_required
def import_data(data_type):
    """Импорт данных из Excel"""
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
            # Определяем таблицу для импорта
            table_mapping = {
                'devices': 'devices',
                'providers': 'providers', 
                'cubes': 'software_cubes',
                'organizations': 'organizations',
                'todos': 'todos'
            }
            
            if data_type not in table_mapping:
                flash('Неподдерживаемый тип данных для импорта', 'error')
                return redirect(request.url)
            
            success, message = import_from_excel(file, table_mapping[data_type])
            
            if success:
                flash(message, 'success')
            else:
                flash(message, 'error')
                
            return redirect(url_for(data_type))
            
        except Exception as e:
            flash(f'Ошибка при импорте данных: {str(e)}', 'error')
            return redirect(request.url)
    
    # GET запрос - показываем форму импорта
    page_titles = {
        'devices': 'устройств',
        'providers': 'провайдеров',
        'cubes': 'программных кубов', 
        'organizations': 'организаций',
        'todos': 'задач'
    }
    
    if data_type not in page_titles:
        flash('Неподдерживаемый тип данных', 'error')
        return redirect(url_for('index'))
    
    return render_template('excel/import.html', 
                         data_type=data_type, 
                         page_title=f"Импорт {page_titles[data_type]}")

# ========== МАРШРУТЫ ДЛЯ УСТРОЙСТВ ==========

@app.route('/devices')
@login_required
def devices():
    db = get_db()
    devices = db.execute('''
        SELECT * FROM devices 
        ORDER BY created_at DESC
    ''').fetchall()
    return render_template('devices/devices.html', devices=devices)

@app.route('/add_device', methods=['GET', 'POST'])
@admin_required
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
            return redirect(url_for('devices'))
        except Exception as e:
            flash(f'Ошибка при добавлении устройства: {str(e)}', 'error')
    
    return render_template('devices/add_device.html')

@app.route('/edit_device/<int:device_id>', methods=['GET', 'POST'])
@admin_required
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
            return redirect(url_for('devices'))
        except Exception as e:
            flash(f'Ошибка при обновлении устройства: {str(e)}', 'error')
    
    device = db.execute('SELECT * FROM devices WHERE id=?', (device_id,)).fetchone()
    return render_template('devices/edit_device.html', device=device)

@app.route('/delete_device/<int:device_id>')
@admin_required
def delete_device(device_id):
    db = get_db()
    try:
        db.execute('DELETE FROM devices WHERE id=?', (device_id,))
        db.commit()
        flash('Устройство успешно удалено!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении устройства: {str(e)}', 'error')
    
    return redirect(url_for('devices'))

@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    db = get_db()
    
    devices = db.execute('''
        SELECT * FROM devices 
        WHERE name LIKE ? OR model LIKE ? OR serial_number LIKE ? OR assigned_to LIKE ?
        ORDER BY created_at DESC
    ''', (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%')).fetchall()
    
    return render_template('devices/devices.html', devices=devices, search_query=query)

# ========== МАРШРУТЫ ДЛЯ ПРОВАЙДЕРОВ ==========

@app.route('/providers')
@login_required
def providers():
    db = get_db()
    providers_list = db.execute('''
        SELECT * FROM providers 
        ORDER BY created_at DESC
    ''').fetchall()
    return render_template('providers/providers.html', providers=providers_list)

@app.route('/add_provider', methods=['GET', 'POST'])
@admin_required
def add_provider():
    if request.method == 'POST':
        name = request.form['name']
        service_type = request.form['service_type']
        contract_number = request.form.get('contract_number', '')
        contract_date = request.form.get('contract_date', '')
        ip_range = request.form.get('ip_range', '')
        speed = request.form.get('speed', '')
        price = request.form.get('price', 0)
        contact_person = request.form.get('contact_person', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        object_location = request.form['object_location']
        city = request.form['city']
        status = request.form['status']
        notes = request.form.get('notes', '')
        
        # Преобразуем цену в число
        try:
            price = float(price) if price else 0
        except ValueError:
            price = 0
        
        db = get_db()
        try:
            db.execute('''
                INSERT INTO providers 
                (name, service_type, contract_number, contract_date, ip_range, speed, price, 
                 contact_person, phone, email, object_location, city, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                name, service_type, contract_number, contract_date, ip_range, speed, price,
                contact_person, phone, email, object_location, city, status, notes
            ))
            db.commit()
            flash('Провайдер успешно добавлен!', 'success')
            return redirect(url_for('providers'))
        except Exception as e:
            flash(f'Ошибка при добавлении провайдера: {str(e)}', 'error')
    
    return render_template('providers/add_provider.html')

@app.route('/edit_provider/<int:provider_id>', methods=['GET', 'POST'])
@admin_required
def edit_provider(provider_id):
    db = get_db()
    
    if request.method == 'POST':
        name = request.form['name']
        service_type = request.form['service_type']
        contract_number = request.form.get('contract_number', '')
        contract_date = request.form.get('contract_date', '')
        ip_range = request.form.get('ip_range', '')
        speed = request.form.get('speed', '')
        price = request.form.get('price', 0)
        contact_person = request.form.get('contact_person', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        object_location = request.form['object_location']
        city = request.form['city']
        status = request.form['status']
        notes = request.form.get('notes', '')
        
        # Преобразуем цену в число
        try:
            price = float(price) if price else 0
        except ValueError:
            price = 0
        
        try:
            db.execute('''
                UPDATE providers SET 
                name=?, service_type=?, contract_number=?, contract_date=?, ip_range=?, speed=?, price=?,
                contact_person=?, phone=?, email=?, object_location=?, city=?, status=?, notes=?
                WHERE id=?
            ''', (
                name, service_type, contract_number, contract_date, ip_range, speed, price,
                contact_person, phone, email, object_location, city, status, notes, provider_id
            ))
            db.commit()
            flash('Данные провайдера успешно обновлены!', 'success')
            return redirect(url_for('providers'))
        except Exception as e:
            flash(f'Ошибка при обновлении провайдера: {str(e)}', 'error')
    
    provider = db.execute('SELECT * FROM providers WHERE id=?', (provider_id,)).fetchone()
    return render_template('providers/edit_provider.html', provider=provider)

@app.route('/delete_provider/<int:provider_id>')
@admin_required
def delete_provider(provider_id):
    db = get_db()
    try:
        db.execute('DELETE FROM providers WHERE id=?', (provider_id,))
        db.commit()
        flash('Провайдер успешно удален!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении провайдера: {str(e)}', 'error')
    
    return redirect(url_for('providers'))

@app.route('/provider_search')
@login_required
def provider_search():
    query = request.args.get('q', '')
    db = get_db()
    
    providers_list = db.execute('''
        SELECT * FROM providers 
        WHERE name LIKE ? OR contract_number LIKE ? OR object_location LIKE ? OR city LIKE ? OR contact_person LIKE ?
        ORDER BY created_at DESC
    ''', (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%')).fetchall()
    
    return render_template('providers/providers.html', providers=providers_list, search_query=query)

# ========== МАРШРУТЫ ДЛЯ КУБИКОВ (ПРОГРАММНОЕ ОБЕСПЕЧЕНИЕ) ==========




@app.route('/cubes')
@login_required
def cubes():
    cubes_list = get_cubes()
    return render_template('cubes/cubes.html', cubes=cubes_list)

@app.route('/add_cube', methods=['GET', 'POST'])
@admin_required
def add_cube():
    if request.method == 'POST':
        name = request.form['name']
        software_type = request.form['software_type']
        license_type = request.form['license_type']
        license_key = request.form.get('license_key', '')
        contract_number = request.form.get('contract_number', '')
        contract_date = request.form.get('contract_date', '')
        price = request.form.get('price', 0)
        users_count = request.form.get('users_count', 1)
        support_contact = request.form.get('support_contact', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        object_location = request.form['object_location']
        city = request.form['city']
        status = request.form['status']
        renewal_date = request.form.get('renewal_date', '')
        notes = request.form.get('notes', '')
        
        # Преобразуем цены и количество в числа
        try:
            price = float(price) if price else 0
            users_count = int(users_count) if users_count else 1
        except ValueError:
            price = 0
            users_count = 1
        
        db = get_db()
        try:
            db.execute('''
                INSERT INTO software_cubes 
                (name, software_type, license_type, license_key, contract_number, contract_date, price, users_count, 
                 support_contact, phone, email, object_location, city, status, renewal_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, software_type, license_type, license_key, contract_number, contract_date, price, users_count,
                  support_contact, phone, email, object_location, city, status, renewal_date, notes))
            db.commit()
            flash('Кубик успешно добавлен!', 'success')
            return redirect(url_for('cubes'))
        except Exception as e:
            flash(f'Ошибка при добавлении кубика: {str(e)}', 'error')
    
    return render_template('cubes/add_cube.html')

@app.route('/edit_cube/<int:cube_id>', methods=['GET', 'POST'])
@admin_required
def edit_cube(cube_id):
    db = get_db()
    
    if request.method == 'POST':
        name = request.form['name']
        software_type = request.form['software_type']
        license_type = request.form['license_type']
        license_key = request.form.get('license_key', '')
        contract_number = request.form.get('contract_number', '')
        contract_date = request.form.get('contract_date', '')
        price = request.form.get('price', 0)
        users_count = request.form.get('users_count', 1)
        support_contact = request.form.get('support_contact', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        object_location = request.form['object_location']
        city = request.form['city']
        status = request.form['status']
        renewal_date = request.form.get('renewal_date', '')
        notes = request.form.get('notes', '')
        
        # Преобразуем цены и количество в числа
        try:
            price = float(price) if price else 0
            users_count = int(users_count) if users_count else 1
        except ValueError:
            price = 0
            users_count = 1
        
        try:
            db.execute('''
                UPDATE software_cubes SET 
                name=?, software_type=?, license_type=?, license_key=?, contract_number=?, contract_date=?, price=?, users_count=?,
                support_contact=?, phone=?, email=?, object_location=?, city=?, status=?, renewal_date=?, notes=?
                WHERE id=?
            ''', (name, software_type, license_type, license_key, contract_number, contract_date, price, users_count,
                  support_contact, phone, email, object_location, city, status, renewal_date, notes, cube_id))
            db.commit()
            flash('Данные кубика успешно обновлены!', 'success')
            return redirect(url_for('cubes'))
        except Exception as e:
            flash(f'Ошибка при обновлении кубика: {str(e)}', 'error')
    
    cube = db.execute('SELECT * FROM software_cubes WHERE id=?', (cube_id,)).fetchone()
    return render_template('cubes/edit_cube.html', cube=cube)

@app.route('/delete_cube/<int:cube_id>')
@admin_required
def delete_cube(cube_id):
    db = get_db()
    try:
        db.execute('DELETE FROM software_cubes WHERE id=?', (cube_id,))
        db.commit()
        flash('Кубик успешно удален!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении кубика: {str(e)}', 'error')
    
    return redirect(url_for('cubes'))

@app.route('/cube_search')
@login_required
def cube_search():
    query = request.args.get('q', '')
    db = get_db()
    
    cubes_list = db.execute('''
        SELECT * FROM software_cubes 
        WHERE name LIKE ? OR license_key LIKE ? OR contract_number LIKE ? OR object_location LIKE ? OR support_contact LIKE ?
        ORDER BY created_at DESC
    ''', (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%')).fetchall()
    
    return render_template('cubes/cubes.html', cubes=cubes_list, search_query=query)

@app.route('/todo')
@login_required
def todo():
    db = get_db()
    
    # Получаем параметр показа выполненных задач
    show_completed = request.args.get('show_completed', 'false').lower() == 'true'
    
    # Базовый запрос
    query = '''
        SELECT t.*, o.name as organization_name 
        FROM todos t 
        LEFT JOIN organizations o ON t.organization_id = o.id 
    '''
    
    where_conditions = []
    if not show_completed:
        where_conditions.append("(t.is_completed = 0 OR t.is_completed IS NULL)")
    
    if where_conditions:
        query += " WHERE " + " AND ".join(where_conditions)
    
    query += '''
        ORDER BY 
            CASE 
                WHEN t.status = 'в работе' THEN 1
                WHEN t.status = 'новая' THEN 2
                WHEN t.status = 'отложена' THEN 3
                ELSE 4
            END,
            CASE 
                WHEN t.priority = 'критичный' THEN 1
                WHEN t.priority = 'высокий' THEN 2
                WHEN t.priority = 'средний' THEN 3
                ELSE 4
            END,
            t.due_date ASC,
            t.created_at DESC
    '''
    
    todos = db.execute(query).fetchall()
    
    # Обрабатываем даты для шаблона
    today = datetime.now().date()
    
    processed_todos = []
    for task in todos:
        task_dict = dict(task)
        
        # Обрабатываем due_date
        if task_dict['due_date']:
            if isinstance(task_dict['due_date'], str):
                try:
                    task_dict['due_date'] = datetime.strptime(task_dict['due_date'], '%Y-%m-%d').date()
                except ValueError:
                    task_dict['due_date'] = None
            # Если это datetime объект, преобразуем в date
            elif hasattr(task_dict['due_date'], 'date'):
                task_dict['due_date'] = task_dict['due_date'].date()
        
        # Определяем, просрочена ли задача
        task_dict['is_overdue'] = False
        if task_dict['due_date'] and not task_dict['is_completed']:
            task_dict['is_overdue'] = task_dict['due_date'] < today
        
        processed_todos.append(task_dict)
    
    # Статистика для отображения - ИСПРАВЛЕННЫЙ ЗАПРОС
    all_tasks_stats = db.execute('''
        SELECT 
            COUNT(*) as total,
            COALESCE(SUM(is_completed), 0) as completed_total
        FROM todos
    ''').fetchone()
    
    # Статистика для отображения
    total_tasks = len(processed_todos)
    in_progress = len([t for t in processed_todos if t['status'] == 'в работе'])
    completed_count = len([t for t in processed_todos if t['is_completed'] == 1])
    
    return render_template('todo/todo.html', 
                         todos=processed_todos, 
                         total_tasks=total_tasks,
                         in_progress=in_progress,
                         completed_count=completed_count,
                         show_completed=show_completed,
                         all_tasks_total=all_tasks_stats['total'],
                         all_tasks_completed=all_tasks_stats['completed_total'],
                         today=today)

@app.route('/add_todo', methods=['GET', 'POST'])
@login_required
def add_todo():
    db = get_db()
    organizations = db.execute('SELECT * FROM organizations ORDER BY name').fetchall()
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form.get('description', '')
        status = request.form['status']
        priority = request.form['priority']
        organization_id = request.form.get('organization_id') or None
        due_date_str = request.form.get('due_date', '')
        
        # Валидация
        if not title:
            flash('Название задачи обязательно для заполнения', 'error')
            return render_template('add_todo.html', organizations=organizations)
        
        # Преобразуем дату
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Неверный формат даты', 'error')
                return render_template('todo/add_todo.html', organizations=organizations)
        
        try:
            db.execute('''
                INSERT INTO todos (title, description, status, priority, organization_id, due_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (title, description, status, priority, organization_id, due_date))
            db.commit()
            flash('Задача успешно добавлена!', 'success')
            return redirect(url_for('todo'))
        except Exception as e:
            flash(f'Ошибка при добавлении задачи: {str(e)}', 'error')
    
    return render_template('todo/add_todo.html', organizations=organizations)

@app.route('/edit_todo/<int:todo_id>', methods=['GET', 'POST'])
@login_required
def edit_todo(todo_id):
    db = get_db()
    organizations = db.execute('SELECT * FROM organizations ORDER BY name').fetchall()
    
    # Получаем задачу
    task = db.execute('''
        SELECT t.*, o.name as organization_name 
        FROM todos t 
        LEFT JOIN organizations o ON t.organization_id = o.id 
        WHERE t.id = ?
    ''', (todo_id,)).fetchone()
    
    if not task:
        flash('Задача не найдена', 'error')
        return redirect(url_for('todo'))
    
    # Обрабатываем дату для формы
    task_dict = dict(task)
    if task_dict['due_date']:
        if isinstance(task_dict['due_date'], str):
            try:
                task_dict['due_date'] = datetime.strptime(task_dict['due_date'], '%Y-%m-%d').date()
            except ValueError:
                task_dict['due_date'] = None
        elif hasattr(task_dict['due_date'], 'date'):
            task_dict['due_date'] = task_dict['due_date'].date()
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form.get('description', '')
        status = request.form['status']
        priority = request.form['priority']
        organization_id = request.form.get('organization_id') or None
        due_date_str = request.form.get('due_date', '')
        is_completed = request.form.get('is_completed') == '1'
        
        # Валидация
        if not title:
            flash('Название задачи обязательно для заполнения', 'error')
            return render_template('todo/todo/edit_todo.html', task=task_dict, organizations=organizations)
        
        # Преобразуем дату
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Неверный формат даты', 'error')
                return render_template('todo/edit_todo.html', task=task_dict, organizations=organizations)
        
        # Определяем completed_at
        completed_at = None
        if is_completed and not task_dict['is_completed']:
            completed_at = datetime.now()
        elif not is_completed and task_dict['is_completed']:
            completed_at = None
        
        try:
            db.execute('''
                UPDATE todos SET 
                title=?, description=?, status=?, priority=?, organization_id=?, due_date=?,
                is_completed=?, completed_at=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (title, description, status, priority, organization_id, due_date, 
                  is_completed, completed_at, todo_id))
            db.commit()
            flash('Задача успешно обновлена!', 'success')
            return redirect(url_for('todo'))
        except Exception as e:
            flash(f'Ошибка при обновлении задачи: {str(e)}', 'error')
    
    return render_template('todo/edit_todo.html', task=task_dict, organizations=organizations)

@app.route('/delete_todo/<int:todo_id>')
@login_required
def delete_todo(todo_id):
    db = get_db()
    try:
        db.execute('DELETE FROM todos WHERE id = ?', (todo_id,))
        db.commit()
        flash('Задача успешно удалена!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении задачи: {str(e)}', 'error')
    
    return redirect(url_for('todo'))

@app.route('/complete_todo/<int:todo_id>')
@login_required
def complete_todo(todo_id):
    """Отметить задачу как выполненную"""
    db = get_db()
    try:
        db.execute('''
            UPDATE todos SET 
            status = 'выполнена', 
            is_completed = 1,
            completed_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (todo_id,))
        db.commit()
        flash('Задача отмечена как выполненная!', 'success')
    except Exception as e:
        flash(f'Ошибка при выполнении задачи: {str(e)}', 'error')
    
    return redirect(url_for('todo'))

@app.route('/reopen_todo/<int:todo_id>')
@login_required
def reopen_todo(todo_id):
    """Вернуть задачу в работу"""
    db = get_db()
    try:
        db.execute('''
            UPDATE todos SET 
            status = 'в работе', 
            is_completed = 0,
            completed_at = NULL,
            updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (todo_id,))
        db.commit()
        flash('Задача возвращена в работу!', 'success')
    except Exception as e:
        flash(f'Ошибка при возврате задачи: {str(e)}', 'error')
    
    return redirect(url_for('todo'))

@app.route('/toggle_completed')
@login_required
def toggle_completed():
    """Переключить отображение выполненных задач"""
    show_completed = request.args.get('show_completed', 'false') == 'true'
    return redirect(url_for('todo', show_completed=show_completed))

# ========== МАРШРУТЫ ДЛЯ ОРГАНИЗАЦИЙ ==========

@app.route('/organizations')
@login_required
def organizations():
    db = get_db()
    organizations_list = db.execute('''
        SELECT * FROM organizations 
        ORDER BY 
            CASE type
                WHEN 'ООО' THEN 1
                WHEN 'ИП' THEN 2
                WHEN 'Самозанятый' THEN 3
                ELSE 4
            END,
            name
    ''').fetchall()
    return render_template('organizations/organizations.html', organizations=organizations_list)

@app.route('/add_organization', methods=['GET', 'POST'])
@admin_required
def add_organization():
    if request.method == 'POST':
        name = request.form['name']
        org_type = request.form['type']
        inn = request.form.get('inn', '')
        contact_person = request.form.get('contact_person', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        address = request.form.get('address', '')
        notes = request.form.get('notes', '')
        
        # Валидация
        if not name:
            flash('Название организации обязательно для заполнения', 'error')
            return render_template('add_organization.html')
        
        db = get_db()
        try:
            db.execute('''
                INSERT INTO organizations (name, type, inn, contact_person, phone, email, address, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, org_type, inn, contact_person, phone, email, address, notes))
            db.commit()
            flash('Организация успешно добавлена!', 'success')
            return redirect(url_for('organizations'))
        except Exception as e:
            flash(f'Ошибка при добавлении организации: {str(e)}', 'error')
    
    return render_template('organizations/add_organization.html')

@app.route('/edit_organization/<int:org_id>', methods=['GET', 'POST'])
@admin_required
def edit_organization(org_id):
    db = get_db()
    
    org = db.execute('SELECT * FROM organizations WHERE id = ?', (org_id,)).fetchone()
    if not org:
        flash('Организация не найдена', 'error')
        return redirect(url_for('organizations'))
    
    if request.method == 'POST':
        name = request.form['name']
        org_type = request.form['type']
        inn = request.form.get('inn', '')
        contact_person = request.form.get('contact_person', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        address = request.form.get('address', '')
        notes = request.form.get('notes', '')
        
        # Валидация
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
            return redirect(url_for('organizations'))
        except Exception as e:
            flash(f'Ошибка при обновлении организации: {str(e)}', 'error')
    
    return render_template('organizations/edit_organization.html', org=org)

@app.route('/delete_organization/<int:org_id>')
@admin_required
def delete_organization(org_id):
    db = get_db()
    
    # Проверяем, используется ли организация в задачах
    tasks_count = db.execute('SELECT COUNT(*) as count FROM todos WHERE organization_id = ?', (org_id,)).fetchone()['count']
    
    if tasks_count > 0:
        flash('Невозможно удалить организацию, так как она используется в задачах', 'error')
        return redirect(url_for('organizations'))
    
    try:
        db.execute('DELETE FROM organizations WHERE id = ?', (org_id,))
        db.commit()
        flash('Организация успешно удалена!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении организации: {str(e)}', 'error')
    
    return redirect(url_for('organizations'))

# ========== МАРШРУТЫ ДЛЯ СТАТЕЙ И ЗАМЕТОК ==========

@app.route('/articles')
@login_required
def articles_list():
    db = get_db()
    articles = db.execute('''
        SELECT a.*, u.username as author_name 
        FROM articles a 
        JOIN users u ON a.author_id = u.id 
        WHERE a.is_published = 1
        ORDER BY a.updated_at DESC
    ''').fetchall()
    
    # Получаем уникальные категории для фильтра
    categories = db.execute('SELECT DISTINCT category FROM articles ORDER BY category').fetchall()
    category_list = [cat['category'] for cat in categories]
    
    # Статистика для сегодня
    today = datetime.now().strftime('%Y-%m-%d')
    today_updated = db.execute('''
        SELECT COUNT(*) as count FROM articles 
        WHERE DATE(updated_at) = ? AND is_published = 1
    ''', (today,)).fetchone()['count']
    
    return render_template('knowledge/articles/articles.html', 
                         articles=articles, 
                         categories=category_list,
                         today_updated=today_updated)



@app.route('/add_article', methods=['GET', 'POST'])
@login_required
def add_article():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        category = request.form['category']
        tags = request.form.get('tags', '')
        is_published = request.form.get('is_published') == '1'
        
        # Валидация
        if not title or not content:
            flash('Заголовок и содержание обязательны для заполнения', 'error')
            return render_template('knowledge/articles/add_article.html')
        
        db = get_db()
        try:
            # Создаем статью
            cursor = db.execute('''
                INSERT INTO articles (title, content, category, tags, author_id, is_published)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (title, content, category, tags, session['user_id'], is_published))
            article_id = cursor.lastrowid
            
            # Обработка загруженных скриншотов
            if 'screenshots' in request.files:
                files = request.files.getlist('screenshots')
                uploaded_count = 0
                
                for file in files:
                    if file and file.filename:  # Проверяем, что файл выбран
                        screenshot_info = save_screenshot(file, article_id)
                        if screenshot_info:
                            db.execute('''
                                INSERT INTO article_screenshots (article_id, filename, original_filename, file_size)
                                VALUES (?, ?, ?, ?)
                            ''', (article_id, screenshot_info['filename'], 
                                  screenshot_info['original_filename'], screenshot_info['file_size']))
                            uploaded_count += 1
                
                if uploaded_count > 0:
                    flash(f'Статья успешно создана! Загружено {uploaded_count} скриншотов.', 'success')
                else:
                    flash('Статья успешно создана!', 'success')
            
            db.commit()
            return redirect(url_for('view_article', article_id=article_id))
            
        except Exception as e:
            db.rollback()
            flash(f'Ошибка при создании статьи: {str(e)}', 'error')
    
    return render_template('knowledge/articles/add_article.html')


@app.route('/delete_article/<int:article_id>')
@login_required
def delete_article(article_id):
    db = get_db()
    article = db.execute('SELECT * FROM articles WHERE id = ?', (article_id,)).fetchone()
    
    if not article:
        flash('Статья не найдена', 'error')
        return redirect(url_for('articles_list'))
    
    # Проверяем права доступа
    if article['author_id'] != session['user_id'] and session['role'] != 'admin':
        flash('У вас нет прав для удаления этой статьи', 'error')
        return redirect(url_for('articles_list'))
    
    try:
        # Удаляем связанные скриншоты
        screenshots = db.execute('SELECT * FROM article_screenshots WHERE article_id = ?', (article_id,)).fetchall()
        for screenshot in screenshots:
            delete_screenshot(screenshot['id'])
        
        # Удаляем статью
        db.execute('DELETE FROM articles WHERE id = ?', (article_id,))
        db.commit()
        flash('Статья и все связанные скриншоты успешно удалены!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении статьи: {str(e)}', 'error')
    
    return redirect(url_for('articles_list'))

# ========== МАРШРУТЫ ДЛЯ СКРИНШОТОВ СТАТЕЙ ==========

@app.route('/edit_article/<int:article_id>', methods=['GET', 'POST'])
@login_required
def edit_article(article_id):
    db = get_db()
    article = db.execute('SELECT * FROM articles WHERE id = ?', (article_id,)).fetchone()
    
    if not article:
        flash('Статья не найдена', 'error')
        return redirect(url_for('articles_list'))
    
    # Проверяем права доступа
    if article['author_id'] != session['user_id'] and session['role'] != 'admin':
        flash('У вас нет прав для редактирования этой статьи', 'error')
        return redirect(url_for('articles_list'))
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        category = request.form['category']
        tags = request.form.get('tags', '')
        is_published = request.form.get('is_published') == '1'
        
        if not title or not content:
            flash('Заголовок и содержание обязательны для заполнения', 'error')
            return render_template('knowledge/articles/edit_article.html', article=article, screenshots=get_article_screenshots(article_id))
        
        try:
            db.execute('''
                UPDATE articles SET 
                title=?, content=?, category=?, tags=?, is_published=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (title, content, category, tags, is_published, article_id))
            db.commit()
            
            # Обработка загруженных скриншотов
            if 'screenshots' in request.files:
                files = request.files.getlist('screenshots')
                for file in files:
                    if file and file.filename:  # Проверяем, что файл выбран
                        screenshot_info = save_screenshot(file, article_id)
                        if screenshot_info:
                            db.execute('''
                                INSERT INTO article_screenshots (article_id, filename, original_filename, file_size)
                                VALUES (?, ?, ?, ?)
                            ''', (article_id, screenshot_info['filename'], 
                                  screenshot_info['original_filename'], screenshot_info['file_size']))
                            db.commit()
            
            flash('Статья успешно обновлена!', 'success')
            return redirect(url_for('view_article', article_id=article_id))
        except Exception as e:
            flash(f'Ошибка при обновлении статьи: {str(e)}', 'error')
    
    return render_template('knowledge/articles/edit_article.html', 
                         article=article, 
                         screenshots=get_article_screenshots(article_id))

@app.route('/articles/screenshot/<int:screenshot_id>/description', methods=['POST'])
@login_required
def update_screenshot_description(screenshot_id):
    """Обновляет описание скриншота"""
    db = get_db()
    data = request.get_json()
    
    if not data or 'description' not in data:
        return jsonify({'success': False, 'error': 'Неверные данные'})
    
    screenshot = db.execute('SELECT * FROM article_screenshots WHERE id = ?', (screenshot_id,)).fetchone()
    if not screenshot:
        return jsonify({'success': False, 'error': 'Скриншот не найден'})
    
    # Проверяем права доступа
    article = db.execute('SELECT * FROM articles WHERE id = ?', (screenshot['article_id'],)).fetchone()
    if article['author_id'] != session['user_id'] and session['role'] != 'admin':
        return jsonify({'success': False, 'error': 'Нет прав доступа'})
    
    try:
        db.execute('''
            UPDATE article_screenshots SET description = ? WHERE id = ?
        ''', (data['description'], screenshot_id))
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/delete_screenshot/<int:screenshot_id>')
@login_required
def delete_screenshot(screenshot_id):
    """Удаляет скриншот"""
    db = get_db()
    screenshot = db.execute('SELECT * FROM article_screenshots WHERE id = ?', (screenshot_id,)).fetchone()
    
    if not screenshot:
        flash('Скриншот не найден', 'error')
        return redirect(url_for('articles_list'))
    
    # Проверяем права доступа
    article = db.execute('SELECT * FROM articles WHERE id = ?', (screenshot['article_id'],)).fetchone()
    if article['author_id'] != session['user_id'] and session['role'] != 'admin':
        flash('У вас нет прав для удаления этого скриншота', 'error')
        return redirect(url_for('view_article', article_id=article['id']))
    
    if delete_screenshot(screenshot_id):
        flash('Скриншот успешно удален!', 'success')
    else:
        flash('Ошибка при удалении скриншота', 'error')
    
    return redirect(url_for('edit_article', article_id=article['id']))

@app.route('/articles/<int:article_id>')
@login_required
def view_article(article_id):
    db = get_db()
    
    # Увеличиваем счетчик просмотров
    db.execute('UPDATE articles SET views = views + 1 WHERE id = ?', (article_id,))
    db.commit()
    
    article = db.execute('''
        SELECT a.*, u.username as author_name 
        FROM articles a 
        JOIN users u ON a.author_id = u.id 
        WHERE a.id = ?
    ''', (article_id,)).fetchone()
    
    if not article:
        flash('Статья не найдена', 'error')
        return redirect(url_for('articles_list'))
    
    return render_template('knowledge/articles/view_article.html', 
                         article=article, 
                         screenshots=get_article_screenshots(article_id))

def allowed_file(filename):
    """Проверяет, разрешено ли расширение файла"""
    if not '.' in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    
    # Проверяем расширение
    if ext not in ALLOWED_EXTENSIONS:
        return False
    
    return True

def save_screenshot(file, article_id):
    """Сохраняет скриншот и возвращает информацию о файле"""
    if file and file.filename and allowed_file(file.filename):
        # Проверяем размер файла
        file.seek(0, 2)  # Перемещаемся в конец файла
        file_size = file.tell()
        file.seek(0)  # Возвращаемся в начало
        
        if file_size > MAX_FILE_SIZE:
            raise ValueError(f"Файл слишком большой. Максимальный размер: {MAX_FILE_SIZE // (1024*1024)}MB")
        
        filename = secure_filename(file.filename)
        # Создаем уникальное имя файла
        import uuid
        unique_filename = f"{article_id}_{uuid.uuid4().hex[:8]}_{filename}"
        filepath = os.path.join(app.config['SCREENSHOTS_FOLDER'], unique_filename)
        
        # Сохраняем файл
        file.save(filepath)
        
        return {
            'filename': unique_filename,
            'original_filename': filename,
            'file_size': file_size,
            'filepath': filepath
        }
    return None

def get_article_screenshots(article_id):
    """Получает все скриншоты для статьи"""
    db = get_db()
    return db.execute('''
        SELECT * FROM article_screenshots 
        WHERE article_id = ? 
        ORDER BY upload_order, created_at
    ''', (article_id,)).fetchall()

def delete_screenshot(screenshot_id):
    """Удаляет скриншот"""
    db = get_db()
    screenshot = db.execute('SELECT * FROM article_screenshots WHERE id = ?', (screenshot_id,)).fetchone()
    
    if screenshot:
        # Удаляем файл
        try:
            os.remove(os.path.join(app.config['SCREENSHOTS_FOLDER'], screenshot['filename']))
        except OSError:
            pass  # Файл уже удален или не существует
        
        # Удаляем запись из БД
        db.execute('DELETE FROM article_screenshots WHERE id = ?', (screenshot_id,))
        db.commit()
        return True
    return False


# ========== МАРШРУТЫ ДЛЯ ЗАМЕТОК ==========

@app.route('/notes')
@login_required
def notes_list():
    db = get_db()
    notes = db.execute('''
        SELECT n.*, u.username as author_name 
        FROM notes n 
        JOIN users u ON n.author_id = u.id 
        WHERE n.author_id = ?
        ORDER BY n.is_pinned DESC, n.updated_at DESC
    ''', (session['user_id'],)).fetchall()
    
    # Статистика для сегодня
    today = datetime.now().strftime('%Y-%m-%d')
    today_created = db.execute('''
        SELECT COUNT(*) as count FROM notes 
        WHERE DATE(created_at) = ? AND author_id = ?
    ''', (today, session['user_id'])).fetchone()['count']
    
    return render_template('knowledge/notes/notes.html', notes=notes, today_created=today_created)

@app.route('/add_note', methods=['GET', 'POST'])
@login_required
def add_note():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        color = request.form.get('color', '#ffffff')
        is_pinned = request.form.get('is_pinned') == '1'
        
        if not title or not content:
            flash('Заголовок и содержание обязательны для заполнения', 'error')
            return render_template('knowledge/notes/add_note.html')
        
        db = get_db()
        try:
            db.execute('''
                INSERT INTO notes (title, content, color, is_pinned, author_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (title, content, color, is_pinned, session['user_id']))
            db.commit()
            flash('Заметка успешно создана!', 'success')
            return redirect(url_for('notes_list'))
        except Exception as e:
            flash(f'Ошибка при создании заметки: {str(e)}', 'error')
    
    return render_template('knowledge/notes/add_note.html')

# ========== МАРШРУТЫ ДЛЯ УДАЛЕНИЯ И РЕДАКТИРОВАНИЯ СТАТЕЙ И ЗАМЕТОК ==========


@app.route('/delete_note/<int:note_id>')
@login_required
def delete_note(note_id):
    db = get_db()
    note = db.execute('SELECT * FROM notes WHERE id = ? AND author_id = ?', 
                     (note_id, session['user_id'])).fetchone()
    
    if not note:
        flash('Заметка не найдена', 'error')
        return redirect(url_for('notes_list'))
    
    try:
        db.execute('DELETE FROM notes WHERE id = ?', (note_id,))
        db.commit()
        flash('Заметка успешно удалена!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении заметки: {str(e)}', 'error')
    
    return redirect(url_for('notes_list'))

@app.route('/edit_note/<int:note_id>', methods=['GET', 'POST'])
@login_required
def edit_note(note_id):
    db = get_db()
    note = db.execute('SELECT * FROM notes WHERE id = ? AND author_id = ?', 
                     (note_id, session['user_id'])).fetchone()
    
    if not note:
        flash('Заметка не найдена', 'error')
        return redirect(url_for('notes_list'))
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        color = request.form.get('color', '#ffffff')
        is_pinned = request.form.get('is_pinned') == '1'
        
        if not title or not content:
            flash('Заголовок и содержание обязательны для заполнения', 'error')
            return render_template('knowledge/notes/edit_note.html', note=note)
        
        try:
            db.execute('''
                UPDATE notes SET 
                title=?, content=?, color=?, is_pinned=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (title, content, color, is_pinned, note_id))
            db.commit()
            flash('Заметка успешно обновлена!', 'success')
            return redirect(url_for('notes_list'))
        except Exception as e:
            flash(f'Ошибка при обновлении заметки: {str(e)}', 'error')
    
    return render_template('knowledge/notes/edit_note.html', note=note)

@app.route('/toggle_pin_note/<int:note_id>')
@login_required
def toggle_pin_note(note_id):
    db = get_db()
    note = db.execute('SELECT * FROM notes WHERE id = ? AND author_id = ?', 
                     (note_id, session['user_id'])).fetchone()
    
    if not note:
        flash('Заметка не найдена', 'error')
        return redirect(url_for('notes_list'))
    
    try:
        db.execute('UPDATE notes SET is_pinned = NOT is_pinned WHERE id = ?', (note_id,))
        db.commit()
        flash('Статус закрепления изменен!', 'success')
    except Exception as e:
        flash(f'Ошибка при изменении статуса: {str(e)}', 'error')
    
    return redirect(url_for('notes_list'))


# ========== МАРШРУТЫ ДЛЯ ГРАФИКА СМЕН ==========

@app.route('/shifts')
@login_required
def shifts_list():
    db = get_db()
    
    # Параметры фильтрации
    user_id = request.args.get('user_id', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    period = request.args.get('period', 'week')
    
    # Устанавливаем даты по умолчанию
    from datetime import datetime, timedelta
    today = datetime.now().date()
    
    if not date_from:
        if period == 'month':
            date_from = today.replace(day=1)
        else:  # week
            date_from = today - timedelta(days=today.weekday())
    
    if not date_to:
        if period == 'month':
            next_month = today.replace(day=28) + timedelta(days=4)
            date_to = next_month - timedelta(days=next_month.day - 1)
        else:  # week
            date_to = date_from + timedelta(days=6)
    
    # Преобразуем в строки для шаблона
    if isinstance(date_from, str):
        date_from_str = date_from
    else:
        date_from_str = date_from.strftime('%Y-%m-%d')
        
    if isinstance(date_to, str):
        date_to_str = date_to
    else:
        date_to_str = date_to.strftime('%Y-%m-%d')
    
    # Базовый запрос
    query = '''
        SELECT s.*, u.username 
        FROM shifts s 
        JOIN users u ON s.user_id = u.id 
        WHERE s.shift_date BETWEEN ? AND ?
    '''
    params = [date_from_str, date_to_str]
    
    # Фильтр по сотруднику
    if user_id:
        query += ' AND s.user_id = ?'
        params.append(user_id)
    
    query += ' ORDER BY s.shift_date, u.username'
    
    shifts = db.execute(query, params).fetchall()
    
    # Получаем всех пользователей для фильтра
    all_users = db.execute('SELECT id, username FROM users ORDER BY username').fetchall()
    
    # Статистика
    stats = db.execute('''
        SELECT 
            COUNT(*) as month_shifts,
            SUM(CASE WHEN shift_type = 'Утро' THEN 1 ELSE 0 END) as morning_shifts,
            SUM(CASE WHEN shift_type = 'Вечер' THEN 1 ELSE 0 END) as evening_shifts,
            SUM(CASE WHEN shift_type = 'Ночь' THEN 1 ELSE 0 END) as night_shifts
        FROM shifts 
        WHERE shift_date BETWEEN ? AND ?
    ''', (date_from_str, date_to_str)).fetchone()
    
    # Данные для календаря
    calendar_dates = []
    current_date = datetime.strptime(date_from_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(date_to_str, '%Y-%m-%d').date()
    
    while current_date <= end_date:
        calendar_dates.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'day_name': current_date.strftime('%a'),
            'is_weekend': current_date.weekday() >= 5
        })
        current_date += timedelta(days=1)
    
    # Пользователи для календаря
    calendar_users = all_users
    
    return render_template('shifts/shifts.html', 
                         shifts=shifts,
                         all_users=all_users,
                         selected_user=int(user_id) if user_id else None,
                         date_from=date_from_str,
                         date_to=date_to_str,
                         stats=stats,
                         calendar_dates=calendar_dates,
                         calendar_users=calendar_users)

@app.route('/add_shift', methods=['GET', 'POST'])
@admin_required
def add_shift():
    db = get_db()
    users = db.execute('SELECT id, username FROM users ORDER BY username').fetchall()
    
    if request.method == 'POST':
        user_id = request.form['user_id']
        shift_date = request.form['shift_date']
        shift_type = request.form['shift_type']
        start_time = request.form.get('start_time', '')
        end_time = request.form.get('end_time', '')
        notes = request.form.get('notes', '')
        
        # Валидация
        if not user_id or not shift_date:
            flash('Сотрудник и дата смены обязательны для заполнения', 'error')
            return render_template('add_shift.html', users=users)
        
        # Проверяем, нет ли уже смены у этого сотрудника на эту дату
        existing_shift = db.execute(
            'SELECT id FROM shifts WHERE user_id = ? AND shift_date = ?',
            (user_id, shift_date)
        ).fetchone()
        
        if existing_shift:
            flash('У этого сотрудника уже есть смена на указанную дату', 'error')
            return render_template('shifts/add_shift.html', users=users)
        
        try:
            db.execute('''
                INSERT INTO shifts (user_id, shift_date, shift_type, start_time, end_time, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, shift_date, shift_type, start_time, end_time, notes))
            db.commit()
            flash('Смена успешно добавлена!', 'success')
            return redirect(url_for('shifts_list'))
        except Exception as e:
            flash(f'Ошибка при добавлении смены: {str(e)}', 'error')
    
    return render_template('shifts/add_shift.html', users=users)

@app.route('/edit_shift/<int:shift_id>', methods=['GET', 'POST'])
@admin_required
def edit_shift(shift_id):
    db = get_db()
    
    shift = db.execute('''
        SELECT s.*, u.username 
        FROM shifts s 
        JOIN users u ON s.user_id = u.id 
        WHERE s.id = ?
    ''', (shift_id,)).fetchone()
    
    if not shift:
        flash('Смена не найдена', 'error')
        return redirect(url_for('shifts_list'))
    
    users = db.execute('SELECT id, username FROM users ORDER BY username').fetchall()
    
    if request.method == 'POST':
        user_id = request.form['user_id']
        shift_date = request.form['shift_date']
        shift_type = request.form['shift_type']
        start_time = request.form.get('start_time', '')
        end_time = request.form.get('end_time', '')
        notes = request.form.get('notes', '')
        
        # Валидация
        if not user_id or not shift_date:
            flash('Сотрудник и дата смены обязательны для заполнения', 'error')
            return render_template('edit_shift.html', shift=shift, users=users)
        
        # Проверяем, нет ли уже смены у этого сотрудника на эту дату (кроме текущей)
        existing_shift = db.execute(
            'SELECT id FROM shifts WHERE user_id = ? AND shift_date = ? AND id != ?',
            (user_id, shift_date, shift_id)
        ).fetchone()
        
        if existing_shift:
            flash('У этого сотрудника уже есть смена на указанную дату', 'error')
            return render_template('shifts/edit_shift.html', shift=shift, users=users)
        
        try:
            db.execute('''
                UPDATE shifts SET 
                user_id=?, shift_date=?, shift_type=?, start_time=?, end_time=?, notes=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (user_id, shift_date, shift_type, start_time, end_time, notes, shift_id))
            db.commit()
            flash('Смена успешно обновлена!', 'success')
            return redirect(url_for('shifts_list'))
        except Exception as e:
            flash(f'Ошибка при обновлении смены: {str(e)}', 'error')
    
    return render_template('shifts/edit_shift.html', shift=shift, users=users)

@app.route('/delete_shift/<int:shift_id>')
@admin_required
def delete_shift(shift_id):
    db = get_db()
    
    try:
        db.execute('DELETE FROM shifts WHERE id = ?', (shift_id,))
        db.commit()
        flash('Смена успешно удалена!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении смены: {str(e)}', 'error')
    
    return redirect(url_for('shifts_list'))

# ========== ЗАПУСК ПРИЛОЖЕНИЯ С СЕТЕВЫМ ДОСТУПОМ ==========

def get_local_ip():
    """Получает локальный IP-адрес для доступа по сети"""
    try:
        # Создаем временное соединение чтобы определить IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        return ip
    except:
        return "не удалось определить"

if __name__ == '__main__':
    local_ip = get_local_ip()
    
    # Запускаем сервер с доступом из локальной сети
    app.run(
        debug=True, 
        host='0.0.0.0',  # Доступ со всех интерфейсов
        port=8000,       # Порт (можно изменить при необходимости)
        threaded=True    # Для обработки нескольких запросов одновременно
    )