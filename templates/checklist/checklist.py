from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from templates.base.requirements import login_required
from templates.base.database import get_db
import json
from datetime import datetime

from sqlalchemy import text

bluprint_checklist_routes = Blueprint('checklist', __name__, template_folder='templates')

# Инициализация таблицы в БД
def init_checklist_db():
    db = get_db()
    
    # Создаем таблицу для чек-листа
    db.execute(text('''
        CREATE TABLE IF NOT EXISTS checklist_tasks (
            id INTEGER PRIMARY KEY,
            task_number TEXT,
            stage TEXT NOT NULL,
            task_description TEXT NOT NULL,
            category TEXT,
            comment TEXT,
            status TEXT DEFAULT 'Не начато',
            planned_date DATE,
            actual_date DATE,
            responsible TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    '''))
    
    # Создаем таблицу для истории изменений
    db.execute(text('''
        CREATE TABLE IF NOT EXISTS checklist_history (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            task_id INTEGER,
            changed_field TEXT,
            old_value TEXT,
            new_value TEXT,
            changed_by TEXT,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES checklist_tasks (id)
        )
    '''))
    
    db.commit()

# Импорт начальных данных из таблицы
def import_initial_checklist_data():
    db = get_db()
    
    # Проверяем, есть ли уже данные
    existing = db.execute(text('SELECT COUNT(*) as count FROM checklist_tasks')).fetchone().count
    
    if existing > 0:
        return  # Данные уже импортированы
    
    # Данные из предоставленной таблицы
    checklist_data = [
        # Договора/подрядчик/закупки
        {"stage": "Договора/подрядчик/закупки", "task": "Интернет", "task_number": "1", "description": "Сбор данных о провайдерах в ТЦ", "comment": "Можно узнать напрямую в ТЦ список провайдеров, которые к ним заходят", "status": "Выполнено"},
        {"stage": "Договора/подрядчик/закупки", "task": "Интернет", "task_number": "1.1", "description": "Запрос КП от провайдеров - формирование сравнительной таблицы", "comment": "Сравнительная таблица на случай обоснования выбора (скорость, сумма)", "status": "Выполнено"},
        {"stage": "Договора/подрядчик/закупки", "task": "Интернет", "task_number": "1.2", "description": "Подпись договора на подключение к сети", "comment": "", "status": "Выполнено"},
        {"stage": "Договора/подрядчик/закупки", "task": "Интернет", "task_number": "1.3", "description": "Получение данных о подключении (адресация)", "comment": "Данные заносим в Passwork", "status": "Выполнено"},
        {"stage": "Договора/подрядчик/закупки", "task": "Интернет", "task_number": "1.4", "description": "Внесение данных в общую таблицу по провайдерам на объектах", "comment": "", "status": "В работе"},
        {"stage": "Договора/подрядчик/закупки", "task": "Интернет", "task_number": "1.5", "description": "Контроль подключения на объекте", "comment": "Вывод кабеля в планируемой зоне коммутационного шкафа", "status": "Выполнено"},
        
        {"stage": "Договора/подрядчик/закупки", "task": "Закупка", "task_number": "2", "description": "Запрос плана расстановки видеонаблюдения и звука", "comment": "Запрашиваем у архитекторов (проектировщиков)", "status": "Выполнено"},
        {"stage": "Договора/подрядчик/закупки", "task": "Закупка", "task_number": "2.1", "description": "Формирование первой закупки", "comment": "Коммутационный шкаф, роутер, камеры, видеорегистратор, усилитель, колонки, МФУ", "status": "Выполнено"},
        {"stage": "Договора/подрядчик/закупки", "task": "Закупка", "task_number": "2.2", "description": "Формирование второй закупки", "comment": "Оборудование после определения с подрядчиком", "status": "Выполнено"},
        {"stage": "Договора/подрядчик/закупки", "task": "Закупка", "task_number": "2.3", "description": "Формирование третьей закупки", "comment": "Закупка оборудования для кафе", "status": "Выполнено"},
        
        {"stage": "Договора/подрядчик/закупки", "task": "Подрядчик", "task_number": "3", "description": "Запрос плана по камерам и звуку на новом объекте у проектировщиков", "comment": "", "status": "Выполнено"},
        {"stage": "Договора/подрядчик/закупки", "task": "Подрядчик", "task_number": "3.1", "description": "Запрос в отдел кадров размещения вакансии на hh.ru", "comment": "", "status": "Выполнено"},
        {"stage": "Договора/подрядчик/закупки", "task": "Подрядчик", "task_number": "3.2", "description": "Размещение заданий на яндекс услуги и других тематических сайтов", "comment": "", "status": "Выполнено"},
        {"stage": "Договора/подрядчик/закупки", "task": "Подрядчик", "task_number": "3.3", "description": "Обзвон первых 3-4 крупных компаний по монтажу видеонаблюдения", "comment": "", "status": "Выполнено"},
        {"stage": "Договора/подрядчик/закупки", "task": "Подрядчик", "task_number": "3.4", "description": "Организация посещения подрядчиком объекта для более точной оценки", "comment": "", "status": "Выполнено"},
        {"stage": "Договора/подрядчик/закупки", "task": "Подрядчик", "task_number": "3.5", "description": "Отправка суммы (сметы) на согласование по почте ДА", "comment": "", "status": "Выполнено"},
        {"stage": "Договора/подрядчик/закупки", "task": "Подрядчик", "task_number": "3.6", "description": "Отправка договора на проверку юр. службе", "comment": "", "status": "Выполнено"},
        {"stage": "Договора/подрядчик/закупки", "task": "Подрядчик", "task_number": "3.7", "description": "Подпись договора - обсуждение сроков выхода на монтаж", "comment": "", "status": "Выполнено"},
        
        # Сервисы
        {"stage": "Сервисы", "task": "Сервисы", "task_number": "4", "description": "Подпись договора Кубик Мьюзик Кафе (если есть)", "comment": "Заявляем площадь 100 кв.м", "status": "Выполнено"},
        {"stage": "Сервисы", "task": "Сервисы", "task_number": "4.1", "description": "Подпись договора Кубик Мьюзик РЦ", "comment": "Заявляем площадь 100-150 кв.м", "status": "Выполнено"},
        {"stage": "Сервисы", "task": "Сервисы", "task_number": "4.2", "description": "Запрос и оплата счета лицензии на УРВ", "comment": "При отсутствии резервов ключей в Passwork", "status": "Выполнено"},
        {"stage": "Сервисы", "task": "Сервисы", "task_number": "4.3", "description": "Запрос лицензий RKeeper", "comment": "", "status": "В работе"},
        
        # Честный знак
        {"stage": "Честный знак", "task": "Честный знак", "task_number": "5", "description": "Добавление тарифов (картинка) в Карусели", "comment": "", "status": "Не начато"},
        {"stage": "Честный знак", "task": "Честный знак", "task_number": "5.1", "description": "Добавление файла меню (при наличии кафе) в Карусели", "comment": "", "status": "Не начато"},
        {"stage": "Честный знак", "task": "Честный знак", "task_number": "5.2", "description": "Установка и настройка модуля на кассовых ПК", "comment": "", "status": "Не начато"},
        {"stage": "Честный знак", "task": "Честный знак", "task_number": "5.3", "description": "Настройки площадки в Карусели", "comment": "", "status": "Не начато"},
        
        # Карусель
        {"stage": "Карусель", "task": "Карусель", "task_number": "6", "description": "Создание площадки", "comment": "", "status": "Выполнено"},
        {"stage": "Карусель", "task": "Карусель", "task_number": "6.1", "description": "Настройка площадки", "comment": "", "status": "Выполнено"},
        {"stage": "Карусель", "task": "Карусель", "task_number": "6.2", "description": "Наполнение площадки тарифами", "comment": "", "status": "В работе"},
        {"stage": "Карусель", "task": "Карусель", "task_number": "6.3", "description": "Наполнение площадки товарами/услугами", "comment": "", "status": "Не начато"},
        {"stage": "Карусель", "task": "Карусель", "task_number": "6.4", "description": "Покупка ккм сервера для площадки", "comment": "", "status": "Не начато"},
        {"stage": "Карусель", "task": "Карусель", "task_number": "6.5", "description": "Внесение кассовых настроек", "comment": "", "status": "Не начато"},
        {"stage": "Карусель", "task": "Карусель", "task_number": "6.6", "description": "Внесение настроек интернет эквайринга", "comment": "", "status": "Не начато"},
        {"stage": "Карусель", "task": "Карусель", "task_number": "6.7", "description": "Заполнение расписки, если необходимо", "comment": "", "status": "Не начато"},
        {"stage": "Карусель", "task": "Карусель", "task_number": "6.8", "description": "Выдать доступ к площадке сотрудникам", "comment": "", "status": "Не начато"},
        {"stage": "Карусель", "task": "Карусель", "task_number": "6.9", "description": "Добавить ссылки для сбора отзывов", "comment": "", "status": "Не начато"},
        
        # Монтаж - Сеть
        {"stage": "Монтаж", "task": "Сеть", "task_number": "7", "description": "Монтаж коммутационного шкафа", "comment": "", "status": "В работе"},
        {"stage": "Монтаж", "task": "Сеть", "task_number": "7.1", "description": "Настройка роутера Mikrotik на объекте", "comment": "", "status": "Выполнено"},
        {"stage": "Монтаж", "task": "Сеть", "task_number": "7.2", "description": "Монтаж коммутаторов под локальную сеть и POE", "comment": "", "status": "В работе"},
        {"stage": "Монтаж", "task": "Сеть", "task_number": "7.3", "description": "Монтаж патч панелей", "comment": "", "status": "Не начато"},
        
        # Монтаж - Видеонаблюдение
        {"stage": "Монтаж", "task": "Видеонаблюдение", "task_number": "8", "description": "Монтаж камер видеонаблюдения согласно плана", "comment": "", "status": "В работе"},
        {"stage": "Монтаж", "task": "Видеонаблюдение", "task_number": "8.1", "description": "Монтаж и настройка видеорегистратора", "comment": "", "status": "Выполнено"},
        {"stage": "Монтаж", "task": "Видеонаблюдение", "task_number": "8.2", "description": "Проброс во внешний доступ видеорегистратора", "comment": "", "status": "Не начато"},
        {"stage": "Монтаж", "task": "Видеонаблюдение", "task_number": "8.3", "description": "Настройка доступа к видеонаблюдению", "comment": "", "status": "Не начато"},
        
        # Звуковое сопровождение
        {"stage": "Монтаж", "task": "Звуковое сопровождение", "task_number": "9", "description": "Монтаж звуковых колонок согласно плана", "comment": "", "status": "В работе"},
        {"stage": "Монтаж", "task": "Звуковое сопровождение", "task_number": "9.1", "description": "Монтаж и установка усилителя", "comment": "", "status": "Не начато"},
        {"stage": "Монтаж", "task": "Звуковое сопровождение", "task_number": "9.2", "description": "Подключение Мини-ПК для Cubic Music", "comment": "", "status": "В работе"},
        {"stage": "Монтаж", "task": "Звуковое сопровождение", "task_number": "9.3", "description": "Настройка Мини-ПК, установка CubicMusic", "comment": "", "status": "Не начато"},
        
        # Кассовая зона
        {"stage": "Монтаж", "task": "Кассовая зона", "task_number": "10", "description": "Контроль монтажа кассовой зоны РЦ", "comment": "", "status": "Не начато"},
        {"stage": "Монтаж", "task": "Кассовая зона", "task_number": "10.1", "description": "Контроль установки рабочих мест", "comment": "", "status": "Не начато"},
        {"stage": "Монтаж", "task": "Кассовая зона", "task_number": "10.2", "description": "Настройка кассового сервера", "comment": "", "status": "Не начато"},
        
        # Кассовая зона кафе/бара
        {"stage": "Монтаж", "task": "Кассовая зона кафе/бара", "task_number": "11", "description": "Контроль монтажа бара (кассовой зоны ресторана)", "comment": "", "status": "Не начато"},
        {"stage": "Монтаж", "task": "Кассовая зона кафе/бара", "task_number": "11.1", "description": "Контроль установки рабочих мест", "comment": "", "status": "Не начато"},
    ]
    
    # Вставляем данные
    #for item in checklist_data:
    i = 0
    for item in checklist_data:
        item["id"] = i
        i += 1
        db.execute(text(f'''
            INSERT INTO checklist_tasks (id, task_number, stage, task_description, comment, status)
            VALUES (:id, :task_number, :stage, :description, :comment, :status)
        '''), item)
    
    db.commit()

