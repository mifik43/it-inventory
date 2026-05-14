from flask import Flask, render_template, request, redirect, url_for, flash, send_file, Response
from config import config
from logger import setup_logger
from templates.base.database_helper import db, init_db, get_db

#from templates.social.scheduler import SocialScheduler

import socket
from datetime import datetime, timedelta
from sqlalchemy import func

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
from templates.social.social_routes import bluprint_social_routes
from templates.base.requirements import login_required, get_current_user
from templates.checklist.checklist import bluprint_checklist_routes

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

from templates.social.scheduler import SocialScheduler

# Импортируем модели
from models import (
    User, Device, Provider, SoftwareCube, Organization, Todo, 
    Shift, Article, Note, GuestWifi, Log, SocialPost, Script
)

app = Flask(__name__)
app.config.from_object(config)

# Инициализация логирования
logger = setup_logger(app)

social_scheduler = SocialScheduler(app)
# Глобальный объект сканера

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
app.register_blueprint(bluprint_social_routes)
app.register_blueprint(bluprint_checklist_routes)

# Инициализация БД при запуске приложения
with app.app_context():
    db.init_app(app)
    db.create_all()
    init_db(app)
    
    from templates.checklist.checklist import init_checklist_db, import_initial_checklist_data
    init_checklist_db()
    import_initial_checklist_data()

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

    if get_current_user() is None:
        logger.info("Перенаправляем на страницу входа")
        return render_template('auth/login.html')

    # Основная статистика
    devices_count = Device.query.count()
    active_providers_count = Provider.query.filter_by(status="Активен").count()
    total_monthly_cost = db.session.query(func.sum(Provider.price)).filter_by(status="Активен").scalar() or 0
    users_count = User.query.count()

    # Статистика по статьям и заметкам
    articles_count = Article.query.filter_by(is_published=True).count()
    notes_count = Note.query.count()
    
    # Ближайшие смены (на сегодня и завтра)
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    
    upcoming_shifts = db.session.query(Shift, User).join(User).filter(
        Shift.shift_date.between(today, tomorrow)
    ).order_by(Shift.shift_date, Shift.shift_type).limit(10).all()

    # Статистика по устройствам
    devices_by_type = db.session.query(
        Device.type, func.count(Device.id).label('count')
    ).group_by(Device.type).order_by(func.count(Device.id).desc()).all()
    
    devices_by_status = db.session.query(
        Device.status, func.count(Device.id).label('count')
    ).group_by(Device.status).order_by(func.count(Device.id).desc()).all()
    
    # Последние добавленные устройства
    recent_devices = Device.query.order_by(Device.created_at.desc()).limit(5).all()
    
    # Активные провайдеры
    active_providers = Provider.query.filter_by(status="Активен").order_by(Provider.created_at.desc()).limit(5).all()
    
    # Статистика по провайдерам по городам
    providers_by_city = db.session.query(
        Provider.city, func.count(Provider.id).label('count')
    ).group_by(Provider.city).order_by(func.count(Provider.id).desc()).all()
    
    # Стоимость по типам услуг
    cost_by_service = db.session.query(
        Provider.service_type, func.sum(Provider.price).label('total_cost')
    ).filter_by(status="Активен").group_by(Provider.service_type).order_by(func.sum(Provider.price).desc()).all()

    cubes_list = get_cubes()

    total_cubes_price = 0
    for c in cubes_list:
        total_cubes_price += c['price']

    current_user = get_current_user()
    
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
                        current_user=current_user
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
    
    simple_data_type = data_type.split('.')[0] if '.' in data_type else data_type
    
    return render_template('excel/import.html', 
                         data_type=data_type,
                         simple_data_type=simple_data_type,  
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
    social_scheduler.start()
    
    # Запускаем сервер с доступом из локальной сети
    try:
        app.run(
            debug=True, 
            host='0.0.0.0',  # Доступ со всех интерфейсов
            port=8000,       # Порт (можно изменить при необходимости)
            threaded=True    # Для обработки нескольких запросов одновременно
        )
    except KeyboardInterrupt:
        logger.info("Остановка сервера...")
        social_scheduler.stop()
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        social_scheduler.stop()