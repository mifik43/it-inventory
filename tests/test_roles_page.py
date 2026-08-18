import os
import sys
import pytest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.pool import StaticPool
from werkzeug.security import generate_password_hash
from config import config
from templates.roles.permissions import Permissions

def create_role_in_db(name, description, permissions=None):
    from templates.roles.database_roles import save_role
    from templates.roles.permissions import Role as DomainRole

    role = DomainRole(id=None, name=name, description=description, permissions=set(permissions or []))
    save_role(role, commit=True)
    return role


def test_roles_page_list(logged_in_admin):
    response = logged_in_admin.get('/roles')

    assert response.status_code == 200
    text = response.data.decode('utf-8')
    assert 'Управление ролями' in text


def test_create_role_get(logged_in_admin):
    response = logged_in_admin.get('/create_role')

    assert response.status_code == 200
    text = response.data.decode('utf-8')
    assert 'Создание роли' in text
    assert 'Имя роли' in text


def test_create_role_post_creates_role(logged_in_admin):
    response = logged_in_admin.post(
        '/create_role',
        data={
            'name': 'TestRole',
            'description': 'Тестовая роль',
            'roles_read': 'on',
            'roles_manage': 'on',
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'TestRole' in response.data

    from models import Role as ORMRole
    role = ORMRole.query.filter_by(name='TestRole').first()
    assert role is not None
    assert role.description == 'Тестовая роль'


def test_edit_role_get_and_post(logged_in_admin):
    from templates.roles.permissions import Role as DomainRole
    role = create_role_in_db(
        name='EditableRole',
        description='Before edit',
        permissions={Permissions.roles_read},
    )
    role_id = role.id

    response = logged_in_admin.get(f'/edit_role/{role_id}')
    assert response.status_code == 200
    text = response.data.decode('utf-8')
    assert 'Редактирование роли' in text
    assert 'EditableRole' in text

    response = logged_in_admin.post(
        f'/edit_role/{role_id}',
        data={
            'name': 'EditableRole',
            'description': 'After edit',
            'roles_read': 'on',
            'roles_manage': 'on',
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
        
    from models import Role as ORMRole
    updated_role = ORMRole.query.get(role_id)
    assert updated_role is not None
    assert updated_role.description == 'After edit'


def test_delete_role(logged_in_admin):
    role = create_role_in_db(
        name='DeletableRole',
        description='For deletion',
        permissions={Permissions.roles_read},
    )
    role_id = role.id

    response = logged_in_admin.get(f'/delete_role/{role_id}', follow_redirects=True)
    assert response.status_code == 200
    assert b'DeletableRole' not in response.data

    from models import Role as ORMRole
    assert ORMRole.query.get(role_id) is None
