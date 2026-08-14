from logger import logger

from flask import render_template, request, redirect, url_for, flash, session, Blueprint

from templates.base.database import get_db
from templates.base.requirements import permissions_required, permissions_required_all, permissions_required
from templates.roles.permissions import Permissions
from datetime import datetime
from sqlalchemy import text, func, case, and_, or_, Integer

from models import Todo, Organization

from templates.base.navigation import create_main_menu

bluprint_todo_routes = Blueprint("todo", __name__)


@bluprint_todo_routes.route('/todo')
@permissions_required([Permissions.todo_read])
def todo():
    logger.info("Запуск todo")
    db = get_db()

    # Получаем параметр показа выполненных задач
    show_completed = request.args.get('show_completed', 'false').lower() == 'true'
    logger.debug("Параметры: show_completed=%s", show_completed)

    try:
        # Базовый запрос через ORM с LEFT JOIN
        query = db.query(Todo, Organization.name).outerjoin(
            Organization, Todo.organization_id == Organization.id
        )

        # Фильтр по выполненным задачам
        if not show_completed:
            query = query.filter(or_(Todo.is_completed == False, Todo.is_completed.is_(None)))
            logger.debug("Добавлен фильтр: показаны только невыполненные задачи")

        # Порядок сортировки через CASE
        status_order = case(
            (Todo.status == 'в работе', 1),
            (Todo.status == 'новая', 2),
            (Todo.status == 'отложена', 3),
            else_=4
        )
        priority_order = case(
            (Todo.priority == 'критичный', 1),
            (Todo.priority == 'высокий', 2),
            (Todo.priority == 'средний', 3),
            else_=4
        )

        query = query.order_by(
            status_order,
            priority_order,
            Todo.due_date.asc().nullslast(),
            Todo.created_at.desc()
        )

        todos_rows = query.all()
        logger.info("Найдено задач: %d", len(todos_rows))

        # Обрабатываем даты для шаблона
        today = datetime.now().date()
        processed_todos = []

        for task, org_name in todos_rows:
            task_dict = {
                'id': task.id,
                'title': task.title,
                'description': task.description or '',
                'status': task.status,
                'priority': task.priority,
                'organization_id': task.organization_id,
                'organization_name': org_name or 'Не указана',
                'due_date': task.due_date.strftime('%Y-%m-%d') if task.due_date else None,
                'is_completed': task.is_completed or 0,
                'is_overdue': False,
                'created_at': task.created_at.strftime('%Y-%m-%d') if task.created_at else '',
                'completed_at': task.completed_at.strftime('%Y-%m-%d') if task.completed_at else None,
                'completed_date': task.completed_at.strftime('%Y-%m-%d') if task.completed_at else '',
            }

            # Определяем, просрочена ли задача
            due_date_val = None
            if task.due_date:
                if isinstance(task.due_date, str):
                    try:
                        due_date_val = datetime.strptime(task.due_date, '%Y-%m-%d').date()
                    except ValueError:
                        pass
                elif hasattr(task.due_date, 'date'):
                    due_date_val = task.due_date.date()

            if due_date_val and not task.is_completed:
                task_dict['is_overdue'] = due_date_val < today

            processed_todos.append(task_dict)

        # Получаем статистику по всем задачам
        all_stats = db.query(
            func.count(Todo.id).label('total'),
            func.coalesce(func.sum(Todo.is_completed.cast(Integer)), 0).label('completed_total')
        ).one_or_none()

        in_progress = len([t for t in processed_todos if t['status'] == 'в работе'])
        completed_count = len([t for t in processed_todos if t['is_completed'] == 1])
        total_tasks = len(processed_todos)

        logger.info("Статистика: всего=%d, в работе=%d, выполнено=%d, пропущено=%d",
                     total_tasks, in_progress, completed_count,
                     len([t for t in processed_todos if t['is_overdue']]))

        logger.info("todo завершено успешно")
        return render_template('todo/todo.html',
                             todos=processed_todos,
                             total_tasks=total_tasks,
                             in_progress=in_progress,
                             completed_count=completed_count,
                             show_completed=show_completed,
                             all_tasks_total=all_stats.total or 0,
                             all_tasks_completed=all_stats.completed_total or 0,
                             today=today)

    except Exception as e:
        logger.error("Ошибка в todo: %s", str(e), exc_info=True)
        flash(f'Ошибка при загрузке задач: {str(e)}', 'error')
        return render_template('todo/todo.html',
                             todos=[], total_tasks=0, in_progress=0,
                             completed_count=0, show_completed=show_completed,
                             all_tasks_total=0, all_tasks_completed=0,
                             today=datetime.now().date())


