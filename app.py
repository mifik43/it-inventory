from flask import Flask, render_template, request, redirect, url_for, flash, session
from database import init_db, get_db
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import socket
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-very-secret-key-change-in-production'

# Декоратор для проверки авторизации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Пожалуйста, войдите в систему', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Декоратор для проверки прав администратора
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Пожалуйста, войдите в систему', 'error')
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Недостаточно прав для выполнения этого действия', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

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
    
    return render_template('index.html',
                         devices_count=devices_count,
                         active_providers_count=active_providers_count,
                         total_monthly_cost=total_monthly_cost,
                         users_count=users_count,
                         devices_by_type=devices_by_type,
                         devices_by_status=devices_by_status,
                         recent_devices=recent_devices,
                         active_providers=active_providers,
                         providers_by_city=providers_by_city,
                         cost_by_service=cost_by_service,
                         cubes_list=cubes_list,
                         total_cubes_price=total_cubes_price)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()
        
        if user and check_password_hash(user['password_hash'], password):
            session['logged_in'] = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Вы успешно вошли в систему!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'success')
    return redirect(url_for('index'))

# ========== МАРШРУТЫ ДЛЯ УСТРОЙСТВ ==========

@app.route('/devices')
@login_required
def devices():
    db = get_db()
    devices = db.execute('''
        SELECT * FROM devices 
        ORDER BY created_at DESC
    ''').fetchall()
    return render_template('devices.html', devices=devices)

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
    
    return render_template('add_device.html')

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
    return render_template('edit_device.html', device=device)

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
    
    return render_template('devices.html', devices=devices, search_query=query)

# ========== МАРШРУТЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ==========

@app.route('/users')
@admin_required
def users():
    db = get_db()
    users_list = db.execute('SELECT id, username, role, created_at FROM users').fetchall()
    return render_template('users.html', users=users_list)

@app.route('/create_user', methods=['GET', 'POST'])
@admin_required
def create_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        
        db = get_db()
        
        # Проверяем, существует ли пользователь с таким именем
        existing_user = db.execute(
            'SELECT id FROM users WHERE username = ?', (username,)
        ).fetchone()
        
        if existing_user:
            flash('Пользователь с таким именем уже существует', 'error')
            return render_template('create_user.html')
        
        # Хешируем пароль и создаем пользователя
        password_hash = generate_password_hash(password)
        
        try:
            db.execute(
                'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                (username, password_hash, role)
            )
            db.commit()
            flash('Пользователь успешно создан!', 'success')
            return redirect(url_for('users'))
        except Exception as e:
            flash(f'Ошибка при создании пользователя: {str(e)}', 'error')
    
    return render_template('create_user.html')

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    db = get_db()
    
    if request.method == 'POST':
        username = request.form['username']
        role = request.form['role']
        new_password = request.form.get('new_password', '')
        
        try:
            # Обновляем основные данные пользователя
            if new_password:
                # Если указан новый пароль, обновляем его
                password_hash = generate_password_hash(new_password)
                db.execute(
                    'UPDATE users SET username = ?, role = ?, password_hash = ? WHERE id = ?',
                    (username, role, password_hash, user_id)
                )
                flash('Данные пользователя и пароль успешно обновлены!', 'success')
            else:
                # Если пароль не указан, обновляем только остальные данные
                db.execute(
                    'UPDATE users SET username = ?, role = ? WHERE id = ?',
                    (username, role, user_id)
                )
                flash('Данные пользователя успешно обновлены!', 'success')
            
            db.commit()
            return redirect(url_for('users'))
        except Exception as e:
            flash(f'Ошибка при обновлении пользователя: {str(e)}', 'error')
    
    user = db.execute('SELECT id, username, role FROM users WHERE id = ?', (user_id,)).fetchone()
    return render_template('edit_user.html', user=user)

@app.route('/delete_user/<int:user_id>')
@admin_required
def delete_user(user_id):
    # Запрещаем удаление самого себя
    if user_id == session.get('user_id'):
        flash('Вы не можете удалить свою собственную учетную запись', 'error')
        return redirect(url_for('users'))
    
    db = get_db()
    try:
        db.execute('DELETE FROM users WHERE id = ?', (user_id,))
        db.commit()
        flash('Пользователь успешно удален!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении пользователя: {str(e)}', 'error')
    
    return redirect(url_for('users'))

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        if new_password != confirm_password:
            flash('Новый пароль и подтверждение не совпадают', 'error')
            return render_template('change_password.html')
        
        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE id = ?', (session['user_id'],)
        ).fetchone()
        
        if user and check_password_hash(user['password_hash'], current_password):
            new_password_hash = generate_password_hash(new_password)
            db.execute(
                'UPDATE users SET password_hash = ? WHERE id = ?',
                (new_password_hash, session['user_id'])
            )
            db.commit()
            flash('Пароль успешно изменен!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Текущий пароль указан неверно', 'error')
    
    return render_template('change_password.html')

# ========== МАРШРУТЫ ДЛЯ ПРОВАЙДЕРОВ ==========

@app.route('/providers')
@login_required
def providers():
    db = get_db()
    providers_list = db.execute('''
        SELECT * FROM providers 
        ORDER BY created_at DESC
    ''').fetchall()
    return render_template('providers.html', providers=providers_list)

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
    
    return render_template('add_provider.html')

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
    return render_template('edit_provider.html', provider=provider)

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
    
    return render_template('providers.html', providers=providers_list, search_query=query)

# ========== МАРШРУТЫ ДЛЯ КУБИКОВ (ПРОГРАММНОЕ ОБЕСПЕЧЕНИЕ) ==========




@app.route('/cubes')
@login_required
def cubes():
    cubes_list = get_cubes()
    return render_template('cubes.html', cubes=cubes_list)

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
    
    return render_template('add_cube.html')

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
    return render_template('edit_cube.html', cube=cube)

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
    
    return render_template('cubes.html', cubes=cubes_list, search_query=query)

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
    
    return render_template('todo.html', 
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
                return render_template('add_todo.html', organizations=organizations)
        
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
    
    return render_template('add_todo.html', organizations=organizations)

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
            return render_template('edit_todo.html', task=task_dict, organizations=organizations)
        
        # Преобразуем дату
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Неверный формат даты', 'error')
                return render_template('edit_todo.html', task=task_dict, organizations=organizations)
        
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
    
    return render_template('edit_todo.html', task=task_dict, organizations=organizations)

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
    return render_template('organizations.html', organizations=organizations_list)

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
    
    return render_template('add_organization.html')

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
            return render_template('edit_organization.html', org=org)
        
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
    
    return render_template('edit_organization.html', org=org)

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
    
    print("=" * 60)
    print("🚀 IT Inventory System запущен!")
    print("=" * 60)
    print(f"📍 Локальный доступ:  http://localhost:8000")
    print(f"🌐 Сетевой доступ:    http://{local_ip}:8000")
    print("=" * 60)
    print("📱 Для доступа с других устройств в сети используйте сетевой URL")
    print("⏹️  Для остановки сервера нажмите Ctrl+C")
    print("=" * 60)
    
    # Запускаем сервер с доступом из локальной сети
    app.run(
        debug=True, 
        host='0.0.0.0',  # Доступ со всех интерфейсов
        port=8000,       # Порт (можно изменить при необходимости)
        threaded=True    # Для обработки нескольких запросов одновременно
    )