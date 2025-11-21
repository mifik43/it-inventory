from flask import render_template, request, redirect, url_for, flash, session, Blueprint

from templates.base.database import get_db
from templates.base.requirements import permission_required, permissions_required_all, permissions_required_any
from templates.roles.permissions import Permissions

bluprint_wtware_routes = Blueprint("wtware", __name__)



# ========== МАРШРУТЫ ДЛЯ WTWARE ==========

@bluprint_wtware_routes.route('/wtware')
def wtware_list():
    db = get_db()
    configs = db.execute('''
        SELECT * FROM wtware_configs 
        ORDER BY name, created_at DESC
    ''').fetchall()
    return render_template('wtware/wtware_list.html', configs=configs)

@bluprint_wtware_routes.route('/add_wtware', methods=['GET', 'POST'])
def add_wtware():
    if request.method == 'POST':
        name = request.form['name']
        version = request.form.get('version', '')
        server_ip = request.form.get('server_ip', '')
        server_port = request.form.get('server_port', 80)
        screen_width = request.form.get('screen_width', 1024)
        screen_height = request.form.get('screen_height', 768)
        auto_start = request.form.get('auto_start', '')
        network_drive = request.form.get('network_drive', '')
        printer_config = request.form.get('printer_config', '')
        startup_script = request.form.get('startup_script', '')
        shutdown_script = request.form.get('shutdown_script', '')
        custom_config = request.form.get('custom_config', '')
        status = request.form.get('status', 'Активна')
        notes = request.form.get('notes', '')
        
        # Валидация
        if not name:
            flash('Название конфигурации обязательно', 'error')
            return render_template('wtware/add_wtware.html')
        
        db = get_db()
        try:
            db.execute('''
                INSERT INTO wtware_configs 
                (name, version, server_ip, server_port, screen_width, screen_height,
                 auto_start, network_drive, printer_config, startup_script,
                 shutdown_script, custom_config, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                name, version, server_ip, server_port, screen_width, screen_height,
                auto_start, network_drive, printer_config, startup_script,
                shutdown_script, custom_config, status, notes
            ))
            db.commit()
            flash('Конфигурация WTware успешно добавлена!', 'success')
            return redirect(url_for('wtware_list'))
        except Exception as e:
            flash(f'Ошибка при добавлении конфигурации: {str(e)}', 'error')
    
    return render_template('wtware/add_wtware.html')

@bluprint_wtware_routes.route('/edit_wtware/<int:config_id>', methods=['GET', 'POST'])
def edit_wtware(config_id):
    db = get_db()
    
    wtware_config = db.execute('SELECT * FROM wtware_configs WHERE id=?', (config_id,)).fetchone()
    if not wtware_config:
        flash('Конфигурация не найдена', 'error')
        return redirect(url_for('wtware_list'))
    
    if request.method == 'POST':
        name = request.form['name']
        version = request.form.get('version', '')
        server_ip = request.form.get('server_ip', '')
        server_port = request.form.get('server_port', 80)
        screen_width = request.form.get('screen_width', 1024)
        screen_height = request.form.get('screen_height', 768)
        auto_start = request.form.get('auto_start', '')
        network_drive = request.form.get('network_drive', '')
        printer_config = request.form.get('printer_config', '')
        startup_script = request.form.get('startup_script', '')
        shutdown_script = request.form.get('shutdown_script', '')
        custom_config = request.form.get('custom_config', '')
        status = request.form.get('status', 'Активна')
        notes = request.form.get('notes', '')
        
        # Валидация
        if not name:
            flash('Название конфигурации обязательно', 'error')
            return render_template('wtware/edit_wtware.html', config=config)
        
        try:
            db.execute('''
                UPDATE wtware_configs SET 
                name=?, version=?, server_ip=?, server_port=?, screen_width=?, screen_height=?,
                auto_start=?, network_drive=?, printer_config=?, startup_script=?,
                shutdown_script=?, custom_config=?, status=?, notes=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (
                name, version, server_ip, server_port, screen_width, screen_height,
                auto_start, network_drive, printer_config, startup_script,
                shutdown_script, custom_config, status, notes, config_id
            ))
            db.commit()
            flash('Конфигурация WTware успешно обновлена!', 'success')
            return redirect(url_for('wtware_list'))
        
        except Exception as e:
            flash(f'Ошибка при обновлении конфигурации: {str(e)}', 'error')
    

    return render_template('wtware/edit_wtware.html', wtware_config=wtware_config)
    
 
