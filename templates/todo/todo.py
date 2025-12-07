from flask import render_template, request, redirect, url_for, flash, session, Blueprint
from templates.base.database import get_db
from templates.base.requirements import permission_required
from templates.roles.permissions import Permissions
from templates.base.organization_utils import get_user_organizations_list, has_organization_access

bluprint_todo_routes = Blueprint("todo", __name__)

@bluprint_todo_routes.route('/todos')
@permission_required(Permissions.todo_read)
def todo():
    db = get_db()
    user_id = session.get('user_id')
    
    organization_filter = request.args.get('organization_id', type=int)
    
    query = '''
        SELECT t.*, o.name as organization_name 
        FROM todos t
        LEFT JOIN organizations o ON t.organization_id = o.id
    '''
    params = []
    
    where_clauses = []
    
    if session.get('role') not in ['admin', 'manager']:
        where_clauses.append('''
            (t.organization_id IN (
                SELECT organization_id FROM user_organizations WHERE user_id = ?
            ) OR t.organization_id IS NULL)
        ''')
        params.append(user_id)
    
    if organization_filter:
        where_clauses.append('t.organization_id = ?')
        params.append(organization_filter)
    
    if where_clauses:
        query += ' WHERE ' + ' AND '.join(where_clauses)
    
    query += ' ORDER BY t.created_at DESC'
    
    todos_list = db.execute(query, tuple(params)).fetchall()
    
    organizations = get_user_organizations_list(user_id, include_all=True)
    
    return render_template('todo/todo.html', 
                         todos=todos_list,
                         organizations=organizations,
                         selected_org=organization_filter)

@bluprint_todo_routes.route('/add_todo', methods=['GET', 'POST'])
@permission_required(Permissions.todo_manage)
def add_todo():
    db = get_db()
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form.get('description', '')
        status = request.form.get('status', 'Новая')
        priority = request.form.get('priority', 'Средний')
        due_date = request.form.get('due_date', None)
        organization_id = request.form.get('organization_id', None)
        
        if not title:
            flash('Название задачи обязательно', 'error')
            return redirect(url_for('todo.add_todo'))
        
        # Проверяем доступ к организации
        if organization_id and not has_organization_access(user_id, organization_id):
            flash('У вас нет доступа к выбранной организации', 'error')
            return redirect(url_for('todo.add_todo'))
        
        try:
            db.execute('''
                INSERT INTO todos (title, description, status, priority, due_date, organization_id, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (title, description, status, priority, due_date, organization_id, user_id))
            db.commit()
            flash('Задача успешно добавлена!', 'success')
            return redirect(url_for('todo.todo'))
        except Exception as e:
            flash(f'Ошибка при добавлении задачи: {str(e)}', 'error')
    
    organizations = get_user_organizations_list(user_id)
    
    return render_template('todo/add_todo.html', organizations=organizations)

@bluprint_todo_routes.route('/edit_todo/<int:todo_id>', methods=['GET', 'POST'])
@permission_required(Permissions.todo_manage)
def edit_todo(todo_id):
    db = get_db()
    user_id = session.get('user_id')
    
    todo_item = db.execute('SELECT * FROM todos WHERE id = ?', (todo_id,)).fetchone()
    
    if not todo_item:
        flash('Задача не найдена', 'error')
        return redirect(url_for('todo.todo'))
    
    # Проверяем доступ к организации задачи
    if todo_item['organization_id'] and not has_organization_access(user_id, todo_item['organization_id']):
        flash('У вас нет доступа к этой задаче', 'error')
        return redirect(url_for('todo.todo'))
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form.get('description', '')
        status = request.form.get('status', 'Новая')
        priority = request.form.get('priority', 'Средний')
        due_date = request.form.get('due_date', None)
        organization_id = request.form.get('organization_id', None)
        
        if not title:
            flash('Название задачи обязательно', 'error')
            return redirect(url_for('todo.edit_todo', todo_id=todo_id))
        
        # Проверяем доступ к новой организации
        if organization_id and organization_id != todo_item['organization_id']:
            if not has_organization_access(user_id, organization_id):
                flash('У вас нет доступа к выбранной организации', 'error')
                return redirect(url_for('todo.edit_todo', todo_id=todo_id))
        
        try:
            db.execute('''
                UPDATE todos SET 
                title=?, description=?, status=?, priority=?, due_date=?, organization_id=?
                WHERE id=?
            ''', (title, description, status, priority, due_date, organization_id, todo_id))
            db.commit()
            flash('Задача успешно обновлена!', 'success')
            return redirect(url_for('todo.todo'))
        except Exception as e:
            flash(f'Ошибка при обновлении задачи: {str(e)}', 'error')
    
    organizations = get_user_organizations_list(user_id)
    
    return render_template('todo/edit_todo.html', 
                         todo=todo_item,
                         organizations=organizations)