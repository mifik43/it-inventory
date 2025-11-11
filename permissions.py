import enum

import database_roles as db_helper


# список всех разрешений
class Permissions(enum.Enum):
    users_read = 1
    users_manage = 2
    roles_read = 3
    roles_manage = 4

    def to_name(p):
        if p == Permissions.users_read:
            return "Чтение списка пользователей и их настроек"
        elif p == Permissions.users_manage:
            return "Управление списком пользователей и их настройками"
        elif p == Permissions.roles_read:
            return "Чтение списка ролей и разрешений"
        elif p == Permissions.roles_manage:
            return "Управление списком ролей и разрешений"


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
class Role:
    def __init__(self, id, name, permissions = set(), description = str()):
        self.id = id
        self.name = name
        self.permissions:Permissions = permissions
        self.description = description
        self.checked = ""
    
    def __str__(self):
        return f"Role: id = {str(self.id)} name = {self.name}, perm = [{self.permissions}]"

    def add_permission(self, p:Permissions):
        self.permissions.add(p)
        print(f"В роль \"{self.name}\" было добавлено разрешение \"{p.name}\"")

    def remove_permission(self, p:Permissions):
        if self.is_permission_granted(p):
            self.permissions.remove(p)
            print(f"Из роли \"{self.name}\" было удалено разрешение \"{p.name}\"")
    
    def is_permission_granted(self, p:Permissions):
        return p in self.permissions
    
    def get_effective_permissions(roles:list[Role]):
        permissions = set()
        for role in roles:
            for p in role.permissions:
                permissions.add(p)
        
        return permissions

    
# роль со всеми правами
def create_full_access_role():
    role = Role(0, "SuperAdmin", description="Роль админа по умолчанию")

    for p in Permissions:
        role.add_permission(p)
    
    return role

