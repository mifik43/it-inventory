from flask import render_template, request, redirect, url_for, flash, session, Blueprint

from templates.base.database import get_db
from templates.base.requirements import permission_required, permissions_required_all, permissions_required_any
from templates.roles.permissions import Permissions

bluprint_script_routes = Blueprint("script", __name__)


# ========== МАРШРУТЫ ДЛЯ СКРИПТОВ ==========

@bluprint_script_routes.route('/scripts')
def script_list():  # Изменили имя с scripts_list на script_list
    """Список всех скриптов"""
    db = get_db()
    scripts = db.execute('''
        SELECT s.*, 
               COUNT(sr.id) as execution_count,
               MAX(sr.executed_at) as last_executed
        FROM scripts s 
        LEFT JOIN script_results sr ON s.id = sr.script_id 
        GROUP BY s.id
        ORDER BY s.created_at DESC
    ''').fetchall()
    
    return render_template('scripts/scripts_list.html', scripts=scripts)

@bluprint_script_routes.route('/add_script', methods=['GET', 'POST'])
def add_script():  # Изменили имя с add_script на script_add
    """Добавление нового скрипта"""
    if request.method == 'POST':
        name = request.form['name']
        description = request.form.get('description', '')
        filename = request.form['filename']
        content = request.form['content']
        
        # Валидация
        if not name or not filename or not content:
            flash('Название, имя файла и содержимое обязательны', 'error')
            return render_template('scripts/add_script.html')
        
        # Проверяем расширение файла
        allowed_extensions = {'bat', 'ps1'}
        file_ext = filename.split('.')[-1].lower()
        if file_ext not in allowed_extensions:
            flash('Разрешены только файлы с расширениями .bat и .ps1', 'error')
            return render_template('scripts/add_script.html')
        
        db = get_db()
        try:
            db.execute('''
                INSERT INTO scripts (name, description, filename, content)
                VALUES (?, ?, ?, ?)
            ''', (name, description, filename, content))
            db.commit()
            flash('Скрипт успешно добавлен!', 'success')
            return redirect(url_for('script.script_list'))  # Обновили ссылку
        except Exception as e:
            flash(f'Ошибка при добавлении скрипта: {str(e)}', 'error')
    
    return render_template('scripts/add_script.html')

@bluprint_script_routes.route('/edit_script/<int:script_id>', methods=['GET', 'POST'])
def script_edit(script_id):  # Изменили имя с edit_script на script_edit
    """Редактирование скрипта"""
    db = get_db()
    script = db.execute('SELECT * FROM scripts WHERE id = ?', (script_id,)).fetchone()
    
    if not script:
        flash('Скрипт не найден', 'error')
        return redirect(url_for('script.script_list'))  # Обновили ссылку
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form.get('description', '')
        filename = request.form['filename']
        content = request.form['content']
        
        # Валидация
        if not name or not filename or not content:
            flash('Название, имя файла и содержимое обязательны', 'error')
            return render_template('scripts/edit_script.html', script=script)
        
        # Проверяем расширение файла
        allowed_extensions = {'bat', 'ps1'}
        file_ext = filename.split('.')[-1].lower()
        if file_ext not in allowed_extensions:
            flash('Разрешены только файлы с расширениями .bat и .ps1', 'error')
            return render_template('scripts/edit_script.html', script=script)
        
        try:
            db.execute('''
                UPDATE scripts SET 
                name=?, description=?, filename=?, content=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (name, description, filename, content, script_id))
            db.commit()
            flash('Скрипт успешно обновлен!', 'success')
            return redirect(url_for('script.script_list'))  # Обновили ссылку
        except Exception as e:
            flash(f'Ошибка при обновлении скрипта: {str(e)}', 'error')
    
    return render_template('scripts/edit_script.html', script=script)

@bluprint_script_routes.route('/delete_script/<int:script_id>')
def script_delete(script_id):  # Изменили имя с delete_script на script_delete
    """Удаление скрипта"""
    db = get_db()
    
    try:
        # Сначала удаляем результаты выполнения
        db.execute('DELETE FROM script_results WHERE script_id = ?', (script_id,))
        # Затем удаляем сам скрипт
        db.execute('DELETE FROM scripts WHERE id = ?', (script_id,))
        db.commit()
        flash('Скрипт и все связанные результаты успешно удалены!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении скрипта: {str(e)}', 'error')
    
    return redirect(url_for('script.script_list'))  # Обновили ссылку

@bluprint_script_routes.route('/run_script/<int:script_id>')
def script_run(script_id):  # Изменили имя с run_script на script_run
    """Выполнение скрипта"""
    db = get_db()
    script = db.execute('SELECT * FROM scripts WHERE id = ?', (script_id,)).fetchone()
    
    if not script:
        flash('Скрипт не найден', 'error')
        return redirect(url_for('script.script_list'))  # Обновили ссылку
    
    try:
        # Определяем тип скрипта по расширению
        script_type = script['filename'].split('.')[-1].lower()
        
        # Выполняем скрипт
        result = execute_script(script['content'], script_type)
        
        # Сохраняем результат
        save_script_result(db, script_id, result)
        
        if result['success']:
            flash('Скрипт успешно выполнен!', 'success')
        else:
            flash('Скрипт выполнен с ошибками', 'warning')
        
        # Показываем результат
        return render_template('scripts/script_result.html', 
                             script=script, 
                             result=result,
                             execution_time=result.get('execution_time', 0))
        
    except Exception as e:
        flash(f'Ошибка при выполнении скрипта: {str(e)}', 'error')
        # Создаем объект результата с ошибкой для отображения
        error_result = {
            'success': False,
            'output': '',
            'error': str(e),
            'return_code': -1,
            'execution_time': 0
        }
        return render_template('scripts/script_result.html', 
                             script=script, 
                             result=error_result,
                             execution_time=0)

@bluprint_script_routes.route('/view_script_results/<int:script_id>')
def script_results(script_id):  # Обратите внимание на имя функции
    """Просмотр истории выполнения скрипта"""
    db = get_db()
    script = db.execute('SELECT * FROM scripts WHERE id = ?', (script_id,)).fetchone()
    
    if not script:
        flash('Скрипт не найден', 'error')
        return redirect(url_for('script.script_list'))
    
    results = script_results(db, script_id, 20)
    
    return render_template('scripts/script_results.html', 
                         script=script, 
                         results=results)

@bluprint_script_routes.route('/view_script/<int:script_id>')
def script_view(script_id):  # Изменили имя с view_script на script_view
    """Просмотр содержимого скрипта"""
    db = get_db()
    script = db.execute('SELECT * FROM scripts WHERE id = ?', (script_id,)).fetchone()
    
    if not script:
        flash('Скрипт не найден', 'error')
        return redirect(url_for('script.script_list'))  # Обновили ссылку
    
    return render_template('scripts/view_script.html', script=script)

@bluprint_script_routes.route('/download_script/<int:script_id>')
def script_download(script_id):  # Изменили имя с download_script на script_download
    """Скачивание скрипта"""
    db = get_db()
    script = db.execute('SELECT * FROM scripts WHERE id = ?', (script_id,)).fetchone()
    
    if not script:
        flash('Скрипт не найден', 'error')
        return redirect(url_for('script.script_list'))  # Обновили ссылку
    
    # Создаем ответ с содержимым скрипта
    response = Response(
        script['content'],
        mimetype="text/plain",
        headers={
            "Content-Disposition": f"attachment;filename={script['filename']}",
            "Content-Type": "text/plain; charset=utf-8"
        }
    )
    
    return response