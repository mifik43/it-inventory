from .requirements import get_current_user
from templates.roles.permissions import Permissions, Role
from templates.roles.database_roles import read_roles_for_user
from flask import url_for
from .module_registry import is_module_enabled

# ========== БАЗОВЫЕ КЛАССЫ ==========

class DrawableMenuItem:
    def __init__(self, icon, button_class="nav-link"):
        self.icon = icon
        self.button_class = button_class

    def is_allowed(self):
        return True

    def is_active(self, url):
        return True

    def draw(self, url):
        return ""


class MenuItem(DrawableMenuItem):
    def __init__(self, icon: str, name: str, url: str,
                 urls_to_be_active: list, permissions: list,
                 button_class="nav-link", module_key=None):
        super().__init__(icon, button_class)
        self.name = name
        self.url = url
        self.urls_to_be_active = urls_to_be_active
        self.permissions = permissions
        self.module_key = module_key 

    def is_allowed(self):
        # Проверяем, включён ли модуль
        if self.module_key and not is_module_enabled(self.module_key):
            return False
        user = get_current_user()
        if not user:
            return False
        if len(self.permissions) == 0:
            return True
        user_roles = read_roles_for_user(user.id)
        user_permissions = Role.get_effective_permissions(user_roles)
        for p in self.permissions:
            if p in user_permissions:
                return True
        return False

    def is_active(self, url):
        return url in self.urls_to_be_active

    def draw(self, url):
        active = "active" if self.is_active(url) else ""
        if not self.is_allowed():
            return ""
        try:
            url_for_result = url_for(self.url) if self.url and self.url != 'index' else '/'
        except:
            url_for_result = '#'
        return f"""
            <li>
                <a class="{self.button_class} {active}" href="{url_for_result}">
                    <i class="bi {self.icon}"></i> {self.name}
                </a>
            </li>
        """

class SimpleMenu(DrawableMenuItem):
    def __init__(self, icon: str = "", module_key=None):
        super().__init__(icon)
        self.items = []
        self.module_key = module_key

    def add_item(self, item: DrawableMenuItem):
        self.items.append(item)

    def draw(self, url):
        return "".join(i.draw(url) for i in self.items)

    def is_allowed(self):
        if self.module_key and not is_module_enabled(self.module_key):
            return False
        return any(i.is_allowed() for i in self.items)

    def is_active(self, url):
        return any(i.is_active(url) for i in self.items)


class DropDownMenu(SimpleMenu):
    def __init__(self, icon: str, name: str, module_key=None):
        super().__init__(icon, module_key=module_key)
        self.name = name

    def draw(self, url):
        if not self.is_allowed():
            return ""
        active = "active" if self.is_active(url) else ""
        return f"""
        <li class="nav-item dropdown">
            <a class="nav-link dropdown-toggle {active}" href="#" data-bs-toggle="dropdown">
                <i class="bi {self.icon}"></i> {self.name}
            </a>
            <ul class="dropdown-menu">
                {super().draw(url)}
            </ul>
        </li>
        """

# ========== ОСНОВНЫЕ РАЗДЕЛЫ ==========

def create_knowledge_base_menu():
    menu = DropDownMenu(name="База знаний", icon="bi-journal-text")
    menu.add_item(MenuItem(
        button_class="dropdown-item", icon="bi-journal-text", name="Статьи",
        url="articles.articles_list",
        urls_to_be_active=['articles.articles_list', 'articles.view_article', 'articles.add_article', 'articles.edit_article'],
        permissions=[Permissions.articles_read, Permissions.articles_manage],
        module_key="articles"
    ))
    menu.add_item(MenuItem(
        button_class="dropdown-item", icon="bi-sticky", name="Заметки",
        url="notes.notes_list",
        urls_to_be_active=['notes.notes_list', 'notes.add_note', 'notes.edit_note'],
        permissions=[Permissions.notes_manage, Permissions.notes_read],
        module_key="notes"
    ))
    return menu

