
from templates.roles.permissions import Permissions
from flask import session, url_for

class DrawableMenuItem():
    def __init__(self, icon, button_class = "nav-link"):
        self.icon = icon
        self.button_class = button_class
        pass
    def is_allowed(self):
        return True
    
    def is_active(self, url):
        return True
    
    def draw(self, url):
        return ""
    
class MenuItem(DrawableMenuItem):
    def __init__(self, icon:str, name:str, url:str, urls_to_be_active:list, permissions:list, button_class = "nav-link"):
        super().__init__(icon, button_class)
        self.name = name
        self.url = url
        self.urls_to_be_active = urls_to_be_active
        self.permissions = permissions

    def is_allowed(self):
        if len(self.permissions) == 0:
            return True

        for p in session['permissions']:
            if p in self.permissions:
                return True
        
        return False

    def is_active(self, url):
        return url in self.urls_to_be_active


    def draw(self, url):
        print (f"Рисуем элемент меню {self.name}")
        active = "active" if self.is_active(url) else ""

        if not self.is_allowed():
            print("Not allowed")
            return ""

        return f"""
            <li>
                <a
                    class="{self.button_class} {active}"
                    href="{ "index" if self.url is None or self.url == '' else url_for(self.url) }">
                    <i class="bi {self.icon}"></i>{self.name}
                </a>
            </li>
        """

class SimpleMenu(DrawableMenuItem):
    def __init__(self, icon:str):
        super().__init__(icon)
        self.items = list[DrawableMenuItem]()
    
    def add_item(self,  item:DrawableMenuItem):
        self.items.append(item)

    def draw(self, url):
        items_presentation = ""
        for i in self.items:
            items_presentation += i.draw(url)
        return items_presentation

    def is_allowed(self):
        return any(i.is_allowed() for i in self.items)

    def is_active(self, url):
        return any(i.is_active(url) for i in self.items)

class DropDownMenu(SimpleMenu):
    def __init__(self, icon:str, name:str):
        super().__init__(icon)
        self.name = name

    def draw(self, url):
        if not self.is_allowed():
            return ""
        
        active = "active" if self.is_active(url) else ""

        return f"""
        <li class="nav-item dropdown" >
            <a 
                class="nav-link dropdown-toggle 
                {active}
                href="#" data-bs-toggle="dropdown">
                <i class="bi {self.icon}"></i>{self.name}
            </a>
            <ul class="dropdown-menu">
                {super().draw(url)}
            </ul>
        </li>
        """

def create_knowlege_base_menu():
    menu = DropDownMenu(name="База знаний", icon="bi-journal-text")
    menu.add_item(MenuItem(button_class="dropdown-item", icon="bi-journal-text",name="Статьи", url="articles.articles_list", urls_to_be_active= ['articles.articles_list', 'articles.view_article', 'articles.add_article', 'articles.edit_article'], permissions=[Permissions.articles_read, Permissions.articles_manage]))
    menu.add_item(MenuItem(button_class="dropdown-item", icon="bi-sticky",name="Заметки", url="notes.notes_list", urls_to_be_active= ['notes.notes_list', 'notes.add_note', 'notes.edit_note'], permissions=[Permissions.notes_manage, Permissions.notes_read]))

    return menu

def create_simple_menu():
    menu = SimpleMenu(icon="bi-tools")
    menu.add_item(MenuItem(icon="bi-check-square",name="Задачи", url="todo.todo", urls_to_be_active= ['todo.todo', 'todo.add_todo', 'todo.edit_todo'], permissions=[Permissions.todo_manage, Permissions.todo_read]))
    menu.add_item(MenuItem(icon="bi-calendar-week",name="График смен", url="shifts.shifts_list", urls_to_be_active= ['shifts.shifts_list', 'shifts.add_shift', 'shifts.edit_shift'], permissions=[Permissions.shifts_manage, Permissions.todo_read]))
    menu.add_item(MenuItem(icon="fa-network-wired",name="Сканирование сети", url="network_scan", urls_to_be_active= ['network_scan'], permissions=[]))
    menu.add_item(MenuItem(icon="fa-terminal",name="Скрипты", url="scripts_list", urls_to_be_active= ['scripts_list'], permissions=[]))
    menu.add_item(MenuItem(icon="bi-calendar-week",name="Роли пользователей", url="roles.roles", urls_to_be_active= ['roles.roles', 'roles.create_role', 'roles.edir_role'], permissions=[Permissions.roles_manage, Permissions.roles_read]))
    menu.add_item(MenuItem(icon="bi-people",name="Пользователи", url="users.users", urls_to_be_active= ['users.users', 'users.create_user', 'users.edit_user'], permissions=[Permissions.users_manage, Permissions.users_read]))

    return menu


def create_menu():
    main_menu = DropDownMenu(name="На обслуживании", icon="bi-tools")
    main_menu.add_item(MenuItem(button_class="dropdown-item", icon="bi-pc-display", name="Устройства", url="devices.devices", urls_to_be_active= ["devices.devices", "devices.add_device", "devices.edit_device"], permissions=[Permissions.devices_manage, Permissions.devices_read]))
    main_menu.add_item(MenuItem(button_class="dropdown-item", icon="bi-wifi",name="Провайдеры", url="providers.providers", urls_to_be_active= ['providers.providers', 'providers.add_provider', 'providers.edit_provider'], permissions=[Permissions.providers_manage, Permissions.providers_read]))
    main_menu.add_item(MenuItem(button_class="dropdown-item", icon="bi-router",name="Гостевой WiFi", url="guest_wifi.guest_wifi", urls_to_be_active= ['guest_wifi.guest_wifi','guest_wifi.add_guest_wifi','guest_wifi.edit_guest_wifi'], permissions=[Permissions.guest_wifi_manage, Permissions.guest_wifi_read]))
    main_menu.add_item(MenuItem(button_class="dropdown-item", icon="bi-terminal",name="WTware Конфигурации", url="wtware_list", urls_to_be_active= ['wtware_list', 'add_wtware', 'edit_wtware'], permissions=[]))
    main_menu.add_item(MenuItem(button_class="dropdown-item", icon="bi-clock-history",name="История развертываний", url="wtware_deployments", urls_to_be_active= ['wtware_deployments'], permissions=[]))
    main_menu.add_item(MenuItem(button_class="dropdown-item", icon="bi-box",name="Программы", url="cubes.cubes", urls_to_be_active= ['cubes.cubes', 'cubes.add_cube', 'cubes.edit_cube'], permissions=[Permissions.cubes_manage, Permissions.cubes_read]))
    main_menu.add_item(MenuItem(button_class="dropdown-item", icon="bi-building",name="Организации", url="organizations.organizations", urls_to_be_active= ['organizations.organizations', 'organizations.add_organization', 'organizations.edit_organization'], permissions=[Permissions.organizations_manage, Permissions.organizations_read]))


    return main_menu


def create_main_menu():
    menu = SimpleMenu(icon="bi-speedometer2")
    
    menu.add_item(MenuItem(icon="bi-speedometer2", name="Дашборд", url="index", urls_to_be_active= ['index'], permissions=[]))
    menu.add_item(create_menu())
    menu.add_item(create_knowlege_base_menu())
    menu.add_item(create_simple_menu())

    return menu