import enum

import database_roles as db_helper


# список всех разрешений
class Permissions(enum.Enum):
    users_read = 1
    users_manage = 2
    permissions_read = 3
    permissions_manage = 4
    roles_read = 5
    roles_manage = 6


# класс для работы с ролями
# каждая роль имеет уникальный id, имя и список разрешений
class Role:
    def __init__(self, id, name, permissions = set(), description = str()):
        self.id = id
        self.name = name
        self.permissions:Permissions = permissions
        self.description = description
    
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
    
# роль со всеми правами
def create_full_access_role():
    role = Role(0, "SuperAdmin", description="Роль админа по умолчанию")

    for p in Permissions:
        role.add_permission(p)
    
    return role

