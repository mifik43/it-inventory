
from templates.base.db import Base, get_db_engine
from templates.roles.permissions import Role, init_default_roles, find_role_by_name

from sqlalchemy import String, select, Table, Column, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm import Session

from werkzeug.security import generate_password_hash, check_password_hash

user_roles_table = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id")),
    Column("role_id", ForeignKey("roles.id")),
)

class User(Base):
    # имя колонки: Mapped[тип данных] = mapped_column(настройки колонки)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(), nullable=False)

    roles:Mapped[list[Role]] = relationship(secondary=user_roles_table)

    def update_password(self, new_password:str):
        self.password = generate_password_hash(new_password)
    
    def verify_password(self, password:str):
        return check_password_hash(self.password, password)



def find_user_by_name(user_name:str, session:Session):
    user = session.scalar(select(User).where(User.name == user_name))
    return user

def safe_new_user(user_name:str, user_pass:str, session:Session):
    print(f"Сохраняем нового пользователя '{user_name}'")
    password_hash = generate_password_hash(user_pass)
    user = User(name=user_name, password = password_hash)
    session.add(user)


def init_default_admin():
    init_default_roles()
    with Session(get_db_engine()) as session:
        user = find_user_by_name("admin", session)
        if user is not None:
            print("Админ по умолчанию найден")
            return
        
        print("Админ по умолчанию не найден. Создаём")
        safe_new_user(user_name="admin", user_pass='admin123', session=session)
        safe_new_user(user_name="user", user_pass='user123', session=session)
        session.commit()

        user = find_user_by_name("admin", session=session)
        role = find_role_by_name("SuperAdmin", session=session)

        user.roles.append(role)

        session.commit()