def create_menu():
    main_menu = DropDownMenu(name="На обслуживании", icon="bi-tools")
    main_menu.add_item(MenuItem(
        button_class="dropdown-item", icon="bi-pc-display", name="Устройства",
        url="devices.devices",
        urls_to_be_active=["devices.devices", "devices.add_device", "devices.edit_device"],
        permissions=[Permissions.devices_manage, Permissions.devices_read],
        module_key="devices"
    ))
    main_menu.add_item(MenuItem(
        button_class="dropdown-item", icon="bi-wifi", name="Провайдеры",
        url="providers.providers",
        urls_to_be_active=['providers.providers', 'providers.add_provider', 'providers.edit_provider'],
        permissions=[Permissions.providers_manage, Permissions.providers_read],
        module_key="providers"
    ))
    main_menu.add_item(MenuItem(
        button_class="dropdown-item", icon="bi-router", name="Гостевой WiFi",
        url="guest_wifi.guest_wifi",
        urls_to_be_active=['guest_wifi.guest_wifi', 'guest_wifi.add_guest_wifi', 'guest_wifi.edit_guest_wifi'],
        permissions=[Permissions.guest_wifi_manage, Permissions.guest_wifi_read],
        module_key="guest_wifi"
    ))
    main_menu.add_item(MenuItem(
        button_class="dropdown-item", icon="bi-terminal", name="WTware Конфигурации",
        url="wtware.wtware_list",
        urls_to_be_active=['wtware.wtware_list', 'add_wtware', 'edit_wtware'],
        permissions=[],
        module_key="wtware"
    ))
    main_menu.add_item(MenuItem(
        button_class="dropdown-item", icon="bi-clock-history", name="История развертываний",
        url="wtware.wtware_deployments",
        urls_to_be_active=['wtware.wtware_deployments'],
        permissions=[],
        module_key="wtware"
    ))
    main_menu.add_item(MenuItem(
        button_class="dropdown-item", icon="bi-box", name="Программы",
        url="cubes.cubes",
        urls_to_be_active=['cubes.cubes', 'cubes.add_cube', 'cubes.edit_cube'],
        permissions=[Permissions.cubes_manage, Permissions.cubes_read],
        module_key="cubes"
    ))
    return main_menu

def create_operations_menu():
    """Рабочие инструменты (для всех сотрудников)"""
    menu = DropDownMenu(name="На обслуживании", icon="bi-tools")
    menu.add_item(MenuItem(button_class="dropdown-item", icon="bi-pc-display", name="Устройства", url="devices.devices",
        urls_to_be_active=["devices.devices","devices.add_device","devices.edit_device"],
        permissions=[Permissions.devices_manage, Permissions.devices_read]))
    menu.add_item(MenuItem(button_class="dropdown-item", icon="bi-wifi", name="Провайдеры", url="providers.providers",
        urls_to_be_active=['providers.providers','providers.add_provider','providers.edit_provider'],
        permissions=[Permissions.providers_manage, Permissions.providers_read]))
    menu.add_item(MenuItem(button_class="dropdown-item", icon="bi-router", name="Гостевой WiFi", url="guest_wifi.guest_wifi",
        urls_to_be_active=['guest_wifi.guest_wifi','guest_wifi.add_guest_wifi','guest_wifi.edit_guest_wifi'],
        permissions=[Permissions.guest_wifi_manage, Permissions.guest_wifi_read]))
    menu.add_item(MenuItem(button_class="dropdown-item", icon="bi-box", name="Программы (Кубы)", url="cubes.cubes",
        urls_to_be_active=['cubes.cubes','cubes.add_cube','cubes.edit_cube'],
        permissions=[Permissions.cubes_manage, Permissions.cubes_read]))
    menu.add_item(MenuItem(button_class="dropdown-item", icon="bi-check-square", name="Задачи", url="todo.todo",
        urls_to_be_active=['todo.todo','todo.add_todo','todo.edit_todo'],
        permissions=[Permissions.todo_manage, Permissions.todo_read]))
    menu.add_item(MenuItem(button_class="dropdown-item", icon="bi-terminal", name="WTware", url="wtware.wtware_list",
        urls_to_be_active=['wtware.wtware_list','add_wtware','edit_wtware'],
        permissions=[]))  # пока без прав
    return menu

def create_hr_menu():
    """Кадровое меню (для HR или руководителей)"""
    menu = DropDownMenu(name="Кадровое", icon="bi-people")
    menu.add_item(MenuItem(button_class="dropdown-item", icon="bi-calendar-week", name="График смен", url="shifts.shifts_list",
        urls_to_be_active=['shifts.shifts_list','shifts.add_shift','shifts.edit_shift'],
        permissions=[Permissions.shifts_manage, Permissions.shifts_read]))  # можно отдельное разрешение
    # В будущем можно добавить отпуска, больничные и т.д.
    return menu

