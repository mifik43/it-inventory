import sqlite3

import enum
import permissions

from database_helper import get_db

def find_role_by_name(name:str, db = get_db()):
    return db.execute(
        f"select id, name, description from roles where name=\"{name}\""
    ).fetchone()

def find_role_by_id(id:int, db = get_db()):
    return db.execute(
        f"select id, name, description from roles where id={id}"
    ).fetchone()

def update_role(role : permissions.Role, db = get_db(), commit = True):
    print(f"Обновляем роль {role}")

    db.execute(
        f"UPDATE roles SET name = \"{role.name}\", description = \"{role.description}\" WHERE id={role.id}"
    )

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
    for p in role.permissions:
        db.execute(
            f"INSERT INTO roles_to_permissions (role_id, permission) VALUES ({role.id}, {p.value})"
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

def read_all_roles(db = get_db()):
    roles = list()
    rows = db.execute("select id, name, description from roles order by id").fetchall()

    for row in rows:
        roles.append(permissions.Role(id=row["id"], name=row["name"], description=row["description"], permissions=read_role_permissions(row["id"], db)))
    
    return roles
    

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
               permission INTEGER
            )
    ''')


    
    init_default_admin_role(db)