@bluprint_todo_routes.route('/add_todo', methods=['GET', 'POST'])
@permissions_required([Permissions.todo_manage])
def add_todo():
    logger.info("Запуск add_todo, метод=%s", request.method)
    db = get_db()

    # Получаем организации для выпадающего списка
    orgs_rows = db.query(Organization.id, Organization.name).order_by(Organization.name).all()
    organizations = [{'id': r[0], 'name': r[1]} for r in orgs_rows]

    if request.method == 'POST':
        logger.debug("Данные формы: title=%s, status=%s, priority=%s",
                      request.form.get('title', ''), request.form.get('status', ''),
                      request.form.get('priority', ''))

        title = request.form['title']
        description = request.form.get('description', '')
        status = request.form['status']
        priority = request.form['priority']
        organization_id = request.form.get('organization_id') or None
        due_date_str = request.form.get('due_date', '')

        # Валидация
        if not title:
            logger.warning("Валидация не пройдена: пустой title")
            flash('Название задачи обязательно для заполнения', 'error')
            return render_template('todo/add_todo.html', organizations=organizations)

        # Преобразуем дату
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                logger.warning("Неверный формат даты: %s", due_date_str)
                flash('Неверный формат даты', 'error')
                return render_template('todo/add_todo.html', organizations=organizations)

        try:
            logger.info("Создание новой задачи: title=%s, status=%s, priority=%s",
                        title, status, priority)
            task = Todo(
                title=title,
                description=description,
                status=status,
                priority=priority,
                organization_id=organization_id,
                due_date=due_date,
            )
            db.add(task)
            db.commit()
            logger.info("Задача добавлена успешно, id=%s title=%s", task.id, task.title)
            flash('Задача успешно добавлена!', 'success')
            return redirect(url_for('todo.todo'))
        except Exception as e:
            db.rollback()
            logger.error("Ошибка при добавлении задачи: %s", str(e), exc_info=True)
            flash(f'Ошибка при добавлении задачи: {str(e)}', 'error')

    logger.debug("Рендер формы добавления задачи")
    return render_template('todo/add_todo.html', organizations=organizations)


@bluprint_todo_routes.route('/edit_todo/<int:todo_id>', methods=['GET', 'POST'])
@permissions_required([Permissions.todo_manage])
def edit_todo(todo_id):
    logger.info("Запуск edit_todo, todo_id=%s, метод=%s", todo_id, request.method)
    db = get_db()

    try:
        # Получаем задачу через ORM
        task_row = db.query(Todo, Organization.name).outerjoin(
            Organization, Todo.organization_id == Organization.id
        ).filter(Todo.id == todo_id).first()

        if not task_row:
            logger.warning("Задача не найдена: todo_id=%s", todo_id)
            flash('Задача не найдена', 'error')
            return redirect(url_for('todo.todo'))

        task_data, org_name = task_row

        task_dict = {
            'id': task_data.id,
            'title': task_data.title,
            'description': task_data.description or '',
            'status': task_data.status,
            'priority': task_data.priority,
            'organization_id': task_data.organization_id,
            'organization_name': org_name or 'Не указана',
            'is_completed': task_data.is_completed or 0,
            'due_date': task_data.due_date.strftime('%Y-%m-%d') if task_data.due_date else '',
        }

        orgs_rows = db.query(Organization.id, Organization.name).order_by(Organization.name).all()
        organizations = [{'id': r[0], 'name': r[1]} for r in orgs_rows]

        if request.method == 'POST':
            logger.debug("Данные формы редактирования: todo_id=%s, title=%s, status=%s",
                         todo_id,
                         request.form.get('title', ''),
                         request.form.get('status', ''))

            title = request.form['title']
            description = request.form.get('description', '')
            status = request.form['status']
            priority = request.form['priority']
            organization_id = request.form.get('organization_id') or None
            due_date_str = request.form.get('due_date', '')
            is_completed = request.form.get('is_completed') == '1'

            # Валидация
            if not title:
                logger.warning("Валидация не пройдена при редактировании: пустой title")
                flash('Название задачи обязательно для заполнения', 'error')
                return render_template('todo/edit_todo.html', task=task_dict, organizations=organizations)

            # Преобразуем дату
            due_date = None
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                except ValueError:
                    logger.warning("Неверный формат даты при редактировании: %s", due_date_str)
                    flash('Неверный формат даты', 'error')
                    return render_template('todo/edit_todo.html', task=task_dict, organizations=organizations)

            # Определяем completed_at
            completed_at = None
            if is_completed and not task_data.is_completed:
                completed_at = datetime.now()
                logger.info("Задача помечается как выполненная: todo_id=%s", todo_id)
            elif not is_completed and task_data.is_completed:
                completed_at = None
                logger.info("Задача возвращается в работу: todo_id=%s", todo_id)

            try:
                logger.info("Обновление задачи: todo_id=%s, title=%s, status=%s, priority=%s",
                            todo_id, title, status, priority)
                db.query(Todo).filter(Todo.id == todo_id).update({
                    Todo.title: title,
                    Todo.description: description,
                    Todo.status: status,
                    Todo.priority: priority,
                    Todo.organization_id: organization_id,
                    Todo.due_date: due_date,
                    Todo.is_completed: is_completed,
                    Todo.completed_at: completed_at,
                    Todo.updated_at: func.now(),
                })
                db.commit()
                logger.info("Задача обновлена успешно: todo_id=%s", todo_id)
                flash('Задача успешно обновлена!', 'success')
                return redirect(url_for('todo.todo'))
            except Exception as e:
                db.rollback()
                logger.error("Ошибка при обновлении задачи todo_id=%s: %s", todo_id, str(e), exc_info=True)
                flash(f'Ошибка при обновлении задачи: {str(e)}', 'error')

    except Exception as e:
        logger.error("Ошибка в edit_todo для todo_id=%s: %s", todo_id, str(e), exc_info=True)
        flash(f'Ошибка при загрузке задачи: {str(e)}', 'error')
        return redirect(url_for('todo.todo'))

    logger.debug("Рендер формы редактирования задачи: todo_id=%s", todo_id)
    return render_template('todo/edit_todo.html', task=task_dict, organizations=organizations)


