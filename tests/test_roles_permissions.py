import os

import pytest
from flask import Flask
from sqlalchemy import text

from templates.base.database_helper import db
from config import config
from templates.roles.permissions import Permissions, Role
from templates.roles.database_roles import (
    create_roles_tables,
    save_role,
    find_role_by_name,
    read_role_permissions,
    save_roles_to_user_by_id,
    read_roles_for_user,
    update_role,
    remove_role,
)

def test_permissions_to_name():
    assert Permissions.to_name(Permissions.users_read) == 'Чтение списка пользователей'
    assert Permissions.to_name(Permissions.users_manage) == 'Управление списком пользователей'
    assert Permissions.to_name(Permissions.devices_read) == 'Чтение списка устройств'


def test_role_add_remove_permissions():
    role = Role(id=None, name='TestRole', description='Test role')
    assert not role.is_permission_granted(Permissions.users_read)

    role.add_permission(Permissions.users_read)
    assert role.is_permission_granted(Permissions.users_read)

    role.remove_permission(Permissions.users_read)
    assert not role.is_permission_granted(Permissions.users_read)


def test_get_effective_permissions():
    role1 = Role(id=1, name='Role1', permissions={Permissions.users_read, Permissions.devices_read})
    role2 = Role(id=2, name='Role2', permissions={Permissions.users_manage})

    effective = Role.get_effective_permissions([role1, role2])
    assert Permissions.users_read in effective
    assert Permissions.devices_read in effective
    assert Permissions.users_manage in effective


def test_save_and_read_role_permissions(app_and_db):
    app, db_session = app_and_db

    role = Role(id=None, name='TestRole', description='Тестовая роль', permissions={Permissions.users_read, Permissions.users_manage})
    save_role(role, db=db_session, commit=True)

    found = find_role_by_name('TestRole', db=db_session)
    assert found is not None
    assert found.name == 'TestRole'
    assert found.description == 'Тестовая роль'
    assert role.id is not None

    permissions_set = read_role_permissions(role.id, db=db_session)
    assert Permissions.users_read in permissions_set
    assert Permissions.users_manage in permissions_set
    assert Permissions.devices_read not in permissions_set


def test_save_roles_to_user_and_read_roles_for_user(app_and_db):
    app, db_session = app_and_db

    role1 = Role(id=None, name='RoleA', description='Role A', permissions={Permissions.users_read})
    role2 = Role(id=None, name='RoleB', description='Role B', permissions={Permissions.users_manage})

    save_role(role1, db=db_session, commit=True)
    save_role(role2, db=db_session, commit=True)

    save_roles_to_user_by_id(user_id=42, role_ids=[role1.id, role2.id], db=db_session, commit=True)

    roles = read_roles_for_user(42, db=db_session)
    assert len(roles) == 2

    role_names = {r.name for r in roles}
    assert role_names == {'RoleA', 'RoleB'}
    assert any(Permissions.users_read in r.permissions for r in roles)
    assert any(Permissions.users_manage in r.permissions for r in roles)


def test_update_and_remove_role(app_and_db):
    app, db_session = app_and_db

    role = Role(id=None, name='OldRole', description='Старая роль', permissions={Permissions.users_read})
    save_role(role, db=db_session, commit=True)

    role.name = 'UpdatedRole'
    role.description = 'Обновлённая роль'
    role.permissions.add(Permissions.users_manage)
    update_role(role, db=db_session, commit=True)

    found = find_role_by_name('UpdatedRole', db=db_session)
    assert found is not None
    assert found.name == 'UpdatedRole'

    updated_permissions = read_role_permissions(role.id, db=db_session)
    assert Permissions.users_read in updated_permissions
    assert Permissions.users_manage in updated_permissions

    remove_role(role.id, db=db_session, commit=True)
    assert find_role_by_name('UpdatedRole', db=db_session) is None
