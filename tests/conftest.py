import pytest
import os

from templates.base.database_helper import db, init_db, get_connection_string
from config import config

from flask import Flask

from templates.roles.database_roles import (
    create_roles_tables
)

@pytest.fixture(autouse=True)
def test_env(monkeypatch):
    """Автоматически применяется для всех тестов в файле"""
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_DB", "test_db")
    monkeypatch.setenv("POSTGRES_USER", "postgres")
    monkeypatch.setenv("POSTGRES_PASSWORD", "password")


@pytest.fixture()
def app_and_db():
    print("Init new db")
    from app import app
    #app = Flask("Test")
    #app.config.from_object(config)
    with app.app_context():
        #db.init_app(app)
        print("Drop all data before test")
        db.drop_all()
        print("Create new tables")
        db.create_all()

        print("Init default data")
        init_db(app)
        create_roles_tables(db.session)

        print("Init routes")
        #from templates.auth.users import bluprint_user_routes
        #import templates.roles.roles_page as roles_page

        #app.register_blueprint(bluprint_user_routes)
        #app.register_blueprint(roles_page.bluprint_roles_routes)

        print("Call test")

        yield app, db.session

        print("Test finished. Clear data")
        db.close_all_sessions()
        #db.session.remove()
        db.engine.dispose()

        #db.drop_all()

@pytest.fixture()
def client(app_and_db):
    app, session = app_and_db
    yield app.test_client()

@pytest.fixture()
def logged_in_admin(client):
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
    
    yield client