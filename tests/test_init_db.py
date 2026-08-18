import pytest
import os

from templates.base.database_helper import db, init_db, get_connection_string
from config import config

from flask import Flask

def test_environment():
    assert os.environ.get('POSTGRES_HOST') == "localhost"
    assert os.environ.get('POSTGRES_PORT') == '5432'
    assert os.environ.get('POSTGRES_DB') == 'test_db'
    assert os.environ.get('POSTGRES_USER') == 'postgres'
    assert os.environ.get('POSTGRES_PASSWORD') == 'password'

def test_new_db(app_and_db):
    from templates.auth.users import User
    assert User.query.count() == 2

    user = User.query.filter_by(username="admin").first()
    assert user.username == "admin"

    user = User.query.filter_by(username="user").first()
    assert user.username == "user"