@bluprint_todo_routes.route('/delete_todo/<int:todo_id>')
@permissions_required([Permissions.todo_manage])
def delete_todo(todo_id):
    logger.info("Запуск delete_todo, todo_id=%s", todo_id)
    db = get_db()

    try:
        db.query(Todo).filter(Todo.id == todo_id).delete()
        db.commit()
        logger.info("Задача удалена успешно: todo_id=%s", todo_id)
        flash('Задача успешно удалена!', 'success')
    except Exception as e:
        db.rollback()
        logger.error("Ошибка при удалении задачи todo_id=%s: %s", todo_id, str(e), exc_info=True)
        flash(f'Ошибка при удалении задачи: {str(e)}', 'error')

    return redirect(url_for('todo.todo'))


@bluprint_todo_routes.route('/complete_todo/<int:todo_id>')
@permissions_required([Permissions.todo_manage])
def complete_todo(todo_id):
    """Отметить задачу как выполненную"""
    logger.info("Запуск complete_todo, todo_id=%s", todo_id)
    db = get_db()

    try:
        db.query(Todo).filter(Todo.id == todo_id).update({
            Todo.status: 'выполнена',
            Todo.is_completed: True,
            Todo.completed_at: func.now(),
            Todo.updated_at: func.now(),
        })
        db.commit()
        logger.info("Задача отмечена как выполненная: todo_id=%s", todo_id)
        flash('Задача отмечена как выполненная!', 'success')
    except Exception as e:
        db.rollback()
        logger.error("Ошибка при выполнении задачи todo_id=%s: %s", todo_id, str(e), exc_info=True)
        flash(f'Ошибка при выполнении задачи: {str(e)}', 'error')

    return redirect(url_for('todo.todo'))


@bluprint_todo_routes.route('/reopen_todo/<int:todo_id>')
@permissions_required([Permissions.todo_manage])
def reopen_todo(todo_id):
    """Вернуть задачу в работу"""
    logger.info("Запуск reopen_todo, todo_id=%s", todo_id)
    db = get_db()

    try:
        db.query(Todo).filter(Todo.id == todo_id).update({
            Todo.status: 'в работе',
            Todo.is_completed: False,
            Todo.completed_at: None,
            Todo.updated_at: func.now(),
        })
        db.commit()
        logger.info("Задача возвращена в работу: todo_id=%s", todo_id)
        flash('Задача возвращена в работу!', 'success')
    except Exception as e:
        db.rollback()
        logger.error("Ошибка при возврате задачи todo_id=%s: %s", todo_id, str(e), exc_info=True)
        flash(f'Ошибка при возврате задачи: {str(e)}', 'error')

    return redirect(url_for('todo.todo'))


@bluprint_todo_routes.route('/toggle_completed')
@permissions_required([Permissions.todo_manage])
def toggle_completed():
    """Переключить отображение выполненных задач"""
    show_completed = request.args.get('show_completed', 'false') == 'true'
    return redirect(url_for('todo.todo', show_completed=show_completed))
