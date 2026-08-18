from logger import logger

from flask import render_template, request, redirect, url_for, flash, session, Blueprint

from templates.base.database import get_db
from templates.base.requirements import permissions_required, permissions_required_all, permissions_required
from templates.roles.permissions import Permissions
from sqlalchemy import text, func, case
from models import Shift, User

bluprint_shifts_routes = Blueprint("shifts", __name__)



@bluprint_shifts_routes.route('/shifts_list')
@permissions_required([Permissions.shifts_read])
def shifts_list():
    logger.info("Запуск shifts_list")
    db = get_db()

    # Параметры фильтрации
    user_id = request.args.get('user_id', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    period = request.args.get('period', 'week')

    logger.debug("Параметры фильтрации: user_id=%s, date_from=%s, date_to=%s, period=%s",
                 user_id, date_from, date_to, period)

    # Устанавливаем даты по умолчанию
    from datetime import datetime, timedelta
    today = datetime.now().date()

    if not date_from:
        if period == 'month':
            date_from = today.replace(day=1)
        else:  # week
            date_from = today - timedelta(days=today.weekday())
        logger.debug("Дата начала подсчитана автоматически: %s", date_from)

    if not date_to:
        if period == 'month':
            next_month = today.replace(day=28) + timedelta(days=4)
            date_to = next_month - timedelta(days=next_month.day - 1)
        else:  # week
            date_to = date_from + timedelta(days=6)
        logger.debug("Дата конца подсчитана автоматически: %s", date_to)

    # Преобразуем в строки для шаблона
    if isinstance(date_from, str):
        date_from_str = date_from
    else:
        date_from_str = date_from.strftime('%Y-%m-%d')

    if isinstance(date_to, str):
        date_to_str = date_to
    else:
        date_to_str = date_to.strftime('%Y-%m-%d')

    logger.debug("Даты для запроса: %s - %s", date_from_str, date_to_str)

    try:
        # Запрос через ORM
        query = db.query(Shift, User.username).join(User, Shift.user_id == User.id)

        query = query.filter(Shift.shift_date.between(date_from_str, date_to_str))

        if user_id:
            query = query.filter(Shift.user_id == int(user_id))
            logger.debug("Добавлен фильтр по user_id=%s", user_id)

        query = query.order_by(Shift.shift_date, User.username)

        shifts_rows = query.all()
        logger.info("Найдено смен: %d", len(shifts_rows))

        shifts = [{'id': s.id, 'user_id': s.user_id,
                   'shift_date': s.shift_date.strftime('%Y-%m-%d') if s.shift_date else '',
                   'shift_type': s.shift_type,
                   'start_time': s.start_time.strftime('%H:%M') if s.start_time else '',
                   'end_time': s.end_time.strftime('%H:%M') if s.end_time else '',
                   'notes': s.notes or '',
                   'created_at': s.created_at.strftime('%Y-%m-%d') if s.created_at else '',
                   'username': username}
                  for s, username in shifts_rows]

        # Получаем всех пользователей для фильтра
        all_users_rows = db.query(User.id, User.username).order_by(User.username).all()
        logger.info("Всего пользователей в списке: %d", len(all_users_rows))
        all_users = [{'id': r[0], 'username': r[1]} for r in all_users_rows]

        # Статистика
        logger.debug("Запрос статистики по сменам")
        stats_row = db.query(
            func.count(Shift.id).label('month_shifts'),
        func.sum(case((Shift.shift_type == 'Утро', 1), else_=0)).label('morning_shifts'),
        func.sum(case((Shift.shift_type == 'Вечер', 1), else_=0)).label('evening_shifts'),
        func.sum(case((Shift.shift_type == 'Ночь', 1), else_=0)).label('night_shifts')
        ).filter(Shift.shift_date.between(date_from_str, date_to_str)).one_or_none()

        stats = {
            'month_shifts': stats_row.month_shifts or 0,
            'morning_shifts': stats_row.morning_shifts or 0,
            'evening_shifts': stats_row.evening_shifts or 0,
            'night_shifts': stats_row.night_shifts or 0,
        }

        logger.info("Статистика: всего=%d, утро=%d, вечер=%d, ночь=%d",
                     stats['month_shifts'], stats['morning_shifts'],
                     stats['evening_shifts'], stats['night_shifts'])

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

        logger.debug("Календарь: дней=%d, пользователей=%d",
                     len(calendar_dates), len(all_users))

        # Пользователи для календаря
        calendar_users = all_users

        logger.info("shifts_list завершено успешно")
        return render_template('shifts/shifts.html',
                             shifts=shifts,
                             all_users=all_users,
                             selected_user=int(user_id) if user_id else None,
                             date_from=date_from_str,
                             date_to=date_to_str,
                             stats=stats,
                             calendar_dates=calendar_dates,
                             calendar_users=calendar_users)
    except Exception as e:
        logger.error("Ошибка в shifts_list: %s", str(e), exc_info=True)
        flash(f'Ошибка при загрузке смен: {str(e)}', 'error')
        return render_template('shifts/shifts.html', shifts=[], all_users=[], stats={}, calendar_dates=[], calendar_users=[])

@bluprint_shifts_routes.route('/add_shift', methods=['GET', 'POST'])
@permissions_required([Permissions.shifts_manage])
def add_shift():
    logger.info("Запуск add_shift, метод=%s", request.method)
    db = get_db()

    if request.method == 'POST':
        logger.debug("Данные формы: user_id=%s, shift_date=%s, shift_type=%s",
                      request.form.get('user_id', ''), request.form.get('shift_date', ''),
                      request.form.get('shift_type', ''))

    users_rows = db.query(User.id, User.username).order_by(User.username).all()
    users = [{'id': r[0], 'username': r[1]} for r in users_rows]

    if request.method == 'POST':
        user_id = request.form['user_id']
        shift_date = request.form['shift_date']
        shift_type = request.form['shift_type']
        start_time = request.form.get('start_time', '')
        end_time = request.form.get('end_time', '')
        notes = request.form.get('notes', '')

        # Валидация
        if not user_id or not shift_date:
            logger.warning("Валидация не пройдена: пустой user_id или shift_date")
            flash('Сотрудник и дата смены обязательны для заполнения', 'error')
            return render_template('shifts/add_shift.html', users=users)

        # Проверка через ORM
        existing_shift = db.query(Shift.id).filter(
            Shift.user_id == int(user_id),
            Shift.shift_date == shift_date
        ).first()

        if existing_shift:
            logger.warning("Смена уже существует: user_id=%s, shift_date=%s",
                           user_id, shift_date)
            flash('У этого сотрудника уже есть смена на указанную дату', 'error')
            return render_template('shifts/add_shift.html', users=users)

        try:
            logger.info("Создание новой смены: user_id=%s, shift_date=%s, shift_type=%s",
                        user_id, shift_date, shift_type)
            shift = Shift(
                user_id=int(user_id),
                shift_date=shift_date,
                shift_type=shift_type,
                start_time=start_time or None,
                end_time=end_time or None,
                notes=notes
            )
            db.add(shift)
            db.commit()
            logger.info("Смена добавлена успешно, id=%s", shift.id)
            flash('Смена успешно добавлена!', 'success')
            return redirect(url_for('shifts.shifts_list'))
        except Exception as e:
            db.rollback()
            logger.error("Ошибка при добавлении смены: %s", str(e), exc_info=True)
            flash(f'Ошибка при добавлении смены: {str(e)}', 'error')

    logger.debug("Рендер формы добавления смены")
    return render_template('shifts/add_shift.html', users=users)

@bluprint_shifts_routes.route('/edit_shift/<int:shift_id>', methods=['GET', 'POST'])
@permissions_required([Permissions.shifts_manage])
def edit_shift(shift_id):
    logger.info("Запуск edit_shift, shift_id=%s, метод=%s", shift_id, request.method)
    db = get_db()

    try:
        shift_row = db.query(Shift, User.username).join(User, Shift.user_id == User.id).filter(
            Shift.id == shift_id
        ).first()

        if not shift_row:
            logger.warning("Смена не найдена: shift_id=%s", shift_id)
            flash('Смена не найдена', 'error')
            return redirect(url_for('shifts.shifts_list'))

        shift_data, username = shift_row
        shift = {
            'id': shift_data.id,
            'user_id': shift_data.user_id,
            'shift_date': shift_data.shift_date.strftime('%Y-%m-%d') if shift_data.shift_date else '',
            'shift_type': shift_data.shift_type,
            'start_time': shift_data.start_time.strftime('%H:%M') if shift_data.start_time else '',
            'end_time': shift_data.end_time.strftime('%H:%M') if shift_data.end_time else '',
            'notes': shift_data.notes or '',
            'created_at': shift_data.created_at.strftime('%Y-%m-%d') if shift_data.created_at else '',
            'username': username,
        }

        users_rows = db.query(User.id, User.username).order_by(User.username).all()
        users = [{'id': r[0], 'username': r[1]} for r in users_rows]

        if request.method == 'POST':
            logger.debug("Данные формы редактирования: user_id=%s, shift_date=%s, shift_type=%s",
                         request.form.get('user_id', ''), request.form.get('shift_date', ''),
                         request.form.get('shift_type', ''))

            user_id = request.form['user_id']
            shift_date = request.form['shift_date']
            shift_type = request.form['shift_type']
            start_time = request.form.get('start_time', '')
            end_time = request.form.get('end_time', '')
            notes = request.form.get('notes', '')

            # Валидация
            if not user_id or not shift_date:
                logger.warning("Валидация не пройдена при редактировании: пустой user_id или shift_date")
                flash('Сотрудник и дата смены обязательны для заполнения', 'error')
                return render_template('shifts/edit_shift.html', shift=shift, users=users)

            # Проверка через ORM (исключая текущую запись)
            existing_shift = db.query(Shift.id).filter(
                Shift.user_id == int(user_id),
                Shift.shift_date == shift_date,
                Shift.id != shift_id
            ).first()

            if existing_shift:
                logger.warning("Дубликат смены при редактировании: user_id=%s, shift_date=%s",
                               user_id, shift_date)
                flash('У этого сотрудника уже есть смена на указанную дату', 'error')
                return render_template('shifts/edit_shift.html', shift=shift, users=users)

            try:
                logger.info("Обновление смены: shift_id=%s, user_id=%s, shift_date=%s, shift_type=%s",
                             shift_id, user_id, shift_date, shift_type)
                db.query(Shift).filter(Shift.id == shift_id).update({
                    Shift.user_id: int(user_id),
                    Shift.shift_date: shift_date,
                    Shift.shift_type: shift_type,
                    Shift.start_time: start_time or None,
                    Shift.end_time: end_time or None,
                    Shift.notes: notes,
                    Shift.updated_at: func.now(),
                })
                db.commit()
                logger.info("Смена обновлена успешно, shift_id=%s", shift_id)
                flash('Смена успешно обновлена!', 'success')
                return redirect(url_for('shifts.shifts_list'))
            except Exception as e:
                db.rollback()
                logger.error("Ошибка при обновлении смены shift_id=%s: %s", shift_id, str(e), exc_info=True)
                flash(f'Ошибка при обновлении смены: {str(e)}', 'error')
    except Exception as e:
        logger.error("Ошибка при загрузке смены для редактирования shift_id=%s: %s", shift_id, str(e), exc_info=True)
        flash(f'Ошибка при загрузке смены для редактирования: {str(e)}', 'error')
        return redirect(url_for('shifts.shifts_list'))

    logger.debug("Рендер формы редактирования смены, shift_id=%s", shift_id)
    return render_template('shifts/edit_shift.html', shift=shift, users=users)

@bluprint_shifts_routes.route('/delete_shift/<int:shift_id>')
@permissions_required([Permissions.shifts_manage])
def delete_shift(shift_id):
    logger.info("Запуск delete_shift, shift_id=%s", shift_id)
    db = get_db()

    try:
        db.query(Shift).filter(Shift.id == shift_id).delete()
        db.commit()
        logger.info("Смена удалена успешно, shift_id=%s", shift_id)
        flash('Смена успешно удалена!', 'success')
    except Exception as e:
        db.rollback()
        logger.error("Ошибка при удалении смены shift_id=%s: %s", shift_id, str(e), exc_info=True)
        flash(f'Ошибка при удалении смены: {str(e)}', 'error')

    return redirect(url_for('shifts.shifts_list'))
