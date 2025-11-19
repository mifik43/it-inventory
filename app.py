from flask import Flask, render_template, request, redirect, url_for, flash, send_file, Response
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
from templates.network_scan.network_scanner import bluprint_network_scan_routes
from templates.wtware.wtware import bluprint_wtware_routes
from templates.scripts.script import bluprint_script_routes

from templates.base.requirements import admin_required, login_required

from excel_utils import (
    export_any_type_to_exel, import_from_excel
)

from templates.guest_wifi.wifi_utils import (
    export_guest_wifi_to_excel, 
    import_guest_wifi_from_excel,
    download_wifi_template
)

from wtware_client import WTwareClient, generate_wtware_config, test_wtware_connection, upload_config_to_wtware

from script_utils import execute_script, save_script_result, get_script_results

from network_scanner import NetworkScanner

from templates.base.navigation import create_main_menu
# Глобальный объект сканера


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
app.register_blueprint(bluprint_network_scan_routes)
app.register_blueprint(bluprint_wtware_routes)
app.register_blueprint(bluprint_script_routes)


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

@app.context_processor
def inject_common_variables():
    return {
        'menu': create_main_menu()
    }

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
        filename, excel_file = export_any_type_to_exel(data_type)
        
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
            success, message = import_from_excel(file, data_type)
            
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