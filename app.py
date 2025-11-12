from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from templates.base.database import init_db, get_db
from werkzeug.security import generate_password_hash, check_password_hash


import socket
import os
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

from functools import wraps
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


# ========== ЗАПУСК ПРИЛОЖЕНИЯ С СЕТЕВЫМ ДОСТУПОМ ==========

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
    
    # Запускаем сервер с доступом из локальной сети
    app.run(
        debug=True, 
        host='0.0.0.0',  # Доступ со всех интерфейсов
        port=8000,       # Порт (можно изменить при необходимости)
        threaded=True    # Для обработки нескольких запросов одновременно
    )