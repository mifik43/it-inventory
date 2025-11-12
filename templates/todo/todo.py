from flask import render_template, request, redirect, url_for, flash, session, Blueprint

from templates.base.database import get_db
from templates.base.requirements import permission_required, permissions_required_all, permissions_required_any
from templates.roles.permissions import Permissions

from datetime import datetime

bluprint_todo_routes = Blueprint("todo", __name__)


@bluprint_todo_routes.route('/todo')
@permission_required(Permissions.todo_reads)
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

@bluprint_todo_routes.route('/add_todo', methods=['GET', 'POST'])
@permission_required(Permissions.todo_manage)
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
            return redirect(url_for('todo.todo'))
        except Exception as e:
            flash(f'Ошибка при добавлении задачи: {str(e)}', 'error')
    
    return render_template('todo/add_todo.html', organizations=organizations)

@bluprint_todo_routes.route('/edit_todo/<int:todo_id>', methods=['GET', 'POST'])
@permission_required(Permissions.todo_manage)
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
        return redirect(url_for('todo.todo'))
    
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
            return redirect(url_for('todo.todo'))
        except Exception as e:
            flash(f'Ошибка при обновлении задачи: {str(e)}', 'error')
    
    return render_template('todo/edit_todo.html', task=task_dict, organizations=organizations)

@bluprint_todo_routes.route('/delete_todo/<int:todo_id>')
@permission_required(Permissions.todo_manage)
def delete_todo(todo_id):
    db = get_db()
    try:
        db.execute('DELETE FROM todos WHERE id = ?', (todo_id,))
        db.commit()
        flash('Задача успешно удалена!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении задачи: {str(e)}', 'error')
    
    return redirect(url_for('todo.todo'))

@bluprint_todo_routes.route('/complete_todo/<int:todo_id>')
@permission_required(Permissions.todo_manage)
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
    
    return redirect(url_for('todo.todo'))

@bluprint_todo_routes.route('/reopen_todo/<int:todo_id>')
@permission_required(Permissions.todo_manage)
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
    
    return redirect(url_for('todo.todo'))

@bluprint_todo_routes.route('/toggle_completed')
@permission_required(Permissions.todo_manage)
def toggle_completed():
    """Переключить отображение выполненных задач"""
    show_completed = request.args.get('show_completed', 'false') == 'true'
    return redirect(url_for('todo.todo', show_completed=show_completed))
