from flask import render_template, request, redirect, url_for, flash, Blueprint, Response
from sqlalchemy import func

from templates.base.database_helper import db
from templates.base.requirements import permissions_required, permissions_required_all, permissions_required
from script_utils import execute_script
from models import Script, ScriptResult
from logger import logger

bluprint_script_routes = Blueprint("script", __name__)


# ========== МАРШРУТЫ ДЛЯ СКРИПТОВ ==========

@bluprint_script_routes.route('/scripts')
def script_list():  # Изменили имя с scripts_list на script_list
    """Список всех скриптов"""
    logger.info('Открыт список скриптов')
    script_rows = db.session.query(
        Script,
        func.count(ScriptResult.id).label('execution_count'),
        func.max(ScriptResult.executed_at).label('last_executed')
    ).outerjoin(ScriptResult, Script.id == ScriptResult.script_id)
    script_rows = script_rows.group_by(Script.id).order_by(Script.created_at.desc()).all()

    scripts = []
    for script, execution_count, last_executed in script_rows:
        script_data = {column.name: getattr(script, column.name) for column in script.__table__.columns}
        script_data['execution_count'] = execution_count
        script_data['last_executed'] = last_executed
        scripts.append(script_data)
    
    logger.debug(f'Загружено скриптов: {len(scripts)}')
    return render_template('scripts/scripts_list.html', scripts=scripts)

@bluprint_script_routes.route('/add_script', methods=['GET', 'POST'])
def add_script():  # Изменили имя с add_script на script_add
    """Добавление нового скрипта"""
    logger.info('Открыта страница добавления скрипта')
    if request.method == 'POST':
        logger.info('Запрос на добавление скрипта получен')
        name = request.form['name']
        description = request.form.get('description', '')
        filename = request.form['filename']
        content = request.form['content']

        # Валидация
        if not name or not filename or not content:
            logger.warning(f'Попытка добавить скрипт с пустыми полями: name={bool(name)}, filename={bool(filename)}, content={bool(content)}')
            flash('Название, имя файла и содержимое обязательны', 'error')
            return render_template('scripts/add_script.html')

        # Проверяем расширение файла
        allowed_extensions = {'bat', 'ps1'}
        file_ext = filename.split('.')[-1].lower()
        if file_ext not in allowed_extensions:
            logger.warning(f'Неверное расширение файла при добавлении скрипта: {file_ext}')
            flash('Разрешены только файлы с расширениями .bat и .ps1', 'error')
            return render_template('scripts/add_script.html')

        try:
            logger.debug(f'Параметры нового скрипта: name={name}, filename={filename}')
            script = Script(
                name=name,
                description=description,
                filename=filename,
                content=content
            )
            db.session.add(script)
            db.session.commit()
            logger.info(f'Скрипт добавлен: id={script.id} name={script.name} filename={script.filename}')
            flash('Скрипт успешно добавлен!', 'success')
            return redirect(url_for('script.script_list'))  # Обновили ссылку
        except Exception as e:
            db.session.rollback()
            logger.error(f'Ошибка при добавлении скрипта: {e}', exc_info=True)
            flash(f'Ошибка при добавлении скрипта: {str(e)}', 'error')

    return render_template('scripts/add_script.html')

@bluprint_script_routes.route('/edit_script/<int:script_id>', methods=['GET', 'POST'])
def script_edit(script_id):  # Изменили имя с edit_script на script_edit
    """Редактирование скрипта"""
    logger.info(f'Открыта страница редактирования скрипта: id={script_id}')
    script = Script.query.get(script_id)
    
    if not script:
        logger.warning(f'Скрипт не найден для редактирования: id={script_id}')
        flash('Скрипт не найден', 'error')
        return redirect(url_for('script.script_list'))  # Обновили ссылку
    
    if request.method == 'POST':
        logger.info(f'Запрос на обновление скрипта получен: id={script_id}')
        name = request.form['name']
        description = request.form.get('description', '')
        filename = request.form['filename']
        content = request.form['content']
        
        # Валидация
        if not name or not filename or not content:
            logger.warning(f'Попытка обновить скрипт с пустыми полями: id={script_id}')
            flash('Название, имя файла и содержимое обязательны', 'error')
            return render_template('scripts/edit_script.html', script=script)
        
        # Проверяем расширение файла
        allowed_extensions = {'bat', 'ps1'}
        file_ext = filename.split('.')[-1].lower()
        if file_ext not in allowed_extensions:
            logger.warning(f'Неверное расширение файла при редактировании скрипта id={script_id}: {file_ext}')
            flash('Разрешены только файлы с расширениями .bat и .ps1', 'error')
            return render_template('scripts/edit_script.html', script=script)
        
        try:
            logger.debug(f'Новые параметры скрипта id={script_id}: name={name}, filename={filename}')
            script.name = name
            script.description = description
            script.filename = filename
            script.content = content
            db.session.commit()
            logger.info(f'Скрипт обновлен: id={script_id} name={script.name}')
            flash('Скрипт успешно обновлен!', 'success')
            return redirect(url_for('script.script_list'))  # Обновили ссылку
        except Exception as e:
            db.session.rollback()
            logger.error(f'Ошибка при обновлении скрипта id={script_id}: {e}', exc_info=True)
            flash(f'Ошибка при обновлении скрипта: {str(e)}', 'error')
    
    return render_template('scripts/edit_script.html', script=script)