# Маршруты
@bluprint_checklist_routes.route('/checklist')
@login_required
def checklist():
    """Главная страница чек-листа"""
    db = get_db()
    
    # Получаем все задачи
    tasks = db.execute(text('''
        SELECT * FROM checklist_tasks 
        ORDER BY 
            CASE 
                WHEN stage = 'Договора/подрядчик/закупки' THEN 1
                WHEN stage = 'Сервисы' THEN 2
                WHEN stage = 'Честный знак' THEN 3
                WHEN stage = 'Карусель' THEN 4
                WHEN stage = 'Монтаж' THEN 5
                ELSE 6
            END,
            category,
            task_number
    ''')).fetchall()
    
    # Преобразуем задачи в список словарей для удобства работы в шаблоне
    tasks_list = []
    for task in tasks:
        tasks_list.append({
            'id': id['id'],
            'task_number': task_number['task_number'],
            'stage': stage['stage'],
            'category': category['category'],
            'task_description': task_description['task_description'],
            'comment': comment['comment'],
            'status': status['status'],
            'planned_date': planned_date['planned_date'],
            'actual_date': actual_date['actual_date'],
            'responsible': responsible['responsible'],
            'created_at': created_at['created_at']
        })

    # Статистика по статусам
    stats = db.execute(text('''
        SELECT 
            status,
            COUNT(*) as count,
            COUNT(CASE WHEN status = 'Выполнено' THEN 1 END) as completed,
            COUNT(CASE WHEN status = 'В работе' THEN 1 END) as in_progress,
            COUNT(CASE WHEN status = 'Не начато' THEN 1 END) as not_started
        FROM checklist_tasks
        GROUP BY status
    ''')).fetchall()
    
    # Статистика по этапам
    stage_stats_result = db.execute(text('''
        SELECT 
            stage,
            COUNT(*) as total,
            SUM(CASE WHEN status = 'Выполнено' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status = 'В работе' THEN 1 ELSE 0 END) as in_progress,
            SUM(CASE WHEN status = 'Не начато' THEN 1 ELSE 0 END) as not_started
        FROM checklist_tasks
        GROUP BY stage
        ORDER BY 
            CASE 
                WHEN stage = 'Договора/подрядчик/закупки' THEN 1
                WHEN stage = 'Сервисы' THEN 2
                WHEN stage = 'Честный знак' THEN 3
                WHEN stage = 'Карусель' THEN 4
                WHEN stage = 'Монтаж' THEN 5
                ELSE 6
            END
    ''')).fetchall()

    # Статистика по этапам
    stage_stats = db.execute(text('''
        SELECT 
            stage,
            COUNT(*) as total,
            SUM(CASE WHEN status = 'Выполнено' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status = 'В работе' THEN 1 ELSE 0 END) as in_progress,
            SUM(CASE WHEN status = 'Не начато' THEN 1 ELSE 0 END) as not_started
        FROM checklist_tasks
        GROUP BY stage
        ORDER BY 
            CASE 
                WHEN stage = 'Договора/подрядчик/закупки' THEN 1
                WHEN stage = 'Сервисы' THEN 2
                WHEN stage = 'Честный знак' THEN 3
                WHEN stage = 'Карусель' THEN 4
                WHEN stage = 'Монтаж' THEN 5
                ELSE 6
            END
    ''')).fetchall()
    
    # Следующие задачи (ближайшие по дате или важные)
    upcoming_tasks_result = db.execute(text('''
        SELECT * FROM checklist_tasks 
        WHERE status IN ('Не начато', 'В работе')
        AND planned_date IS NOT NULL
        ORDER BY planned_date ASC
        LIMIT 10
    ''')).fetchall()
    
    upcoming_tasks = db.execute(text('''
        SELECT * FROM checklist_tasks 
        WHERE status IN ('Не начато', 'В работе')
        AND planned_date IS NOT NULL
        ORDER BY planned_date ASC
        LIMIT 10
    ''')).fetchall()
    
    return render_template('checklist/checklist.html',
                         tasks=tasks,
                         stats=stats,
                         stage_stats=stage_stats,
                         upcoming_tasks=upcoming_tasks)

