from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required
from templates.base.database_helper import db
from templates.base.requirements import login_required as req_login_required
from models import ChecklistTask, ChecklistHistory
from sqlalchemy import func, desc
from datetime import datetime

bluprint_checklist_routes = Blueprint('checklist', __name__, template_folder='templates')

# ============================================================
# Инициализация таблиц и начальных данных
# ============================================================
def init_checklist_db():
    """Создаёт таблицы, если их нет (вызывается из app.py)"""
    db.create_all()

def import_initial_checklist_data():
    """Импортирует начальные данные, если таблица пуста"""
    if ChecklistTask.query.first() is not None:
        return  # данные уже есть

    checklist_data = [
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

    for item in checklist_data:
        task = ChecklistTask(
            task_number=item.get('task_number'),
            stage=item['stage'],
            task_description=item['description'],
            category=item.get('task'),  # поле 'task' в исходных данных – это категория
            comment=item.get('comment', ''),
            status=item.get('status', 'Не начато')
        )
        db.session.add(task)
    db.session.commit()

# ============================================================
# Маршруты
# ============================================================
@bluprint_checklist_routes.route('/checklist')
@req_login_required
def checklist():
    """Главная страница чек-листа"""
    # Все задачи с сортировкой по этапам, категории и номеру
    tasks = ChecklistTask.query.order_by(
        db.case(
            (ChecklistTask.stage == 'Договора/подрядчик/закупки', 1),
            (ChecklistTask.stage == 'Сервисы', 2),
            (ChecklistTask.stage == 'Честный знак', 3),
            (ChecklistTask.stage == 'Карусель', 4),
            (ChecklistTask.stage == 'Монтаж', 5),
            else_=6
        ),
        ChecklistTask.category,
        ChecklistTask.task_number
    ).all()

    # Статистика по статусам (общая)
    status_stats = db.session.query(
        ChecklistTask.status,
        func.count().label('count')
    ).group_by(ChecklistTask.status).all()

    # Статистика по этапам
    stage_stats = db.session.query(
        ChecklistTask.stage,
        func.count().label('total'),
        func.sum(db.case((ChecklistTask.status == 'Выполнено', 1), else_=0)).label('completed'),
        func.sum(db.case((ChecklistTask.status == 'В работе', 1), else_=0)).label('in_progress'),
        func.sum(db.case((ChecklistTask.status == 'Не начато', 1), else_=0)).label('not_started')
    ).group_by(ChecklistTask.stage).order_by(
        db.case(
            (ChecklistTask.stage == 'Договора/подрядчик/закупки', 1),
            (ChecklistTask.stage == 'Сервисы', 2),
            (ChecklistTask.stage == 'Честный знак', 3),
            (ChecklistTask.stage == 'Карусель', 4),
            (ChecklistTask.stage == 'Монтаж', 5),
            else_=6
        )
    ).all()

    # Ближайшие задачи (planned_date не null и статус не выполнено)
    upcoming_tasks = ChecklistTask.query.filter(
        ChecklistTask.status.in_(['Не начато', 'В работе']),
        ChecklistTask.planned_date.isnot(None)
    ).order_by(ChecklistTask.planned_date.asc()).limit(10).all()

    return render_template('checklist/checklist.html',
                           tasks=tasks,
                           status_stats=status_stats,
                           stage_stats=stage_stats,
                           upcoming_tasks=upcoming_tasks)


@bluprint_checklist_routes.route('/checklist/add', methods=['GET', 'POST'])
@req_login_required
def add_checklist_task():
    """Добавление новой задачи"""
    if request.method == 'POST':
        task = ChecklistTask(
            task_number=request.form.get('task_number'),
            stage=request.form.get('stage'),
            task_description=request.form.get('task_description'),
            comment=request.form.get('comment'),
            status=request.form.get('status', 'Не начато'),
            planned_date=request.form.get('planned_date') or None,
            responsible=request.form.get('responsible')
        )
        db.session.add(task)
        db.session.commit()
        flash('Задача успешно добавлена', 'success')
        return redirect(url_for('checklist.checklist'))

    return render_template('checklist/add_task.html')


@bluprint_checklist_routes.route('/checklist/<int:task_id>/edit', methods=['GET', 'POST'])
@req_login_required
def edit_checklist_task(task_id):
    """Редактирование задачи"""
    task = ChecklistTask.query.get_or_404(task_id)

    if request.method == 'POST':
        # Сохраняем старые значения для истории (если нужно)
        old_status = task.status
        task.task_number = request.form.get('task_number')
        task.stage = request.form.get('stage')
        task.task_description = request.form.get('task_description')
        task.comment = request.form.get('comment')
        task.status = request.form.get('status')
        task.planned_date = request.form.get('planned_date') or None
        task.responsible = request.form.get('responsible')
        task.updated_at = datetime.utcnow()

        # Запись в историю изменения статуса
        if old_status != task.status:
            history = ChecklistHistory(
                task_id=task.id,
                changed_field='status',
                old_value=old_status,
                new_value=task.status
            )
            db.session.add(history)

        db.session.commit()
        flash('Задача успешно обновлена', 'success')
        return redirect(url_for('checklist.checklist'))

    return render_template('checklist/edit_task.html', task=task)


@bluprint_checklist_routes.route('/checklist/<int:task_id>/update_status', methods=['POST'])
@req_login_required
def update_task_status(task_id):
    """Обновление статуса задачи (AJAX)"""
    data = request.get_json()
    new_status = data.get('status')
    if not new_status:
        return jsonify({'error': 'Статус не указан'}), 400

    task = ChecklistTask.query.get_or_404(task_id)
    old_status = task.status
    task.status = new_status
    task.updated_at = datetime.utcnow()

    # Запись в историю
    history = ChecklistHistory(
        task_id=task.id,
        changed_field='status',
        old_value=old_status,
        new_value=new_status
    )
    db.session.add(history)
    db.session.commit()

    return jsonify({'success': True, 'new_status': new_status})


@bluprint_checklist_routes.route('/checklist/<int:task_id>/delete', methods=['POST'])
@req_login_required
def delete_checklist_task(task_id):
    """Удаление задачи"""
    task = ChecklistTask.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    flash('Задача успешно удалена', 'success')
    return redirect(url_for('checklist.checklist'))


@bluprint_checklist_routes.route('/checklist/stats')
@req_login_required
def checklist_stats():
    """Статистика по чек-листу"""
    total_tasks = ChecklistTask.query.count()
    completed_tasks = ChecklistTask.query.filter_by(status='Выполнено').count()
    in_progress_tasks = ChecklistTask.query.filter_by(status='В работе').count()
    not_started_tasks = ChecklistTask.query.filter_by(status='Не начато').count()
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

    # Статистика по этапам с процентом выполнения
    stage_stats = db.session.query(
        ChecklistTask.stage,
        func.count().label('total'),
        func.sum(db.case((ChecklistTask.status == 'Выполнено', 1), else_=0)).label('completed'),
        func.sum(db.case((ChecklistTask.status == 'В работе', 1), else_=0)).label('in_progress'),
        func.sum(db.case((ChecklistTask.status == 'Не начато', 1), else_=0)).label('not_started'),
        (func.sum(db.case((ChecklistTask.status == 'Выполнено', 1), else_=0)) * 100.0 / func.count()).label('completion_rate')
    ).group_by(ChecklistTask.stage).order_by(desc('completion_rate')).all()

    # Просроченные задачи (planned_date < сегодня и статус не выполнено)
    today = datetime.now().date()
    overdue_tasks = ChecklistTask.query.filter(
        ChecklistTask.planned_date < today,
        ChecklistTask.status != 'Выполнено'
    ).order_by(ChecklistTask.planned_date.asc()).all()

    return render_template('checklist/stats.html',
                         total_tasks=total_tasks,
                         completed_tasks=completed_tasks,
                         in_progress_tasks=in_progress_tasks,
                         not_started_tasks=not_started_tasks,
                         completion_rate=completion_rate,
                         stage_stats=stage_stats,
                         overdue_tasks=overdue_tasks)


@bluprint_checklist_routes.route('/checklist/export')
@req_login_required
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
@req_login_required
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
            flash(message, 'success' if success else 'error')
            return redirect(url_for('checklist.checklist'))
        except Exception as e:
            flash(f'Ошибка при импорте: {str(e)}', 'error')
            return redirect(request.url)
    return render_template('checklist/import.html')