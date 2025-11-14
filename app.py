from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, Response, jsonify
from templates.base.database import init_db, get_db


import socket
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
from templates.todo.todo import bluprint_todo_routes
from templates.shifts.shifts import bluprint_shifts_routes

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

from wtware_client import WTwareClient, generate_wtware_config, test_wtware_connection, upload_config_to_wtware

from script_utils import execute_script, save_script_result, get_script_results

from network_scanner import NetworkScanner
# Глобальный объект сканера
network_scanner = NetworkScanner()

#from telegram_utils import (
#    save_telegram_request, get_telegram_requests, update_request_status,
#    assign_request, add_response, get_request_stats, TelegramBot
#)

# Конфигурация Telegram бота
#TELEGRAM_BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'  # Заменить на реальный токен
#TELEGRAM_WEBHOOK_URL = 'https://your-domain.com/webhook/telegram'  # Заменить на реальный URL

# Инициализация бота
#telegram_bot = TelegramBot(token=TELEGRAM_BOT_TOKEN, webhook_url=TELEGRAM_WEBHOOK_URL)

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
app.register_blueprint(bluprint_todo_routes)
app.register_blueprint(bluprint_shifts_routes)



# Инициализация БД при запуске приложения
with app.app_context():
    init_db()

# ========== ОСНОВНЫЕ МАРШРУТЫ ==========



@app.context_processor
def utility_processor():
    def generate_wtware_config(wtware_config):
        from wtware_ssh import generate_wtware_config as gen_config
        return gen_config(dict(wtware_config))
    return dict(generate_wtware_config=generate_wtware_config)

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

    # Статистика по Telegram заявкам
    #telegram_stats = get_request_stats()
    #new_requests_count = telegram_stats.get('new_count', 0)
    #total_requests_count = telegram_stats.get('total', 0)

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
                        #telegram_stats=telegram_stats,
                        #new_requests_count=new_requests_count,
                        #total_requests_count=total_requests_count
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



# ========== МАРШРУТЫ ДЛЯ WTWARE ==========

@app.route('/wtware')
@login_required
def wtware_list():
    db = get_db()
    configs = db.execute('''
        SELECT * FROM wtware_configs 
        ORDER BY name, created_at DESC
    ''').fetchall()
    return render_template('wtware/wtware_list.html', configs=configs)

@app.route('/add_wtware', methods=['GET', 'POST'])
@admin_required
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

@app.route('/edit_wtware/<int:config_id>', methods=['GET', 'POST'])
@admin_required
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
    
 
@app.route('/delete_wtware/<int:config_id>')
@admin_required
def delete_wtware(config_id):
    db = get_db()
    try:
        db.execute('DELETE FROM wtware_configs WHERE id=?', (config_id,))
        db.commit()
        flash('Конфигурация WTware успешно удалена!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении конфигурации: {str(e)}', 'error')
    
    return redirect(url_for('wtware_list'))

@app.route('/wtware_search')
@login_required
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
@app.route('/export/wtware')
@login_required
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
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        flash(f'Ошибка при экспорте данных: {str(e)}', 'error')
        return redirect(url_for('wtware_list'))

@app.route('/import/wtware', methods=['GET', 'POST'])
@admin_required
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

@app.route('/wtware_connect/<int:config_id>', methods=['GET', 'POST'])
@admin_required
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

@app.route('/wtware_deploy_config/<int:config_id>', methods=['POST'])
@admin_required
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

@app.route('/wtware_restart_service/<int:config_id>', methods=['POST'])
@admin_required
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

@app.route('/wtware_get_current_config/<int:config_id>', methods=['POST'])
@admin_required
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
@app.route('/download_wtware_config/<int:config_id>')
@admin_required
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

@app.route('/wtware_deployments')
@admin_required
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

@app.route('/scripts')
@login_required
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



# ========== МАРШРУТЫ ДЛЯ СКРИПТОВ ==========

@app.route('/scripts')
@login_required
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

@app.route('/add_script', methods=['GET', 'POST'])
@admin_required
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
            return redirect(url_for('script_list'))  # Обновили ссылку
        except Exception as e:
            flash(f'Ошибка при добавлении скрипта: {str(e)}', 'error')
    
    return render_template('scripts/add_script.html')

@app.route('/edit_script/<int:script_id>', methods=['GET', 'POST'])
@admin_required
def script_edit(script_id):  # Изменили имя с edit_script на script_edit
    """Редактирование скрипта"""
    db = get_db()
    script = db.execute('SELECT * FROM scripts WHERE id = ?', (script_id,)).fetchone()
    
    if not script:
        flash('Скрипт не найден', 'error')
        return redirect(url_for('script_list'))  # Обновили ссылку
    
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
            return redirect(url_for('script_list'))  # Обновили ссылку
        except Exception as e:
            flash(f'Ошибка при обновлении скрипта: {str(e)}', 'error')
    
    return render_template('scripts/edit_script.html', script=script)

