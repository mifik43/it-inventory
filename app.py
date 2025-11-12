from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from templates.base.database import init_db, get_db
from werkzeug.security import generate_password_hash, check_password_hash


import socket
import os
from datetime import datetime

from templates.auth.users import bluprint_user_routes
from templates.roles.roles_page import bluprint_roles_routes
from templates.providers.providers import bluprint_provider_routes
from templates.devices.devices import bluprint_devices_routes
from templates.cubes.cubes import bluprint_cubes_routes, get_cubes
from templates.guest_wifi.guest_wify import bluprint_guest_wifi_routes
from templates.organizations.organizations import bluprint_organizations_routes
from templates.knowledge.notes.notes import bluprint_notes_routes
from templates.knowledge.articles.articles import bluprint_articles_routes

from functools import wraps
from templates.base.requirements import admin_required, login_required

from excel_utils import (
    export_devices, export_providers, export_cubes, 
    export_organizations, export_todos, import_from_excel
)

from templates.guest_wifi.wifi_utils import (
    export_guest_wifi_to_excel, 
    import_guest_wifi_from_excel,
    download_wifi_template
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-very-secret-key-change-in-production'

app.register_blueprint(bluprint_user_routes)
app.register_blueprint(bluprint_roles_routes)
app.register_blueprint(bluprint_provider_routes)
app.register_blueprint(bluprint_devices_routes)
app.register_blueprint(bluprint_cubes_routes)
app.register_blueprint(bluprint_guest_wifi_routes)
app.register_blueprint(bluprint_organizations_routes)
app.register_blueprint(bluprint_notes_routes)
app.register_blueprint(bluprint_articles_routes)



# Инициализация БД при запуске приложения
with app.app_context():
    init_db()

# ========== ОСНОВНЫЕ МАРШРУТЫ ==========


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
                         tomorrow=tomorrow,
                        # total_wifi_count=total_wifi_count,
                        # active_wifi_count=active_wifi_count,
                        # total_wifi_price=total_wifi_price,
                        # wifi_cities_count=wifi_cities_count,
                        # recent_wifi=recent_wifi,
                        # wifi_by_city=wifi_by_city
    )  

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
        'devices.devices': 'устройств',
        'providers.providers': 'провайдеров',
        'cubes.cubes': 'программных кубов', 
        'organizations.organizations': 'организаций',
        'todos': 'задач'
    }
    
    if data_type not in page_titles:
        flash('Неподдерживаемый тип данных', 'error')
        return redirect(url_for('index'))
    
    return render_template('excel/import.html', 
                         data_type=data_type, 
                         page_title=f"Импорт {page_titles[data_type]}")

# ========== МАРШРУТЫ ДЛЯ УСТРОЙСТВ ==========

# ========== МАРШРУТЫ ДЛЯ ПРОВАЙДЕРОВ ==========

# ========== МАРШРУТЫ ДЛЯ КУБИКОВ (ПРОГРАММНОЕ ОБЕСПЕЧЕНИЕ) ==========

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

# ========== МАРШРУТЫ ДЛЯ СТАТЕЙ И ЗАМЕТОК ==========



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