@bluprint_checklist_routes.route('/checklist/add', methods=['GET', 'POST'])
@login_required
def add_checklist_task():
    """Добавление новой задачи"""
    if request.method == 'POST':
        task_number = request.form.get('task_number')
        stage = request.form.get('stage')
        task_description = request.form.get('task_description')
        comment = request.form.get('comment')
        status = request.form.get('status', 'Не начато')
        planned_date = request.form.get('planned_date')
        responsible = request.form.get('responsible')
        
        db = get_db()
        db.execute(text('''
            INSERT INTO checklist_tasks 
            (task_number, stage, task_description, comment, status, planned_date, responsible)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        '''), (task_number, stage, task_description, comment, status, planned_date, responsible))
        db.commit()
        
        flash('Задача успешно добавлена', 'success')
        return redirect(url_for('checklist.checklist'))
    
    return render_template('checklist/add_task.html')

@bluprint_checklist_routes.route('/checklist/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_checklist_task(task_id):
    """Редактирование задачи"""
    db = get_db()
    
    if request.method == 'POST':
        task_number = request.form.get('task_number')
        stage = request.form.get('stage')
        task_description = request.form.get('task_description')
        comment = request.form.get('comment')
        status = request.form.get('status')
        planned_date = request.form.get('planned_date')
        responsible = request.form.get('responsible')
        
        # Получаем старые значения для истории
        old_task = db.execute('SELECT * FROM checklist_tasks WHERE id = ?', (task_id,)).fetchone()
        
        # Обновляем задачу
        db.execute(text('''
            UPDATE checklist_tasks 
            SET task_number = ?, stage = ?, task_description = ?, 
                comment = ?, status = ?, planned_date = ?, responsible = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        '''), (task_number, stage, task_description, comment, status, planned_date, responsible, task_id))
        db.commit()
        
        flash('Задача успешно обновлена', 'success')
        return redirect(url_for('checklist.checklist'))
    
    task = db.execute('SELECT * FROM checklist_tasks WHERE id = ?', (task_id,)).fetchone()
    
    if not task:
        flash('Задача не найдена', 'error')
        return redirect(url_for('checklist.checklist'))
    
    return render_template('checklist/edit_task.html', task=task)

@bluprint_checklist_routes.route('/checklist/<int:task_id>/update_status', methods=['POST'])
@login_required
def update_task_status(task_id):
    """Обновление статуса задачи"""
    data = request.get_json()
    new_status = data.get('status')
    
    if not new_status:
        return jsonify({'error': 'Статус не указан'}), 400
    
    db = get_db()
    
    # Получаем старый статус для истории
    old_task = db.execute('SELECT status FROM checklist_tasks WHERE id = ?', (task_id,)).fetchone()
    
    # Обновляем статус
    db.execute(text('''
        UPDATE checklist_tasks 
        SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    '''), (new_status, task_id))
    db.commit()
    
    # Записываем в историю
    if old_task:
        db.execute(text('''
            INSERT INTO checklist_history (task_id, changed_field, old_value, new_value)
            VALUES (?, ?, ?, ?)
        '''), (task_id, 'status', old_task['status'], new_status))
        db.commit()
    
    return jsonify({'success': True, 'new_status': new_status})

@bluprint_checklist_routes.route('/checklist/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_checklist_task(task_id):
    """Удаление задачи"""
    db = get_db()
    db.execute('DELETE FROM checklist_tasks WHERE id = ?', (task_id,))
    db.commit()
    
    flash('Задача успешно удалена', 'success')
    return redirect(url_for('checklist.checklist'))

@bluprint_checklist_routes.route('/checklist/stats')
@login_required
def checklist_stats():
    """Статистика по чек-листу"""
    db = get_db()
    
    # Общая статистика
    total_tasks = db.execute('SELECT COUNT(*) as count FROM checklist_tasks').fetchone()['count']
    completed_tasks = db.execute('SELECT COUNT(*) as count FROM checklist_tasks WHERE status = "Выполнено"').fetchone()['count']
    in_progress_tasks = db.execute('SELECT COUNT(*) as count FROM checklist_tasks WHERE status = "В работе"').fetchone()['count']
    not_started_tasks = db.execute('SELECT COUNT(*) as count FROM checklist_tasks WHERE status = "Не начато"').fetchone()['count']
    
    # Процент выполнения
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    # Статистика по этапам
    stage_stats = db.execute(text('''
        SELECT 
            stage,
            COUNT(*) as total,
            SUM(CASE WHEN status = 'Выполнено' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status = 'В работе' THEN 1 ELSE 0 END) as in_progress,
            SUM(CASE WHEN status = 'Не начато' THEN 1 ELSE 0 END) as not_started,
            ROUND(CAST(SUM(CASE WHEN status = 'Выполнено' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100, 1) as completion_rate
        FROM checklist_tasks
        GROUP BY stage
        ORDER BY completion_rate DESC
    ''')).fetchall()
    
    # Задачи с истекшим сроком
    overdue_tasks = db.execute(text('''
        SELECT * FROM checklist_tasks 
        WHERE planned_date < DATE('now') 
        AND status != 'Выполнено'
        ORDER BY planned_date ASC
    ''')).fetchall()
    
    return render_template('checklist/stats.html',
                         total_tasks=total_tasks,
                         completed_tasks=completed_tasks,
                         in_progress_tasks=in_progress_tasks,
                         not_started_tasks=not_started_tasks,
                         completion_rate=completion_rate,
                         stage_stats=stage_stats,
                         overdue_tasks=overdue_tasks)

@bluprint_checklist_routes.route('/checklist/export')
@login_required
def export_checklist():
    """Экспорт чек-листа в Excel"""
    try:
        from excel_utils import export_checklist_to_excel
        filename, excel_file = export_checklist_to_excel()
        
        return send_file(
            excel_file,
            download_name=filename,
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        flash(f'Ошибка при экспорте: {str(e)}', 'error')
        return redirect(url_for('checklist.checklist'))

@bluprint_checklist_routes.route('/checklist/import', methods=['GET', 'POST'])
@login_required
def import_checklist():
    """Импорт чек-листа из Excel"""
    if request.method == 'POST':
        if 'excel_file' not in request.files:
            flash('Файл не выбран', 'error')
            return redirect(request.url)
        
        file = request.files['excel_file']
        if file.filename == '':
            flash('Файл не выбран', 'error')
            return redirect(request.url)
        
        try:
            from excel_utils import import_checklist_from_excel
            success, message = import_checklist_from_excel(file)
            
            if success:
                flash(message, 'success')
            else:
                flash(message, 'error')
            
            return redirect(url_for('checklist.checklist'))
        except Exception as e:
            flash(f'Ошибка при импорте: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('checklist/import.html')