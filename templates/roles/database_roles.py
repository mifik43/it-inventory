import sqlite3

import enum
import templates.roles.permissions as permissions

from templates.base.database_helper import get_db

def find_role_by_name(name:str, db = get_db()):
    return db.execute(
        f"select id, name, description from roles where name=\"{name}\""
    ).fetchone()

def find_role_by_id(id:int, db = get_db()):
    row = db.execute(
        f"select id, name, description from roles where id={id}"
    ).fetchone()

    return permissions.Role(id=row["id"], name=row["name"], description=row["description"], permissions=read_role_permissions(row["id"], db))



def remove_permissions_for_role(id:int, db = get_db(), commit = True):
    print(f"Удаляем разрешения для роли с id={id}")
    db.execute(
        f"DELETE FROM roles_to_permissions WHERE role_id={id}"
    )
    if commit:
        db.commit()


def save_role_permissions(role : permissions.Role, db = get_db(), commit = True):
    remove_permissions_for_role(role.id, db, False)
    print(f"Удаляем разрешения для роли с id={role.id} ({role.name})")
    for p in role.permissions:
        db.execute(
            f"INSERT INTO roles_to_permissions (role_id, permission) VALUES ({role.id}, \"{p.value}\") ON CONFLICT(role_id, permission) DO UPDATE SET permission=\"{p.value}\""
        )



def update_role(role : permissions.Role, db = get_db(), commit = True):
    print(f"Обновляем роль {role}")

    db.execute(
        f"UPDATE roles SET name = \"{role.name}\", description = \"{role.description}\" WHERE id={role.id}"
    )

    save_role_permissions(role, db, False)

    if commit:
        db.commit()


def save_role(role : permissions.Role, db = get_db(), commit = True):
    print(f"Сохраняем роль {role}")

    existing_role = find_role_by_name(role.name, db)
    if existing_role is not None:
        raise ValueError(f"Роль с именем \"{role.name}\" уже существует")

    if role.id is None:
        db.execute(
            f"INSERT INTO roles (name, description) VALUES ('{role.name}', '{role.description}')"
        )

        existing_role = find_role_by_name(role.name, db)
        if existing_role is None:
            raise ValueError(f"Во время сохранения роли \"{role.name}\" произошла ошибка")
        role.id = existing_role["id"]
    else:
        db.execute(
            f"INSERT INTO roles (id, name, description) VALUES ({role.id}, '{role.name}', '{role.description}')"
        )
    
    # наполняем её разрешениями
    save_role_permissions(role, db, False)

    if commit:
        db.commit()

def remove_role(id:int, db = get_db(), commit = True):
    print(f"Удаляем роль с id={id}")
    db.execute(
        f"DELETE FROM roles WHERE id={id}"
    )
    remove_permissions_for_role(id, db, False)
    db.execute(
        f"DELETE FROM roles_to_permissions WHERE role_id={id}"
    )
    if commit:
        db.commit()

def read_role_permissions(id, db = get_db()):
    rows = db.execute(f"""
            select role_id, permission 
            from roles_to_permissions
            where role_id = {id}
            order by permission
        """).fetchall()

    all_permissions = set()
    for r in rows:
        id = r["permission"]
        for p in permissions.Permissions:
            if id == p.value:
                all_permissions.add(p)
    
    return all_permissions

def read_all_roles(db = get_db()) -> list[permissions.Role]:
    roles = list[permissions.Role]()
    rows = db.execute("select id, name, description from roles order by id").fetchall()

    for row in rows:
        roles.append(permissions.Role(id=row["id"], name=row["name"], description=row["description"], permissions=read_role_permissions(row["id"], db)))
    
    return roles

def remove_all_roles_from_user(user_id:int, db = get_db(), commit = True):
    print(f"Удаляем все роли у пользователя c id={user_id}")
    db.execute(
        f"DELETE FROM roles_to_user WHERE user_id={user_id}"
    )
    if commit:
        db.commit()

def save_roles_to_user(user_id:int, roles:list[permissions.Role], db = get_db(), commit = True):
    remove_all_roles_from_user(user_id, db, False)
    for role in roles:
        print(f"Сохраняем роль {role.name} для пользователя с id={user_id}")
        db.execute(
            f"INSERT INTO roles_to_user (role_id, user_id) VALUES ('{role.id}', '{user_id}')"
        )
    if commit:
        db.commit()

def save_roles_to_user_by_id(user_id:int, role_ids:list[int], db = get_db(), commit = True):
    remove_all_roles_from_user(user_id, db, False)
    for role_id in role_ids:
        print(f"Сохраняем роль {role_id} для пользователя с id={user_id}")
        db.execute(
            f"INSERT INTO roles_to_user (role_id, user_id) VALUES ('{role_id}', '{user_id}')"
        )
    if commit:
        db.commit()

def read_roles_for_user(user_id:int, db = get_db()) -> list[permissions.Role]:

    # прочтём список всех ролей
    all_roles = read_all_roles(db)

    # список id-шников ролей, назначеных пользователю
    rows = db.execute(f"""
            select role_id, user_id 
            from roles_to_user
            where user_id = {user_id}
            order by role_id
        """).fetchall()

    # выберем из списка ролей те, которые есть в списке назначеных пользователю
    user_roles = list[permissions.Role]()
    for r in rows:
        id = r["role_id"]
        for role in all_roles:
            if id == role.id:
                user_roles.append(role)
    
    return user_roles

def init_default_admin_role(db:sqlite3.Connection):

    # Добавляем администратора по умолчанию
    cursor = db.execute('SELECT COUNT(*) as count FROM roles')
    count = cursor.fetchone()['count']
    
    if count == 0:
        # создаём роль админа
        print("Ролей не найдено. Создаём роль админа по умолчанию")
        role = permissions.create_full_access_role()
        save_role(role, db, False)
        

def create_roles_tables(db:sqlite3.Connection):
    # Таблица ролей
    db.execute('''
        CREATE TABLE IF NOT EXISTS roles (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               name TEXT UNIQUE NOT NULL,
               description TEXT
            )
    ''')

        # Таблица ролей
    db.execute('''
        CREATE TABLE IF NOT EXISTS roles_to_permissions (
               role_id INTEGER,
               permission TEXT,

               PRIMARY KEY (role_id, permission)
            )
    ''')

    db.execute('''
        CREATE TABLE IF NOT EXISTS roles_to_user (
               role_id INTEGER,
               user_id INTEGER,

               PRIMARY KEY (role_id, user_id)
            )
    ''')


    
    init_default_admin_role(db)