def create_administration_menu():
    menu = DropDownMenu(name="Администрирование", icon="bi-shield-lock")
    menu.add_item(MenuItem(
        button_class="dropdown-item", icon="bi-people", name="Пользователи",
        url="users.users",
        urls_to_be_active=['users.users', 'users.create_user', 'users.edit_user'],
        permissions=[Permissions.users_manage, Permissions.users_read],
        module_key="users"
    ))
    menu.add_item(MenuItem(
        button_class="dropdown-item", icon="bi-calendar-week", name="Роли",
        url="roles.roles",
        urls_to_be_active=['roles.roles', 'roles.create_role', 'roles.edit_role'],
        permissions=[Permissions.roles_manage, Permissions.roles_read],
        module_key="roles"
    ))
    menu.add_item(MenuItem(
        button_class="dropdown-item", icon="bi-key", name="Пароли",
        url="password_manager.folders",
        urls_to_be_active=['password_manager.folders', 'password_manager.folder_entries', 'password_manager.view_entry', 'password_manager.history'],
        permissions=[Permissions.password_manager_read, Permissions.password_manager_manage],
        module_key="password_manager"
    ))
    menu.add_item(MenuItem(
        button_class="dropdown-item", icon="bi-toggles", name="Модули",
        url="admin_modules.modules_list",
        urls_to_be_active=['admin_modules.modules_list'],
        permissions=[Permissions.roles_manage]
    ))
    menu.add_item(MenuItem(
        button_class="dropdown-item",
        icon="bi-activity",
        name="Мониторинг",
        url="monitoring.index",
        urls_to_be_active=['monitoring.index'],
        permissions=[Permissions.roles_manage]
    ))
    menu.add_item(MenuItem(
        button_class="dropdown-item",
        icon="bi-database",
        name="Мониторинг БД",
        url="db_monitoring.index",
        urls_to_be_active=['db_monitoring.index'],
        permissions=[Permissions.roles_manage],
        module_key="monitoring"
    ))
    return menu


def create_security_menu():
    menu = DropDownMenu(name="Безопасность", icon="bi-shield-check", module_key="security_scan")
    menu.add_item(MenuItem(
        button_class="dropdown-item", icon="bi-shield-lock", name="Сканирование безопасности",
        url="security_scan.index",
        urls_to_be_active=['security_scan.index', 'security_scan.task_detail'],
        permissions=[Permissions.security_scan_read, Permissions.security_scan_manage]
    ))
    menu.add_item(MenuItem(
        button_class="dropdown-item", icon="bi-list-check", name="Whitelist подсетей",
        url="security_scan.whitelist",
        urls_to_be_active=['security_scan.whitelist'],
        permissions=[Permissions.security_scan_whitelist]
    ))
    return menu

def create_scanning_menu():
    """Сканирование сети (общее)"""
    menu = DropDownMenu(name="Сканирование", icon="bi-radar")
    menu.add_item(MenuItem(button_class="dropdown-item", icon="fa-network-wired", name="Сканирование сети", url="network_scan.network_scan",
        urls_to_be_active=['network_scan.network_scan','network_scan.network_scan_results','network_scan.network_devices'],
        permissions=[]))
    menu.add_item(MenuItem(button_class="dropdown-item", icon="bi-diagram-3", name="Граф сети", url="network_scan.graph_list",
        urls_to_be_active=['network_scan.graph_list','network_scan.create_graph','network_scan.view_graph'],
        permissions=[]))
    return menu

def create_organizations_menu():
    menu = DropDownMenu(name="Организации", icon="bi-building", module_key="organizations")
    menu.add_item(MenuItem(
        button_class="dropdown-item", icon="bi-building", name="Список организаций",
        url="organizations.organizations",
        urls_to_be_active=['organizations.organizations', 'organizations.add_organization', 'organizations.edit_organization'],
        permissions=[Permissions.organizations_manage, Permissions.organizations_read]
    ))
    menu.add_item(MenuItem(
        button_class="dropdown-item", icon="bi-diagram-2", name="Иерархия организаций",
        url="organizations.hierarchy",
        urls_to_be_active=['organizations.hierarchy'],
        permissions=[Permissions.organizations_manage]
    ))
    menu.add_item(MenuItem(
        button_class="dropdown-item", icon="bi-people", name="Пользователи по организациям",
        url="organizations.users_by_organization",
        urls_to_be_active=['organizations.users_by_organization'],
        permissions=[Permissions.organizations_manage]
    ))
    menu.add_item(MenuItem(
        button_class="dropdown-item", icon="bi-bar-chart", name="Отчёт по активности",
        url="organizations.activity_report",
        urls_to_be_active=['organizations.activity_report'],
        permissions=[Permissions.organizations_manage]
    ))
    return menu

