import templates.roles.permissions as permissions

from sqlalchemy import delete, func, select

from templates.base.database_helper import db as flask_db, get_db
from models import Permission as ORMPermission, Role as ORMRole, RolePermission as ORMRolePermission, UserRole as ORMUserRole


def _permission_model_for(permission_enum, db):
    permission = db.scalars(select(ORMPermission).filter_by(name=permission_enum.value)).first()
    if permission is None:
        permission = ORMPermission(name=permission_enum.value, description=permissions.Permissions.to_name(permission_enum))
        db.add(permission)
        db.flush()
    return permission


def _role_model_to_domain(role_model):
    if role_model is None:
        return None

    permission_set = set()
    for p in role_model.permissions:
        try:
            permission_set.add(permissions.Permissions(p.name))
        except ValueError:
            continue

    return permissions.Role(
        id=role_model.id,
        name=role_model.name,
        description=role_model.description,
        permissions=permission_set
    )


def _ensure_permissions(db):
    existing_permissions = {name for (name,) in db.execute(select(ORMPermission.name)).all()}
    for p in permissions.Permissions:
        if p.value not in existing_permissions:
            db.add(ORMPermission(name=p.value, description=permissions.Permissions.to_name(p)))
    db.flush()


def find_role_by_name(name:str, db = get_db()):
    role_model = db.scalars(select(ORMRole).filter_by(name=name)).first()
    return _role_model_to_domain(role_model)

def find_role_by_id(id:int, db = get_db()):
    role_model = db.get(ORMRole, id)
    return _role_model_to_domain(role_model)


def remove_permissions_for_role(id:int, db = get_db(), commit = True):
    print(f"Удаляем разрешения для роли с id={id}")
    db.execute(delete(ORMRolePermission).where(ORMRolePermission.role_id == id))
    if commit:
        db.commit()


def save_role_permissions(role : permissions.Role, db = get_db(), commit = True):
    orm_role = db.get(ORMRole, role.id)
    if orm_role is None:
        raise ValueError(f"Role with id {role.id} not found")

    print(f"Обновляем разрешения роли с id={role.id} ({role.name})")
    orm_role.permissions = [_permission_model_for(p, db) for p in role.permissions]

    if commit:
        db.commit()


def update_role(role : permissions.Role, db = get_db(), commit = True):
    print(f"Обновляем роль {role}")

    orm_role = db.get(ORMRole, role.id)
    if orm_role is None:
        raise ValueError(f"Role with id {role.id} not found")

    orm_role.name = role.name
    orm_role.description = role.description
    save_role_permissions(role, db, False)

    if commit:
        db.commit()


def save_role(role : permissions.Role, db = get_db(), commit = True):
    print(f"Сохраняем роль {role}")

    existing_role = find_role_by_name(role.name, db)
    if existing_role is not None:
        raise ValueError(f"Роль с именем \"{role.name}\" уже существует")

    if role.id is None:
        orm_role = ORMRole(name=role.name, description=role.description)
        db.add(orm_role)
        db.flush()
        role.id = orm_role.id
        print(f"Новый id роли: {role.id}")
    else:
        orm_role = ORMRole(id=role.id, name=role.name, description=role.description)
        db.add(orm_role)
        db.flush()

    save_role_permissions(role, db, False)

    if commit:
        db.commit()

def remove_role(id:int, db = get_db(), commit = True):
    print(f"Удаляем роль с id={id}")
    db.execute(delete(ORMRolePermission).where(ORMRolePermission.role_id == id))
    db.execute(delete(ORMUserRole).where(ORMUserRole.role_id == id))
    orm_role = db.get(ORMRole, id)
    if orm_role is not None:
        db.delete(orm_role)
    if commit:
        db.commit()

def read_role_permissions(id, db = get_db()):
    orm_role = db.get(ORMRole, id)
    if orm_role is None:
        return set()

    permission_set = set()
    for perm in orm_role.permissions:
        try:
            permission_set.add(permissions.Permissions(perm.name))
        except ValueError:
            continue
    return permission_set

def read_all_roles(db = get_db()) -> list[permissions.Role]:
    orm_roles = db.scalars(select(ORMRole).order_by(ORMRole.id)).all()
    return [_role_model_to_domain(role) for role in orm_roles]

def remove_all_roles_from_user(user_id:int, db = get_db(), commit = True):
    print(f"Удаляем все роли у пользователя c id={user_id}")
    db.execute(delete(ORMUserRole).where(ORMUserRole.user_id == user_id))
    if commit:
        db.commit()

def save_roles_to_user(user_id:int, roles:list[permissions.Role], db = get_db(), commit = True):
    remove_all_roles_from_user(user_id, db, False)
    for role in roles:
        print(f"Сохраняем роль {role.name} для пользователя с id={user_id}")
        db.add(ORMUserRole(role_id=role.id, user_id=user_id))
    if commit:
        db.commit()

def save_roles_to_user_by_id(user_id:int, role_ids:list[int], db = get_db(), commit = True):
    remove_all_roles_from_user(user_id, db, False)
    for role_id in role_ids:
        print(f"Сохраняем роль {role_id} для пользователя с id={user_id}")
        db.add(ORMUserRole(role_id=role_id, user_id=user_id))
    if commit:
        db.commit()

def read_roles_for_user(user_id:int, db = get_db()) -> list[permissions.Role]:
    orm_roles = db.scalars(
        select(ORMRole)
        .join(ORMUserRole, ORMRole.id == ORMUserRole.role_id)
        .where(ORMUserRole.user_id == user_id)
        .order_by(ORMRole.id)
    ).all()
    return [_role_model_to_domain(role) for role in orm_roles]

def init_default_admin_role(db):
    _ensure_permissions(db)

    role_count = db.scalar(select(func.count()).select_from(ORMRole))
    if role_count == 0:
        print("Ролей не найдено. Создаём роль админа по умолчанию")
        admin_role = permissions.create_full_access_role()
        save_role(admin_role, db, False)

        reader_role = permissions.create_read_only_role()
        save_role(reader_role, db, False)
        

def create_roles_tables(db):
    bind = None
    if hasattr(db, 'get_bind'):
        bind = db.get_bind()
    elif hasattr(db, 'bind'):
        bind = db.bind

    if bind is None:
        raise RuntimeError('Unable to determine bind for create_roles_tables')

    flask_db.metadata.create_all(bind=bind)
    _ensure_permissions(db)
    init_default_admin_role(db)
