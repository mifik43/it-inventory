from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, declared_attr


# класс родитель для всех таблиц
# все таблицы должны наследоваться от неё
class Base(DeclarativeBase):
    __abstract__ = True  # Класс абстрактный, чтобы не создавать отдельную таблицу для него

    # все таблицы будут иметь имя класса+s в нижнем регистре, чтобы не прописывать отдельно
    @declared_attr.directive 
    def __tablename__(cls) -> str:
        return cls.__name__.lower() + 's'
    

class SingletonClass:
    _instance = None 

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SingletonClass, cls).__new__(cls)
            print("Создали новый SingletonClass")
            cls.db_engine = create_engine(DATABASE_URL, echo=True)
            print("Открыли коннект к базе")
        return cls._instance
    
def get_db_engine():
    singleton = SingletonClass()
    return singleton.db_engine

DATABASE_URL = "sqlite:///new_db.db"
