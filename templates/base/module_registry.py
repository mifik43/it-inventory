# Список всех модулей системы.
# Ключ используется как идентификатор, display_name — отображаемое имя.
MODULES = [
    {'key': 'devices',        'name': 'Устройства',              'icon': 'bi-pc-display'},
    {'key': 'providers',      'name': 'Провайдеры',              'icon': 'bi-wifi'},
    {'key': 'guest_wifi',     'name': 'Гостевой WiFi',           'icon': 'bi-router'},
    {'key': 'cubes',          'name': 'Программы (Кубы)',        'icon': 'bi-box'},
    {'key': 'todo',           'name': 'Задачи',                  'icon': 'bi-check-square'},
    {'key': 'shifts',         'name': 'График смен',             'icon': 'bi-calendar-week'},
    {'key': 'articles',       'name': 'Статьи',                  'icon': 'bi-journal-text'},
    {'key': 'notes',          'name': 'Заметки',                 'icon': 'bi-sticky'},
    {'key': 'organizations',  'name': 'Организации',             'icon': 'bi-building'},
    {'key': 'users',          'name': 'Пользователи',            'icon': 'bi-people'},
    {'key': 'roles',          'name': 'Роли',                    'icon': 'bi-shield-lock'},
    {'key': 'password_manager', 'name': 'Менеджер паролей',      'icon': 'bi-key'},
    {'key': 'network_scan',   'name': 'Сканирование сети',       'icon': 'bi-radar'},
    {'key': 'security_scan',  'name': 'Сканирование безопасности','icon': 'bi-shield-check'},
    {'key': 'checklist',      'name': 'Чек-лист',                'icon': 'bi-clipboard-check'},
    {'key': 'social',         'name': 'Соцсети (тест)',          'icon': 'bi-share'},
    {'key': 'wtware',         'name': 'WTware',                  'icon': 'bi-terminal'},
    {'key': 'scripts',        'name': 'Скрипты',                 'icon': 'bi-terminal'},
    {'key': 'network_graph',  'name': 'Граф сети',               'icon': 'bi-diagram-3'},
    {'key': 'monitoring', 'name': 'Мониторинг системы', 'icon': 'bi-activity'},
]


def is_module_enabled(module_key):
    """Проверяет, включён ли модуль."""
    from models import ModuleSettings
    setting = ModuleSettings.query.filter_by(module_key=module_key).first()
    # Если записи нет — считаем модуль включённым по умолчанию
    return setting.is_enabled if setting else True


def get_all_module_settings():
    """Возвращает список словарей со статусами всех модулей."""
    from models import ModuleSettings
    result = []
    for m in MODULES:
        setting = ModuleSettings.query.filter_by(module_key=m['key']).first()
        enabled = setting.is_enabled if setting else True
        result.append({
            'key': m['key'],
            'name': m['name'],
            'icon': m['icon'],
            'enabled': enabled,
        })
    return result


def ensure_module_settings():
    """Создаёт записи для всех модулей, если их ещё нет."""
    from models import ModuleSettings
    from templates.base.database_helper import db
    created = 0
    for m in MODULES:
        existing = ModuleSettings.query.filter_by(module_key=m['key']).first()
        if not existing:
            db.session.add(ModuleSettings(
                module_key=m['key'],
                display_name=m['name'],
                is_enabled=True,
            ))
            created += 1
    if created:
        db.session.commit()
    return created