@app.route('/delete_script/<int:script_id>')
@admin_required
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
    
    return redirect(url_for('script_list'))  # Обновили ссылку

@app.route('/run_script/<int:script_id>')
@admin_required
def script_run(script_id):  # Изменили имя с run_script на script_run
    """Выполнение скрипта"""
    db = get_db()
    script = db.execute('SELECT * FROM scripts WHERE id = ?', (script_id,)).fetchone()
    
    if not script:
        flash('Скрипт не найден', 'error')
        return redirect(url_for('script_list'))  # Обновили ссылку
    
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

@app.route('/view_script_results/<int:script_id>')
@login_required
def script_results(script_id):  # Обратите внимание на имя функции
    """Просмотр истории выполнения скрипта"""
    db = get_db()
    script = db.execute('SELECT * FROM scripts WHERE id = ?', (script_id,)).fetchone()
    
    if not script:
        flash('Скрипт не найден', 'error')
        return redirect(url_for('script_list'))
    
    results = get_script_results(db, script_id, 20)
    
    return render_template('scripts/script_results.html', 
                         script=script, 
                         results=results)

@app.route('/view_script/<int:script_id>')
@login_required
def script_view(script_id):  # Изменили имя с view_script на script_view
    """Просмотр содержимого скрипта"""
    db = get_db()
    script = db.execute('SELECT * FROM scripts WHERE id = ?', (script_id,)).fetchone()
    
    if not script:
        flash('Скрипт не найден', 'error')
        return redirect(url_for('script_list'))  # Обновили ссылку
    
    return render_template('scripts/view_script.html', script=script)

@app.route('/download_script/<int:script_id>')
@login_required
def script_download(script_id):  # Изменили имя с download_script на script_download
    """Скачивание скрипта"""
    db = get_db()
    script = db.execute('SELECT * FROM scripts WHERE id = ?', (script_id,)).fetchone()
    
    if not script:
        flash('Скрипт не найден', 'error')
        return redirect(url_for('script_list'))  # Обновили ссылку
    
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

# ========== МАРШРУТЫ ДЛЯ СКАНИРОВАНИЯ СЕТИ ==========

@app.route('/network_scan')
@login_required
def network_scan():
    """Главная страница сканирования сети"""
    db = get_db()
    
    # Получаем последние сканирования
    scans = db.execute('''
        SELECT * FROM network_scans 
        ORDER BY created_at DESC 
        LIMIT 10
    ''').fetchall()
    
    return render_template('network_scan/network_scan.html', scans=scans)

