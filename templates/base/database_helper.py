from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base
from sqlalchemy.ext.declarative import declarative_base
import psycopg2
from psycopg2.extras import DictCursor
import logging

import os

logger = logging.getLogger(__name__)

# Инициализация SQLAlchemy
db = SQLAlchemy()
Base = declarative_base()

def get_connection_string():
    POSTGRES_HOST = os.environ.get('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT = os.environ.get('POSTGRES_PORT', '5432')
    POSTGRES_DB = os.environ.get('POSTGRES_DB', 'it_inventory')
    POSTGRES_USER = os.environ.get('POSTGRES_USER', 'postgres')
    POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD', 'password')

    SQLALCHEMY_DATABASE_URI = f'postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}'
    return SQLALCHEMY_DATABASE_URI


class PostgreSQLConnection:
    """Класс для прямого подключения к PostgreSQL"""
    _instance = None
    _engine = None
    _session_factory = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PostgreSQLConnection, cls).__new__(cls)
            cls._init_connection()
        return cls._instance
    
    @classmethod
    def _init_connection(cls):
        """Инициализация подключения к PostgreSQL"""
        try:
            
            # PostgreSQL конфигурация
            

            
            
            # Создаем движок SQLAlchemy
            cls._engine = create_engine(
                get_connection_string(),
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                echo=False  # Установите True для отладки SQL-запросов
            )
            
            # Создаем фабрику сессий
            cls._session_factory = sessionmaker(bind=cls._engine)
            
            logger.info("PostgreSQL connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL connection: {e}")
            raise
    
    @property
    def engine(self):
        return self._engine
    
    @property
    def session(self):
        """Возвращает новую сессию"""
        return scoped_session(self._session_factory)
    
    def get_raw_connection(self):
        """Получить сырое подключение psycopg2"""
        try:
            from app import app
            conn = psycopg2.connect(
                host=app.config.get('POSTGRES_HOST', 'localhost'),
                port=app.config.get('POSTGRES_PORT', '5432'),
                database=app.config.get('POSTGRES_DB', 'it_inventory'),
                user=app.config.get('POSTGRES_USER', 'postgres'),
                password=app.config.get('POSTGRES_PASSWORD', 'password')
            )
            return conn
        except Exception as e:
            logger.error(f"Failed to get raw connection: {e}")
            raise

def get_db():
    """Получить сессию базы данных (для обратной совместимости)"""
    singleton = PostgreSQLConnection()
    return singleton.session()

def get_raw_db():
    """Получить сырое подключение psycopg2"""
    singleton = PostgreSQLConnection()
    return singleton.get_raw_connection()



def init_db(app):
    """Инициализация базы данных"""
    with app.app_context():
        # Создаем все таблицы
        # Создаем администратора по умолчанию если нужно
        from templates.auth.users import User
        from werkzeug.security import generate_password_hash
        
        db.create_all()

        from ..roles.database_roles import create_roles_tables, save_roles_to_user_by_id, find_role_by_name
        create_roles_tables(db.session)
        db.session.commit()

        # Проверяем, есть ли уже пользователи
        if User.query.count() == 0:
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                role='admin',
                email='mifik43@yandex.ru',
                full_name='Администратор',
                is_active=True
            )
            
            user = User(
                username='user',
                password_hash=generate_password_hash('user123'),
                role='user',
                email='user@example.com',
                full_name='Пользователь',
                is_active=True
            )
            
            db.session.add(admin)
            db.session.add(user)
            db.session.commit()

            admin_role = find_role_by_name("SuperAdmin", db.session)
            user_role = find_role_by_name("Reader", db.session)

            save_roles_to_user_by_id(admin.id, [admin_role.id], db.session)
            save_roles_to_user_by_id(user.id, [user_role.id], db.session)
            logger.info("Default admin and user created")

