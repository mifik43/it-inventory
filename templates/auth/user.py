
from templates.base.db import Base, get_db_engine

from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import Session

from werkzeug.security import generate_password_hash

class User(Base):
    # имя колонки: Mapped[тип данных] = mapped_column(настройки колонки)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(), nullable=False)


def find_user_by_name(user_name:str):
    with Session(get_db_engine()) as session:
        user = session.scalar(select(User).where(User.name == user_name))
        return user

def safe_new_user(user_name:str, user_pass:str, session:Session):
    password_hash = generate_password_hash(user_pass)
    user = User(name=user_name, password = password_hash)
    session.add(user)


def init_default_admin():
    with Session(get_db_engine()) as session:
        user = find_user_by_name("admin")
        if user is not None:
            print("Админ по умолчанию найден")
            return
        
        print("Админ по умолчанию не найден. Создаём")
        safe_new_user(user_name="admin", user_pass='admin123', session=session)
        safe_new_user(user_name="user", user_pass='user123', session=session)
        session.commit()