@app.route('/network_scan/start', methods=['POST'])
@admin_required
def start_network_scan():
    """Запуск сканирования сети"""
    scan_type = request.form['scan_type']
    target_range = request.form['target_range']
    scan_name = request.form.get('scan_name', f'Scan {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    
    # Валидация target_range для ping сканирования
    if scan_type == 'ping':
        try:
            ipaddress.ip_network(target_range, strict=False)
        except:
            flash('Неверный формат сетевого диапазона. Пример: 192.168.1.0/24', 'error')
            return redirect(url_for('network_scan'))
    
    db = get_db()
    
    try:
        # Создаем запись о сканировании
        scan_id = db.execute('''
            INSERT INTO network_scans (name, scan_type, target_range, status)
            VALUES (?, ?, ?, ?)
        ''', (scan_name, scan_type, target_range, 'running')).lastrowid
        db.commit()
        
        # Запускаем сканирование в отдельном потоке
        import threading
        scan_thread = threading.Thread(
            target=run_network_scan_background,
            args=(scan_id, scan_type, target_range)
        )
        scan_thread.daemon = True
        scan_thread.start()
        
        flash('Сканирование сети запущено!', 'success')
        
    except Exception as e:
        flash(f'Ошибка при запуске сканирования: {str(e)}', 'error')
    
    return redirect(url_for('network_scan'))

def run_network_scan_background(scan_id, scan_type, target_range):
    """Фоновая задача сканирования сети"""
    with app.app_context():
        db = get_db()
        try:
            # Запускаем сканирование
            devices = network_scanner.start_scan(scan_type, target_range)
            
            # Сохраняем найденные устройства
            for device in devices:
                db.execute('''
                    INSERT INTO network_devices 
                    (scan_id, ip_address, mac_address, hostname, vendor, os_info, ports, response_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    scan_id,
                    device['ip_address'],
                    device.get('mac_address', 'Unknown'),
                    device.get('hostname', 'Unknown'),
                    device.get('vendor', 'Unknown'),
                    device.get('os_info', 'Unknown'),
                    json.dumps(device.get('ports', [])),
                    device.get('response_time', 0)
                ))
            
            # Обновляем статус сканирования
            db.execute('''
                UPDATE network_scans 
                SET status = 'completed', 
                    devices_found = ?,
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (len(devices), scan_id))
            db.commit()
            
        except Exception as e:
            # В случае ошибки обновляем статус
            db.execute('''
                UPDATE network_scans 
                SET status = 'failed',
                    notes = ?
                WHERE id = ?
            ''', (str(e), scan_id))
            db.commit()

@app.route('/network_scan/<int:scan_id>')
@login_required
def network_scan_results(scan_id):
    """Результаты сканирования"""
    db = get_db()
    
    scan = db.execute('SELECT * FROM network_scans WHERE id = ?', (scan_id,)).fetchone()
    devices = db.execute('''
        SELECT * FROM network_devices 
        WHERE scan_id = ? 
        ORDER BY ip_address
    ''', (scan_id,)).fetchall()
    
    # Парсим JSON для портов
    processed_devices = []
    for device in devices:
        device_dict = dict(device)
        if device_dict['ports']:
            try:
                device_dict['ports'] = json.loads(device_dict['ports'])
            except:
                device_dict['ports'] = []
        processed_devices.append(device_dict)
    
    return render_template('network_scan/scan_results.html', 
                         scan=scan, 
                         devices=processed_devices)

@app.route('/network_scan/progress')
@login_required
def network_scan_progress():
    """Получение прогресса сканирования"""
    return jsonify({
        'is_scanning': network_scanner.is_scanning,
        'progress': network_scanner.scan_progress
    })

@app.route('/network_scan/stop', methods=['POST'])
@admin_required
def stop_network_scan():
    """Остановка сканирования"""
    network_scanner.is_scanning = False
    flash('Сканирование остановлено', 'info')
    return redirect(url_for('network_scan'))

@app.route('/network_devices')
@login_required
def network_devices():
    """Список всех обнаруженных устройств"""
    db = get_db()
    
    devices = db.execute('''
        SELECT nd.*, ns.name as scan_name, ns.created_at as scan_date
        FROM network_devices nd
        JOIN network_scans ns ON nd.scan_id = ns.id
        ORDER BY nd.last_seen DESC
    ''').fetchall()
    
    # Обрабатываем порты
    processed_devices = []
    for device in devices:
        device_dict = dict(device)
        if device_dict['ports']:
            try:
                device_dict['ports'] = json.loads(device_dict['ports'])
            except:
                device_dict['ports'] = []
        processed_devices.append(device_dict)
    
    return render_template('network_scan/devices_list.html', devices=processed_devices)

@app.route('/network_scan/ping/<ip>')
@login_required
def ping_device(ip):
    """Пинг устройства"""
    try:
        import platform
        param = "-n 1 -w 1000" if platform.system().lower() == "windows" else "-c 1 -W 1"
        result = subprocess.run(
            f"ping {param} {ip}", 
            capture_output=True, 
            shell=True
        )
        
        success = result.returncode == 0
        return jsonify({
            'success': success,
            'ip': ip,
            'response_time': 10.5 if success else 0,  # В реальности нужно парсить вывод
            'error': '' if success else 'Устройство не отвечает'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/network_scan/device_info/<int:device_id>')
@login_required
def device_info(device_id):
    """Информация об устройстве"""
    db = get_db()
    device = db.execute('''
        SELECT nd.*, ns.name as scan_name 
        FROM network_devices nd
        JOIN network_scans ns ON nd.scan_id = ns.id
        WHERE nd.id = ?
    ''', (device_id,)).fetchone()
    
    if device:
        device_dict = dict(device)
        if device_dict['ports']:
            try:
                device_dict['ports'] = json.loads(device_dict['ports'])
            except:
                device_dict['ports'] = []
        return jsonify({'success': True, 'device': device_dict})
    else:
        return jsonify({'success': False, 'error': 'Устройство не найдено'})



# Вспомогательная функция для шаблонов
@app.context_processor
def utility_processor():
    def get_port_service(port):
        port_services = {
            21: 'FTP', 22: 'SSH', 23: 'Telnet', 25: 'SMTP', 53: 'DNS',
            80: 'HTTP', 110: 'POP3', 143: 'IMAP', 443: 'HTTPS', 993: 'IMAPS',
            995: 'POP3S', 1433: 'MSSQL', 1521: 'Oracle', 3306: 'MySQL',
            3389: 'RDP', 5432: 'PostgreSQL', 5900: 'VNC', 8080: 'HTTP-Alt'
        }
        return port_services.get(port, 'Unknown')
    return dict(get_port_service=get_port_service)

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
    with app.app_context():
        print("Зарегистрированные маршруты:")
        for rule in app.url_map.iter_rules():
            print(f"{rule.endpoint}: {rule.rule}")

    # Запускаем сервер с доступом из локальной сети
    app.run(
        debug=True, 
        host='0.0.0.0',  # Доступ со всех интерфейсов
        port=8000,       # Порт (можно изменить при необходимости)
        threaded=True    # Для обработки нескольких запросов одновременно
    )