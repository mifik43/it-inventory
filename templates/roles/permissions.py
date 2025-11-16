import enum

from templates.base.db import Base, get_db_engine

from sqlalchemy import String, Column, Table, ForeignKey, TypeDecorator, select
from sqlalchemy.orm import Mapped, mapped_column, relationship, Session

# список всех разрешений
class Permissions(enum.StrEnum):
    users_read = "users_read"
    users_manage = "users_manage"
    roles_read = "roles_read"
    roles_manage = "roles_manage"
    devices_read = "devices_read"
    devices_manage = "devices_manage"
    providers_read = "providers_read"
    providers_manage = "providers_manage"
    articles_read = "articles_read"
    articles_manage = "articles_manage"
    notes_read = "notes_read"
    notes_manage = "notes_manage"
    cubes_read = "cubes_read"
    cubes_manage = "cubes_manage"
    guest_wifi_read = "guest_wifi_read"
    guest_wifi_manage = "guest_wifi_manage"
    organizations_read = "organizations_read"
    organizations_manage = "organizations_manage"
    shifts_read = "shifts_read"
    shifts_manage = "shifts_manage"
    todo_read = "todo_read"
    todo_manage = "todo_manage"

    def to_name(p):
        if p == Permissions.users_read:
            return "Чтение списка пользователей"
        elif p == Permissions.users_manage:
            return "Управление списком пользователей"
        elif p == Permissions.roles_read:
            return "Чтение списка ролей и разрешений"
        elif p == Permissions.roles_manage:
            return "Управление списком ролей и разрешений"
        elif p == Permissions.devices_read:
            return "Чтение списка устройств"
        elif p == Permissions.devices_manage:
            return "Управление списком устройств"
        elif p == Permissions.providers_read:
            return "Чтение списка провайдеров"
        elif p == Permissions.providers_manage:
            return "Управление списком провайдеров"
        elif p == Permissions.articles_read:
            return "Чтение списка статей"
        elif p == Permissions.articles_manage:
            return "Управление списком статей"
        elif p == Permissions.notes_read:
            return "Чтение списка заметок"
        elif p == Permissions.notes_manage:
            return "Управление списком заметок"
        elif p == Permissions.cubes_read:
            return "Чтение списка кубов"
        elif p == Permissions.cubes_manage:
            return "Управление списком кубов"
        elif p == Permissions.guest_wifi_read:
            return "Чтение списка гостевых WiFi"
        elif p == Permissions.guest_wifi_manage:
            return "Управление списком гостевых WiFi"
        elif p == Permissions.organizations_read:
            return "Чтение списка организаций"
        elif p == Permissions.organizations_manage:
            return "Управление списком организаций"
        elif p == Permissions.shifts_read:
            return "Чтение графика смен"
        elif p == Permissions.shifts_manage:
            return "Управление графиком смен"
        elif p == Permissions.todo_read:
            return "Чтение списка задач"
        elif p == Permissions.todo_manage:
            return "Управление списком задач"
    
    def get_names():
        names = dict()
        for p in Permissions:
            nested = dict()
            nested['name'] = Permissions.to_name(p)
            nested['checked'] = '' 
            names[p] = nested
        
        return names

# класс для работы с ролями
# каждая роль имеет уникальный id, имя и список разрешений
class Role(Base):

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String())
    permissions = set()
    checked = ""


    # def __init__(self, id, name, permissions = set(), description = str()):
    #     self.name = name
    #     self.permissions:Permissions = permissions
    #     self.checked = ""
    
    def __str__(self):
        perms:str = ""
        for p in self.permissions:
            perms += str(p) + " "
        return f"Role: id = {str(self.id)} name = {self.name}, perm = [{perms}]"

    def add_permission(self, p:Permissions):
        self.permissions.add(p)
        print(f"В роль \"{self.name}\" было добавлено разрешение \"{p.name}\"")

    def remove_permission(self, p:Permissions):
        if self.is_permission_granted(p):
            self.permissions.remove(p)
            print(f"Из роли \"{self.name}\" было удалено разрешение \"{p.name}\"")
    
    def is_permission_granted(self, p:Permissions):
        return p in self.permissions
    
    def get_effective_permissions(roles):
        permissions = set()
        for role in roles:
            for p in role.permissions:
                permissions.add(p)
        
        return permissions

    
# роль со всеми правами
def create_full_access_role():
    role = Role(id=None, name="SuperAdmin", description="Роль админа по умолчанию", permissions=set())

    for p in Permissions:
        role.add_permission(p)
    
    return role

def create_read_only_role():
    role = Role(id=None, name="Reader", description="Роль с правами только на чтение", permissions=set())

    for p in Permissions:
        if str(p).endswith("read"):
            role.add_permission(p)

    return role

def find_role_by_name(name:str, session:Session):
    return session.scalar(select(Role).where(Role.name == name))

def init_default_roles():
    with Session(get_db_engine()) as session:
        role = find_role_by_name("SuperAdmin", session)
        if role is not None:
            print("Роль SuperAdmin найдена")
            return
        
        print("Роль SuperAdmin не найдена. Создаём")
        role = create_full_access_role()
        reader = create_read_only_role()

        session.add(role)
        session.add(reader)
        session.commit()