def create_simple_menu():
    menu = SimpleMenu(icon="bi-tools")
    menu.add_item(MenuItem(
        icon="bi-check-square", name="Задачи",
        url="todo.todo",
        urls_to_be_active=['todo.todo', 'todo.add_todo', 'todo.edit_todo'],
        permissions=[Permissions.todo_manage, Permissions.todo_read],
        module_key="todo"
    ))
    menu.add_item(MenuItem(
        icon="bi-calendar-week", name="График смен",
        url="shifts.shifts_list",
        urls_to_be_active=['shifts.shifts_list', 'shifts.add_shift', 'shifts.edit_shift'],
        permissions=[Permissions.shifts_manage, Permissions.shifts_read],
        module_key="shifts"
    ))
    menu.add_item(MenuItem(
        icon="fa-terminal", name="Скрипты",
        url="script.script_list",
        urls_to_be_active=['script.script_list'],
        permissions=[],
        module_key="scripts"
    ))
    return menu

# ========== ТЕСТОВЫЕ РАЗДЕЛЫ (скрыты для обычных пользователей) ==========

def create_social_menu():
    menu = DropDownMenu(name="Соцсети (тест)", icon="bi-share", module_key="social")
    menu.add_item(MenuItem(
        button_class="dropdown-item", icon="bi-clock-history", name="История публикаций",
        url="social.social_history",
        urls_to_be_active=['social.social_history'],
        permissions=[Permissions.social_read, Permissions.social_manage]
    ))
    menu.add_item(MenuItem(
        button_class="dropdown-item", icon="bi-calendar-event", name="Запланированные",
        url="social.scheduled_posts",
        urls_to_be_active=['social.scheduled_posts'],
        permissions=[Permissions.social_read, Permissions.social_manage]
    ))
    menu.add_item(MenuItem(
        button_class="dropdown-item", icon="bi-gear", name="Настройки платформ",
        url="social.social_platforms",
        urls_to_be_active=['social.social_platforms'],
        permissions=[Permissions.social_manage]
    ))
    return menu

def create_checklist_menu():
    menu = DropDownMenu(name="Чек-лист", icon="bi-clipboard-check", module_key="checklist")
    menu.add_item(MenuItem(
        button_class="dropdown-item", icon="bi-clipboard-check", name="Чек-лист",
        url="checklist.checklist",
        urls_to_be_active=['checklist.checklist', 'checklist.add_checklist_task', 'checklist.edit_checklist_task'],
        permissions=[]
    ))
    menu.add_item(MenuItem(
        button_class="dropdown-item", icon="bi-graph-up", name="Статистика",
        url="checklist.checklist_stats",
        urls_to_be_active=['checklist.checklist_stats'],
        permissions=[]
    ))
    return menu

# ========== ГЛАВНОЕ МЕНЮ ==========

def create_main_menu():
    menu = SimpleMenu(icon="bi-speedometer2")
    menu.add_item(MenuItem(icon="bi-speedometer2", name="Дашборд",
                           url="index", urls_to_be_active=['index'], permissions=[]))
    menu.add_item(create_menu())
    menu.add_item(create_organizations_menu())
    menu.add_item(create_knowlege_base_menu() if 'create_knowlege_base_menu' in globals() else create_knowledge_base_menu())
    menu.add_item(create_simple_menu())
    menu.add_item(create_scanning_menu())
    menu.add_item(create_social_menu())
    menu.add_item(create_checklist_menu())
    menu.add_item(create_administration_menu())
    menu.add_item(create_security_menu())
    menu.add_item(MenuItem(icon="bi-question-circle", name="Справка",
                           url="help.index",
                           urls_to_be_active=['help.index', 'help.section'],
                           permissions=[]))
    return menu