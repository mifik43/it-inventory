import pytest
from flask import session
from werkzeug.security import generate_password_hash
from flask_sqlalchemy import SQLAlchemy
from config import config
from flask import Flask
import os

def test_login_get(client):
    """Тест GET /login"""
    response = client.get('/users/login')
    assert response.status_code == 200

def test_login_post_success(client):
    """Тест успешного POST /login"""
    response = client.post('/users/login', data={
        'username': 'admin',
        'password': 'admin123'
    })
    assert response.status_code == 302
    # Проверяем, что сессия установлена
    with client.session_transaction() as sess:
        print(dict(sess))
        assert sess.get('user_id') is not None
        assert 'user_id' in sess
        assert response.headers['Location'] == '/'

def test_login_post_invalid(client):
    """Тест POST /login с неверными данными"""
    response = client.post('/users/login', data={
        'username': 'wrong',
        'password': 'wrong'
    })
    assert response.status_code == 200

    with client.session_transaction() as sess:
        print(dict(sess))
        assert sess.get('user_id') is None

def test_logout(logged_in_admin):
    """Тест /logout"""
    with logged_in_admin.session_transaction() as sess:
        assert 'user_id' in sess

    response = logged_in_admin.get('/users/logout', follow_redirects=True)
    assert response.status_code == 200

    with logged_in_admin.session_transaction() as sess:
        assert 'user_id' not in sess

# def test_profile(logged_in_admin):
#     """Тест /profile с авторизацией"""
#     response = logged_in_admin.get('/users/profile')
#     assert response.status_code == 200

def test_profile_unauthorized(client):
    """Тест /profile без авторизации"""
    response = client.get('/users/profile')
    assert response.status_code == 401  # Redirect to login

def test_change_password(logged_in_admin):
    """Тест изменения пароля"""
    from models import User, db
    user = db.session.query(User).filter_by(username='admin').first()
    old_hash = str(user.password_hash)
    db.session.remove()

    response = logged_in_admin.post('/users/change_password', data={
        'old_password': 'admin123',
        'new_password': 'newpass123',
        'confirm_password': 'newpass123'
    }, follow_redirects=True)
    assert response.status_code == 200

    db.session.commit()  # <-- Добавьте эту строку
    
    db.session.expire_all()
    
    from models import User, db as db2
    user = db2.session.query(User).filter_by(username='admin').first()
    assert user.password_hash != old_hash

# def test_admin_panel(logged_in_admin, client):
#     """Тест /admin для админа"""
#     response = client.get('/users/admin')
#     assert response.status_code == 200

# def test_admin_panel_forbidden(logged_in_user, client):
#     """Тест /admin для обычного пользователя"""
#     response = client.get('/users/admin')
#     assert response.status_code == 403  # Forbidden

def test_create_user(logged_in_admin):
    """Тест создания пользователя"""
    response = logged_in_admin.post('/users/admin/create', data={
        'username': 'newuser',
        'password': 'newpass',
        'role': 'user',
        'email': 'new@test.com',
        'full_name': 'New User'
    }, follow_redirects=True)
    assert response.status_code == 200
    from models import User
    user = User.query.filter_by(username='newuser').first()
    assert user is not None

# def test_edit_user(logged_in_admin, client, app):
#     """Тест редактирования пользователя"""
#     with app.app_context():
#         from models import User
#         user = User.query.filter_by(username='user').first()
#         response = client.post(f'/users/admin/edit/{user.id}', data={
#             'username': 'user',
#             'role': 'user',
#             'email': 'updated@test.com',
#             'full_name': 'Updated User',
#             'is_active': 'on'
#         }, follow_redirects=True)
#         assert response.status_code == 200
#         db.session.refresh(user)
#         assert user.email == 'updated@test.com'

# def test_delete_user(logged_in_admin, client, app):
#     """Тест удаления пользователя"""
#     with app.app_context():
#         from models import User
#         user = User.query.filter_by(username='user').first()
#         response = client.post(f'/users/admin/delete/{user.id}', follow_redirects=True)
#         assert response.status_code == 200
#         assert User.query.filter_by(username='user').first() is None

# def test_delete_self_forbidden(logged_in_admin, client, app):
#     """Тест запрета удаления себя"""
#     with app.app_context():
#         from models import User
#         admin = User.query.filter_by(username='admin').first()
#         response = client.post(f'/users/admin/delete/{admin.id}')
#         assert response.status_code == 302  # Redirect with flash