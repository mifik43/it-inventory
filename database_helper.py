import sqlite3

class SingletonClass:
    _instance = None 

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SingletonClass, cls).__new__(cls)
            print("Создали новый SingletonClass")
            cls.conn = sqlite3.connect('it_inventory.db', check_same_thread=False)
            cls.conn.row_factory = sqlite3.Row
            print("Открыли коннект к базе")
        return cls._instance
    
def get_db():
    singleton = SingletonClass()
    return singleton.conn