@bluprint_script_routes.route('/delete_script/<int:script_id>')
def script_delete(script_id):  # Изменили имя с delete_script на script_delete
    """Удаление скрипта"""
    logger.info(f'Запрос на удаление скрипта: id={script_id}')
    script = Script.query.get(script_id)

    if not script:
        logger.warning(f'Скрипт не найден для удаления: id={script_id}')
        flash('Скрипт не найден', 'error')
        return redirect(url_for('script.script_list'))

    try:
        logger.info(f'Удаление скрипта: id={script_id} name={script.name}')
        ScriptResult.query.filter_by(script_id=script_id).delete()
        db.session.delete(script)
        db.session.commit()
        logger.info(f'Скрипт успешно удален: id={script_id}')
        flash('Скрипт и все связанные результаты успешно удалены!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Ошибка при удалении скрипта id={script_id}: {e}', exc_info=True)
        flash(f'Ошибка при удалении скрипта: {str(e)}', 'error')

    return redirect(url_for('script.script_list'))  # Обновили ссылку

@bluprint_script_routes.route('/run_script/<int:script_id>')
def script_run(script_id):  # Изменили имя с run_script на script_run
    """Выполнение скрипта"""
    logger.info(f'Запрос на выполнение скрипта: id={script_id}')
    script = Script.query.get(script_id)

    if not script:
        logger.warning(f'Скрипт не найден для выполнения: id={script_id}')
        flash('Скрипт не найден', 'error')
        return redirect(url_for('script.script_list'))  # Обновили ссылку

    try:
        logger.info(f'Начало выполнения скрипта: id={script_id} name={script.name}')
        script_type = script.filename.split('.')[-1].lower()
        logger.debug(f'Тип скрипта: {script_type}')
        result = execute_script(script.content, script_type)
        logger.debug(f'Выполнение завершено: success={result["success"]}, execution_time={result["execution_time"]}')

        try:
            script_result = ScriptResult(
                script_id=script_id,
                output=result['output'],
                success=result['success'],
                error_message=result['error'],
                execution_time=result['execution_time']
            )
            db.session.add(script_result)
            db.session.commit()
            logger.debug(f'Результат сохранен для скрипта: id={script_id}')
        except Exception as save_err:
            db.session.rollback()
            logger.warning(f'Ошибка сохранения результата скрипта id={script_id}: {save_err}')

        if result['success']:
            logger.info(f'Скрипт выполнен успешно: id={script_id}')
            flash('Скрипт успешно выполнен!', 'success')
        else:
            logger.warning(f'Скрипт выполнен с ошибками: id={script_id} error={result["error"]}')
            flash('Скрипт выполнен с ошибками', 'warning')

        return render_template(
            'scripts/script_result.html', 
            script=script, 
            result=result,
            execution_time=result.get('execution_time', 0)
        )

    except Exception as e:
        logger.error(f'Ошибка при выполнении скрипта id={script_id}: {e}', exc_info=True)
        flash(f'Ошибка при выполнении скрипта: {str(e)}', 'error')
        error_result = {
            'success': False,
            'output': '',
            'error': str(e),
            'return_code': -1,
            'execution_time': 0
        }
        return render_template(
            'scripts/script_result.html', 
            script=script, 
            result=error_result,
            execution_time=0
        )

@bluprint_script_routes.route('/view_script_results/<int:script_id>')
def script_results(script_id):  # Обратите внимание на имя функции
    """Просмотр истории выполнения скрипта"""
    logger.info(f'Открыта история выполнения скрипта: id={script_id}')
    script = Script.query.get(script_id)

    if not script:
        logger.warning(f'Скрипт не найден для просмотра истории: id={script_id}')
        flash('Скрипт не найден', 'error')
        return redirect(url_for('script.script_list'))

    results = ScriptResult.query.filter_by(script_id=script_id).order_by(
        ScriptResult.executed_at.desc()
    ).limit(20).all()
    
    logger.debug(f'Загружено результатов для скрипта id={script_id}: {len(results)}')

    return render_template('scripts/script_results.html', 
                         script=script, 
                         results=results)

@bluprint_script_routes.route('/view_script/<int:script_id>')
def script_view(script_id):  # Изменили имя с view_script на script_view
    """Просмотр содержимого скрипта"""
    logger.info(f'Открыт просмотр скрипта: id={script_id}')
    script = Script.query.get(script_id)

    if not script:
        logger.warning(f'Скрипт не найден для просмотра: id={script_id}')
        flash('Скрипт не найден', 'error')
        return redirect(url_for('script.script_list'))  # Обновили ссылку

    return render_template('scripts/view_script.html', script=script)

@bluprint_script_routes.route('/download_script/<int:script_id>')
def script_download(script_id):  # Изменили имя с download_script на script_download
    """Скачивание скрипта"""
    logger.info(f'Запрос на скачивание скрипта: id={script_id}')
    script = Script.query.get(script_id)

    if not script:
        logger.warning(f'Скрипт не найден для скачивания: id={script_id}')
        flash('Скрипт не найден', 'error')
        return redirect(url_for('script.script_list'))  # Обновили ссылку

    logger.info(f'Скачивание скрипта: id={script_id} filename={script.filename}')
    response = Response(
        script.content,
        mimetype="text/plain",
        headers={
            "Content-Disposition": f"attachment;filename={script.filename}",
            "Content-Type": "text/plain; charset=utf-8"
        }
    )

    return response