@bluprint_wtware_routes.route('/delete_wtware/<int:config_id>')
def delete_wtware(config_id):
    db = get_db()
    try:
        db.execute('DELETE FROM wtware_configs WHERE id=?', (config_id,))
        db.commit()
        flash('Конфигурация WTware успешно удалена!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении конфигурации: {str(e)}', 'error')
    
    return redirect(url_for('wtware_list'))

@bluprint_wtware_routes.route('/wtware_search')
def wtware_search():
    query = request.args.get('q', '')
    db = get_db()
    
    configs = db.execute('''
        SELECT * FROM wtware_configs 
        WHERE name LIKE ? OR server_ip LIKE ? OR version LIKE ? OR notes LIKE ?
        ORDER BY name, created_at DESC
    ''', (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%')).fetchall()
    
    return render_template('wtware/wtware_list.html', configs=configs, search_query=query)

# Экспорт WTware в Excel
@bluprint_wtware_routes.route('/export/wtware')
def export_wtware():
    """Экспорт конфигураций WTware в Excel"""
    try:
        excel_file = export_to_excel('wtware_configs', [
            'name', 'version', 'server_ip', 'server_port', 'screen_width', 
            'screen_height', 'auto_start', 'network_drive', 'printer_config',
            'startup_script', 'shutdown_script', 'status', 'notes'
        ])
        filename = f'wtware_export_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
        
        return send_file(
            excel_file,
            download_name=filename,
            as_attachment=True,
            mimetype='bluprint_wtware_routeslication/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        flash(f'Ошибка при экспорте данных: {str(e)}', 'error')
        return redirect(url_for('wtware_list'))

@bluprint_wtware_routes.route('/import/wtware', methods=['GET', 'POST'])
def import_wtware():
    """Импорт конфигураций WTware из Excel"""
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
            success, message = import_from_excel(file, 'wtware_configs')
            
            if success:
                flash(message, 'success')
            else:
                flash(message, 'error')
                
            return redirect(url_for('wtware_list'))
            
        except Exception as e:
            flash(f'Ошибка при импорте данных: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('wtware/import_wtware.html')

# ========== МАРШРУТЫ ДЛЯ УДАЛЕННОГО УПРАВЛЕНИЯ WTWARE ==========

@bluprint_wtware_routes.route('/wtware_connect/<int:config_id>', methods=['GET', 'POST'])
def wtware_connect(config_id):
    """Подключение к устройству WTware"""
    db = get_db()
    wtware_config = db.execute('SELECT * FROM wtware_configs WHERE id=?', (config_id,)).fetchone()
    
    if not wtware_config:
        flash('Конфигурация не найдена', 'error')
        return redirect(url_for('wtware_list'))
    
    connection_status = None
    system_info = {}
    
    if request.method == 'POST':
        device_ip = request.form.get('device_ip')
        port = request.form.get('port', '80')  # Получаем как строку
        
        if not device_ip:
            flash('IP адрес устройства обязателен', 'error')
        else:
            try:
                # Преобразуем порт в int
                port_int = int(port)
                
                # Тестируем подключение (без пароля, как и требуется)
                success, message, info = test_wtware_connection(device_ip, port_int)
                connection_status = {
                    'success': success,
                    'message': message
                }
                system_info = info
                
                if success:
                    flash('Успешное подключение к устройству WTware!', 'success')
                else:
                    flash(f'Ошибка подключения: {message}', 'error')
                    
            except ValueError:
                flash('Порт должен быть числом', 'error')
            except Exception as e:
                flash(f'Ошибка подключения: {str(e)}', 'error')
    
    return render_template('wtware/wtware_connect.html', 
                         wtware_config=wtware_config, 
                         connection_status=connection_status,
                         system_info=system_info)

@bluprint_wtware_routes.route('/wtware_deploy_config/<int:config_id>', methods=['POST'])
def wtware_deploy_config(config_id):
    """Развертывание конфигурации на устройстве WTware"""
    db = get_db()
    wtware_config = db.execute('SELECT * FROM wtware_configs WHERE id=?', (config_id,)).fetchone()
    
    if not wtware_config:
        flash('Конфигурация не найдена', 'error')
        return redirect(url_for('wtware_list'))
    
    device_ip = request.form.get('device_ip')
    port = request.form.get('port', '80')
    
    if not device_ip:
        flash('IP адрес устройства обязателен', 'error')
        return redirect(url_for('wtware_connect', config_id=config_id))
    
    try:
        # Преобразуем порт в int
        port_int = int(port)
        
        # Генерируем конфигурационный файл
        config_dict = dict(wtware_config)
        config_content = generate_wtware_config(config_dict)
        
        # Загружаем конфигурацию на устройство
        success, message = upload_config_to_wtware(device_ip, config_content, port_int)
        
        if success:
            flash(f'Конфигурация успешно развернута на устройстве {device_ip}!', 'success')
            
            # Сохраняем информацию о развертывании
            db.execute('''
                INSERT INTO wtware_deployments (config_id, device_ip, status, deployed_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (config_id, device_ip, 'success'))
            db.commit()
        else:
            flash(f'Ошибка развертывания: {message}', 'error')
            
            db.execute('''
                INSERT INTO wtware_deployments (config_id, device_ip, status, error_message, deployed_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (config_id, device_ip, 'error', message))
            db.commit()
        
    except ValueError:
        flash('Порт должен быть числом', 'error')
    except Exception as e:
        flash(f'Ошибка при развертывании: {str(e)}', 'error')
    
    return redirect(url_for('wtware_connect', config_id=config_id))

@bluprint_wtware_routes.route('/wtware_restart_service/<int:config_id>', methods=['POST'])
def wtware_restart_service(config_id):
    """Перезапуск устройства WTware"""
    db = get_db()
    wtware_config = db.execute('SELECT * FROM wtware_configs WHERE id=?', (config_id,)).fetchone()
    
    if not wtware_config:
        flash('Конфигурация не найдена', 'error')
        return redirect(url_for('wtware_list'))
    
    device_ip = request.form.get('device_ip')
    port = request.form.get('port', '80')
    
    if not device_ip:
        flash('IP адрес устройства обязателен', 'error')
        return redirect(url_for('wtware_connect', config_id=config_id))
    
    client = WTwareClient()
    
    try:
        # Преобразуем порт в int
        port_int = int(port)
        
        # Подключаемся к устройству
        if not client.connect(device_ip, port_int):
            flash('Не удалось подключиться к устройству', 'error')
            return redirect(url_for('wtware_connect', config_id=config_id))
        
        # Перезапускаем устройство
        success, message = client.reboot_device()
        
        if success:
            flash(f'Устройство WTware {device_ip} перезапускается!', 'success')
        else:
            flash(f'Ошибка перезапуска: {message}', 'error')
        
    except ValueError:
        flash('Порт должен быть числом', 'error')
    except Exception as e:
        flash(f'Ошибка при перезапуске: {str(e)}', 'error')
    finally:
        client.disconnect()
    
    return redirect(url_for('wtware_connect', config_id=config_id))

@bluprint_wtware_routes.route('/wtware_get_current_config/<int:config_id>', methods=['POST'])
def wtware_get_current_config(config_id):
    """Получение текущей конфигурации с устройства"""
    db = get_db()
    wtware_config = db.execute('SELECT * FROM wtware_configs WHERE id=?', (config_id,)).fetchone()
    
    if not wtware_config:
        flash('Конфигурация не найдена', 'error')
        return redirect(url_for('wtware_list'))
    
    device_ip = request.form.get('device_ip')
    username = request.form.get('username', 'root')
    password = request.form.get('password')
    port = request.form.get('port', 22)
    
    if not device_ip or not password:
        flash('IP адрес устройства и пароль обязательны', 'error')
        return redirect(url_for('wtware_connect', config_id=config_id))
    
    client = WTwareSSHClient()
    
    try:
        # Подключаемся к устройству
        if not client.connect(device_ip, username, password, port):
            flash('Не удалось подключиться к устройству', 'error')
            return redirect(url_for('wtware_connect', config_id=config_id))
        
        # Скачиваем текущую конфигурацию
        success, current_config = client.download_config()
        
        if success:
            # Показываем текущую конфигурацию
            return render_template('wtware/wtware_current_config.html',
                                wtware_config=wtware_config,
                                current_config=current_config,
                                device_ip=device_ip)
        else:
            flash(f'Ошибка получения конфигурации: {current_config}', 'error')
        
    except Exception as e:
        flash(f'Ошибка при получении конфигурации: {str(e)}', 'error')
    finally:
        client.disconnect()
    
    return redirect(url_for('wtware_connect', config_id=config_id))



# Добавим маршрут для скачивания конфигурационного файла
@bluprint_wtware_routes.route('/download_wtware_config/<int:config_id>')
def download_wtware_config(config_id):
    """Скачивание конфигурационного файла WTware"""
    db = get_db()
    wtware_config = db.execute('SELECT * FROM wtware_configs WHERE id=?', (config_id,)).fetchone()
    
    if not wtware_config:
        flash('Конфигурация не найдена', 'error')
        return redirect(url_for('wtware_list'))
    
    # Генерируем конфигурационный файл
    config_dict = dict(wtware_config)
    config_content = generate_wtware_config(config_dict)
    
    # Создаем ответ для скачивания файла
    from flask import Response
    response = Response(
        config_content,
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment;filename=wtware_config_{wtware_config['name']}.conf"}
    )
    
    return response

@bluprint_wtware_routes.route('/wtware_deployments')

def wtware_deployments():
    """История развертываний конфигураций"""
    db = get_db()
    
    deployments = db.execute('''
        SELECT d.*, w.name as config_name 
        FROM wtware_deployments d 
        JOIN wtware_configs w ON d.config_id = w.id 
        ORDER BY d.deployed_at DESC
        LIMIT 50
    ''').fetchall()
    
    return render_template('wtware/wtware_deployments.html', deployments=deployments)

@bluprint_wtware_routes.route('/scripts')
def scripts_list():
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

# ========== УТИЛИТЫ ДЛЯ СКРИПТОВ ==========

def execute_script(script_content, script_type='bat'):
    """
    Выполняет скрипт и возвращает результат
    """
    try:
        # Создаем временный файл для скрипта
        with tempfile.NamedTemporaryFile(mode='w', 
                                       suffix=f'.{script_type}', 
                                       delete=False,
                                       encoding='utf-8') as temp_file:
            temp_file.write(script_content)
            temp_file.flush()
            temp_path = temp_file.name
        
        # Выполняем скрипт
        start_time = time.time()
        
        if script_type == 'bat':
            result = subprocess.run(
                ['cmd', '/c', temp_path],
                capture_output=True,
                text=True,
                timeout=300,  # 5 минут таймаут
                encoding='cp866'  # Кодировка для русских символов в Windows
            )
        elif script_type == 'ps1':
            result = subprocess.run(
                ['powershell', '-ExecutionPolicy', 'Bypass', '-File', temp_path],
                capture_output=True,
                text=True,
                timeout=300,
                encoding='cp866'
            )
        else:
            raise ValueError(f"Unsupported script type: {script_type}")
        
        execution_time = time.time() - start_time
        
        # Очищаем временный файл
        try:
            os.unlink(temp_path)
        except:
            pass
        
        # Определяем успешность выполнения
        success = result.returncode == 0
        
        return {
            'success': success,
            'output': result.stdout,
            'error': result.stderr,
            'return_code': result.returncode,
            'execution_time': execution_time
        }
        
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'output': '',
            'error': 'Script execution timeout (5 minutes)',
            'return_code': -1,
            'execution_time': 300
        }
    except Exception as e:
        return {
            'success': False,
            'output': '',
            'error': str(e),
            'return_code': -1,
            'execution_time': 0
        }

def save_script_result(db, script_id, result):
    """
    Сохраняет результат выполнения скрипта в базу данных
    """
    db.execute('''
        INSERT INTO script_results 
        (script_id, output, success, error_message, execution_time)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        script_id,
        result['output'],
        result['success'],
        result['error'],
        result['execution_time']
    ))
    db.commit()

def get_script_results(db, script_id, limit=10):
    """
    Получает историю выполнения скрипта
    """
    return db.execute('''
        SELECT * FROM script_results 
        WHERE script_id = ? 
        ORDER BY executed_at DESC 
        LIMIT ?
    ''', (script_id, limit)).fetchall()



