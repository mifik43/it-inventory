from flask import render_template, request, redirect, url_for, flash, session, Blueprint

from templates.base.database import get_db
from templates.base.requirements import permission_required, permissions_required_all, permissions_required_any
from templates.roles.permissions import Permissions

bluprint_shifts_routes = Blueprint("shifts", __name__)



@bluprint_shifts_routes.route('/shifts_list')
@permission_required(Permissions.shifts_read)
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

@bluprint_shifts_routes.route('/add_shift', methods=['GET', 'POST'])
@permission_required(Permissions.shifts_manage)
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
            return redirect(url_for('shifts.shifts_list'))
        except Exception as e:
            flash(f'Ошибка при добавлении смены: {str(e)}', 'error')
    
    return render_template('shifts/add_shift.html', users=users)

@bluprint_shifts_routes.route('/edit_shift/<int:shift_id>', methods=['GET', 'POST'])
@permission_required(Permissions.shifts_manage)
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
        return redirect(url_for('shifts.shifts_list'))
    
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
            return redirect(url_for('shifts.shifts_list'))
        except Exception as e:
            flash(f'Ошибка при обновлении смены: {str(e)}', 'error')
    
    return render_template('shifts/edit_shift.html', shift=shift, users=users)

@bluprint_shifts_routes.route('/delete_shift/<int:shift_id>')
@permission_required(Permissions.shifts_manage)
def delete_shift(shift_id):
    db = get_db()
    
    try:
        db.execute('DELETE FROM shifts WHERE id = ?', (shift_id,))
        db.commit()
        flash('Смена успешно удалена!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении смены: {str(e)}', 'error')
    
    return redirect(url_for('shifts.shifts_list'))
